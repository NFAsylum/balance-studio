"""Balancing-quality experiment: does the Iterator reduce imbalance while keeping variety?

Per domain, per trial (3): design N entities -> measure dispersion + variety -> run K Iterator
iterations (simulate -> judge -> propose -> apply valid) -> measure again. Aggregate mean±std
over trials. Dispersion = win-rate std (competitive) or completion-rate std across workloads
(team). Variety = mean pairwise Gower distance (guardrail against homogenising).

Run: LLM_BACKEND=local poetry run python -m scripts.experiment_balance
     (LLM_BACKEND=fake for a fast harness dry-run)
"""

from __future__ import annotations

import json
import os
import random
import statistics
import tempfile
from typing import Any

from api.registry import discover_domains
from core.balance_metrics import pct_delta, variety_score
from core.iteration_engine import is_valid_payload
from core.llm_factory import build_hats
from core.objectives import Objective
from core.metrics.distribution import WinRateDistribution
from domains.card_game.schema import load_seed as _card_seed
from domains.creature_rpg.schema import load_seed as _creature_seed
from domains.team_composition.schema import load_seed as _team_seed

# Start each trial from the shipped seed roster — a fixed, known-imbalanced set — so the
# experiment isolates the Iterator's effect (not the LLM designer's luck) and never degenerates.
LOADERS = {"card_game": _card_seed, "creature_rpg": _creature_seed, "team_composition": _team_seed}

TRIALS = 3
ITERATIONS = 5
N_WORKLOADS = 10  # team dispersion is measured across this many varied workloads
# Cap edits per iteration: the combat domains have non-linear stat->winrate, so a shotgun of
# ~27 blind edits/pass adds noise and *raises* spread. Few surgical edits let it converge.
MAX_MODS_PER_ITER = 3
# The LLM judge here only ever proxied "variety", which we already compute exactly (and for
# free) with variety_score (Gower). So we feed the exact value into the iterator and skip a
# redundant per-iteration LLM call — halving the calls. Flip to A/B the qualitative judge.
USE_LLM_JUDGE = False

DOMAINS = {
    "card_game": {"brief": "a varied aggressive deck with distinct roles", "n": 10, "kind": "competitive"},
    "creature_rpg": {"brief": "a varied roster spread across elemental types", "n": 10, "kind": "competitive"},
    "team_composition": {"brief": "a team with complementary, non-overlapping skills", "n": 10, "kind": "team"},
}


# -- measurement ----------------------------------------------------------


def _competitive_dispersion(sim, instances, seed: int) -> float:
    env = sim.environment_schema()(seed=seed)
    runs = sim.run_batch(instances, env, n_runs=200)
    return WinRateDistribution().compute(runs).data["std"]


def _team_dispersion(sim, instances, seed: int) -> float:
    from domains.team_composition.schema import TASK_TYPES

    names = [t.name for t in TASK_TYPES]
    rates = []
    for w in range(N_WORKLOADS):
        rng = random.Random(seed * 1000 + w)
        tasks = rng.sample(names, k=min(8, len(names)))
        env = sim.environment_schema()(seed=seed + w, tasks=tasks, deadline_days=6)
        rates.append(sim.run(instances, env).outcome["completion_rate"])
    return statistics.pstdev(rates) if len(rates) > 1 else 0.0


def _sim_metrics(sim, instances, kind: str, seed: int) -> dict[str, Any]:
    if kind == "competitive":
        env = sim.environment_schema()(seed=seed)
        runs = sim.run_batch(instances, env, n_runs=200)
        per_entity = WinRateDistribution().compute(runs).data["per_entity"]
        return {"winrate": per_entity}
    env = sim.environment_schema()(seed=seed, deadline_days=6)
    outcome = sim.run(instances, env).outcome
    return {k: outcome[k] for k in ("completion_rate", "coverage", "redundancy", "spof_skills")}


def _dispersion(sim, instances, kind: str, seed: int) -> float:
    return _competitive_dispersion(sim, instances, seed) if kind == "competitive" else _team_dispersion(sim, instances, seed)


# -- iterator application -------------------------------------------------


