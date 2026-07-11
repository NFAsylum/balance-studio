"""B6.5 — validate the local LLM hats: success rate + full loops per domain.

Run: LLM_BACKEND=local poetry run python -m scripts.experiment_b6
Measures the fraction of designed entities that pass schema + constraints, and runs 2
full design->simulate->judge->iterate loops per domain, then prints a JSON summary.
"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

from core.constraint_engine import Constraint
from core.iteration_engine import IterationEngine
from core.llm_factory import build_hats
from core.scenario import EventLog, Scenario
from core.snapshot import Replay, SnapshotStore

from api.registry import discover_domains

_BASE = Path("/tmp/claude-1000/-workspace/7e6a8d11-9409-4f9a-b36d-8c76ac447255/scratchpad/exp_b6")

DOMAINS = {
    "card_game": {
        "brief": "aggressive low-cost cyberpunk deck with varied abilities",
        "n": 5,
        "constraints": [Constraint(kind="range", params={"field": "cost", "min": 1, "max": 4})],
    },
    "creature_rpg": {
        "brief": "balanced roster spread across elemental types",
        "n": 6,
        "constraints": [Constraint(kind="range", params={"field": "hp", "min": 40, "max": 260})],
    },
}


def measure_success(designer, simulator, cfg, trials: int) -> dict:
    schema = simulator.entity_schema()
    emitted = valid = 0
    latencies = []
    for _ in range(trials):
        stats = {"emitted": 0, "valid": 0}
        t = time.perf_counter()
        designer.design(cfg["brief"], schema, cfg["constraints"], cfg["n"], stats=stats)
        latencies.append(round(time.perf_counter() - t, 2))
        emitted += stats["emitted"]
        valid += stats["valid"]
    rate = valid / emitted if emitted else 0.0
    return {"emitted": emitted, "valid": valid, "success_rate": round(rate, 3), "design_latencies_s": latencies}


def run_loops(domain: str, hats, domains, cfg, loops: int) -> list[dict]:
    results = []
    for i in range(loops):
        sid = f"{domain}-loop{i}"
        d = _BASE / sid
        if d.exists():
            shutil.rmtree(d)
        log = EventLog(base_dir=_BASE)
        log.init_scenario(Scenario(id=sid, domain=domain, name=f"exp {i}", brief=cfg["brief"], n_entities=cfg["n"]))
        engine = IterationEngine(log, Replay(log, SnapshotStore(_BASE)), domains, hats.designer, hats.judge, hats.iterator, n_runs=20)
        t = time.perf_counter()
        loop = engine.auto_loop(sid, max_steps=3, stop_on_convergence=True)
        elapsed = round(time.perf_counter() - t, 1)
        designed = sum(s.details.get("n_designed", 0) for s in loop.steps if s.phase == "design")
        results.append(
            {
                "loop": i,
                "steps": len(loop.steps),
                "converged": loop.converged,
                "designed": designed,
                "elapsed_s": elapsed,
            }
        )
    return results


def main() -> None:
    if _BASE.exists():
        shutil.rmtree(_BASE)
    hats = build_hats("local")
    domains = discover_domains()

    summary = {}
    for domain, cfg in DOMAINS.items():
        print(f"== {domain} ==")
        simulator = domains[domain]
        success = measure_success(hats.designer, simulator, cfg, trials=3)
        print(f"  success: {success['valid']}/{success['emitted']} = {success['success_rate']:.0%}")
        loops = run_loops(domain, hats, domains, cfg, loops=2)
        for lp in loops:
            print(f"  loop {lp['loop']}: {lp['steps']} steps, converged={lp['converged']}, {lp['elapsed_s']}s")
        summary[domain] = {"success": success, "loops": loops}

    print("\n=== JSON SUMMARY ===")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
