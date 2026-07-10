"""Sprint 2 end-to-end demo, entirely on Fake LLMs (no API key, fully deterministic).

Flow: create Scenario -> FakeDesigner designs N units (each logged as a create_entity event)
-> CardGameSimulator plays a ~100-match round-robin of solo decks (so win rate is per unit)
-> FakeJudge scores variety -> FakeIterator proposes nerf/buff modifications -> snapshot.
Everything persists under scenarios/<id>/ (events.jsonl + manifest.json + snapshots/).

Run:
    poetry run python -m scripts.demo_sprint2 --brief "aggro deck" --n 5 --domain card_game

Same brief + seed reproduces byte-identical stdout (the scenario dir is rebuilt each run).
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import shutil
from pathlib import Path

from api.registry import discover_domains
from core.llm_fakes import FakeDesigner, FakeIterator, FakeJudge
from core.metrics import EloMmrRating, WinRateDistribution, aggregate_metrics
from core.scenario import Event, EventLog, Scenario
from core.snapshot import Replay, SnapshotStore
from domains.card_game.simulator import Deck, MatchEnv

TARGET_MATCHES = 100


def _scenario_id(brief: str, n: int, domain: str, seed: int) -> str:
    digest = hashlib.sha256(f"{domain}|{brief}|{n}|{seed}".encode()).hexdigest()[:12]
    return f"demo-{domain}-{digest}"


def run_demo(brief: str, n: int, domain: str, seed: int, base_dir: str) -> dict:
    simulator = discover_domains()[domain]
    schema = simulator.entity_schema()

    scenario_id = _scenario_id(brief, n, domain, seed)
    scenario_dir = Path(base_dir) / scenario_id
    if scenario_dir.exists():
        shutil.rmtree(scenario_dir)  # fresh run -> reproducible

    log = EventLog(base_dir=base_dir)
    log.init_scenario(Scenario(id=scenario_id, domain=domain, name=f"Demo: {brief}"))

    # 1) Design entities (each logged).
    entities = FakeDesigner().design(brief, schema, [], n)
    for entity in entities:
        data = entity.model_dump()
        log.append(
            scenario_id,
            Event(actor="llm-designer", kind="create_entity", target=data["name"], after=data),
        )

    # 2) Simulate: round-robin of solo decks so each unit gets a win rate.
    names = [e.model_dump()["name"] for e in entities]
    dumps = {e.model_dump()["name"]: e.model_dump() for e in entities}
    pairs = list(itertools.combinations(names, 2))
    per_pair = max(1, round(TARGET_MATCHES / len(pairs))) if pairs else 0
    runs = []
    match_seed = seed
    for a, b in pairs:
        for _ in range(per_pair):
            env = MatchEnv(seed=match_seed)
            match_seed += 1
            deck_a = Deck(id=a, units=[dumps[a]])
            deck_b = Deck(id=b, units=[dumps[b]])
            runs.append(simulator.run([deck_a, deck_b], env))

    metric_results = aggregate_metrics([WinRateDistribution(), EloMmrRating()], runs)
    winrate = metric_results["winrate_distribution"].data["per_entity"]
    log.append(
        scenario_id,
        Event(
            actor="user",
            kind="simulate",
            target="scenario",
            after={"n_matches": len(runs), "winrate": winrate},
            metadata={"mode": "round_robin_solo"},
        ),
    )

    # 3) Subjective judgement.
    judge = FakeJudge().judge(entities, "variety")
    log.append(
        scenario_id,
        Event(
            actor="llm-judge",
            kind="evaluate_subjective",
            target="scenario",
            after={"criterion": "variety", "score": judge.score},
            metadata={"rationale": judge.rationale},
        ),
    )

    # 4) Iterator proposals (logged as notes; not auto-applied).
    mods = FakeIterator().propose_changes(entities, {"winrate": winrate}, {"variety": judge.score}, [])
    for mod in mods:
        log.append(
            scenario_id,
            Event(
                actor="llm-iterator",
                kind="note",
                target=mod.target or "scenario",
                metadata={"modification": mod.model_dump()},
            ),
        )

    # 5) Snapshot the final state.
    replay = Replay(log, SnapshotStore(base_dir=base_dir))
    snapshot = replay.snapshot_now(scenario_id)

    return {
        "scenario_id": scenario_id,
        "brief": brief,
        "domain": domain,
        "n": n,
        "seed": seed,
        "entities": sorted(names),
        "matches": len(runs),
        "winrate": {k: round(v, 3) for k, v in sorted(winrate.items())},
        "judge": {"criterion": "variety", "score": round(judge.score, 3)},
        "modifications": [
            {"target": m.target, "reasoning": m.reasoning}
            for m in sorted(mods, key=lambda m: m.target or "")
        ],
        "events_persisted": log.head(scenario_id, "main"),
        "snapshot_at_seq": snapshot.at_seq,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Balance Studio — Sprint 2 Fake-LLM demo")
    parser.add_argument("--brief", required=True)
    parser.add_argument("--n", type=int, default=5)
    parser.add_argument("--domain", default="card_game")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--scenarios-dir", default="scenarios")
    args = parser.parse_args()

    summary = run_demo(args.brief, args.n, args.domain, args.seed, args.scenarios_dir)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