def _apply(entities: dict[str, dict], mods, model_cls) -> int:
    """Apply modifications. Edits MERGE the (often partial) payload onto the current entity,
    so a delta like {"cost": 2} is a valid update rather than a rejected half-entity."""
    applied = 0
    for mod in mods:
        if mod.kind == "delete":
            if entities.pop(mod.target, None) is not None:
                applied += 1
            continue
        base = dict(entities.get(mod.target, {})) if mod.target else {}
        merged = {**base, **(mod.payload or {})}
        if not is_valid_payload(model_cls, merged):
            continue
        key = str(merged.get("name") or mod.target or "")
        if not key:
            continue
        if mod.target and mod.target in entities and mod.target != key:
            entities.pop(mod.target, None)  # renamed
        entities[key] = merged
        applied += 1
    return applied


# -- one trial ------------------------------------------------------------


def run_trial(domain: str, cfg: dict, hats, sim, seed: int) -> dict | None:
    schema = sim.entity_schema()
    model_cls = schema.build_model()
    initial = LOADERS[domain]()[: cfg["n"]]
    if len(initial) < 2:
        return None
    entities = {e.model_dump()["name"]: e.model_dump() for e in initial}

    def snapshot() -> tuple[float, float]:
        insts = [model_cls(**d) for d in entities.values()]
        return _dispersion(sim, insts, cfg["kind"], seed), variety_score(list(entities.values()), schema)

    disp0, var0 = snapshot()
    total_applied = 0
    for _ in range(ITERATIONS):
        insts = [model_cls(**d) for d in entities.values()]
        if len(insts) < 2:
            break
        metrics = _sim_metrics(sim, insts, cfg["kind"], seed)
        balance_target = "winrate spread" if cfg["kind"] == "competitive" else "completion-rate spread"
        objectives = [Objective(metric_name=balance_target, direction="minimize", weight=1.0)]
        variety_signal = variety_score(list(entities.values()), schema)
        try:
            if USE_LLM_JUDGE:
                variety_signal = hats.judge.judge(insts, "variety").score
            mods = hats.iterator.propose_changes(insts, metrics, {"variety": variety_signal}, objectives)
        except Exception as exc:  # noqa: BLE001 - a junk LLM response shouldn't kill the trial
            print(f"  (iteration skipped: {type(exc).__name__})", flush=True)
            continue
        total_applied += _apply(entities, mods[:MAX_MODS_PER_ITER], model_cls)
    disp1, var1 = snapshot()
    return {"disp_before": disp0, "disp_after": disp1, "var_before": var0, "var_after": var1, "applied": total_applied}


def _agg(values: list[float]) -> tuple[float, float]:
    return (round(statistics.fmean(values), 3), round(statistics.pstdev(values), 3) if len(values) > 1 else 0.0)


_OUT = os.path.join(tempfile.gettempdir(), "exp_balance_result.json")


def main() -> None:
    hats = build_hats()
    domains = discover_domains()
    print(f"backend={os.getenv('LLM_BACKEND', 'fake')} trials={TRIALS} iterations={ITERATIONS}\n", flush=True)

    summary = {}
    for domain, cfg in DOMAINS.items():
        sim = domains[domain]
        trials = [run_trial(domain, cfg, hats, sim, seed) for seed in (42, 43, 44)]
        trials = [t for t in trials if t]
        if not trials:
            print(f"{domain}: no valid trials (design failed)", flush=True)
            continue
        db_m, db_s = _agg([t["disp_before"] for t in trials])
        da_m, da_s = _agg([t["disp_after"] for t in trials])
        vb_m, vb_s = _agg([t["var_before"] for t in trials])
        va_m, va_s = _agg([t["var_after"] for t in trials])
        row = {
            "trials": len(trials),
            "dispersion_before": [db_m, db_s],
            "dispersion_after": [da_m, da_s],
            "variety_before": [vb_m, vb_s],
            "variety_after": [va_m, va_s],
            "dispersion_delta_pct": pct_delta(db_m, da_m),
            "variety_delta_pct": pct_delta(vb_m, va_m),
            "avg_applied": round(statistics.fmean([t["applied"] for t in trials]), 1),
        }
        summary[domain] = row
        print(f"== {domain} ({len(trials)} trials) ==", flush=True)
        print(f"  dispersion: {db_m}±{db_s} -> {da_m}±{da_s}  ({row['dispersion_delta_pct']:+}%)", flush=True)
        print(f"  variety:    {vb_m}±{vb_s} -> {va_m}±{va_s}  ({row['variety_delta_pct']:+}%)", flush=True)
        print(f"  avg mods applied/trial: {row['avg_applied']}", flush=True)
        # persist incrementally so partial progress survives
        with open(_OUT, "w") as fh:
            json.dump(summary, fh, indent=2)

    print("\n=== JSON SUMMARY ===", flush=True)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
