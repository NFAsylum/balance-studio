"""Parallel batch execution of independent matches.

Fans matches out over a :class:`~concurrent.futures.ThreadPoolExecutor`. Because each
``simulator.run`` is pure and independent, results are order-preserving and identical to a
serial run. Pure-Python simulators are CPU-bound, so the GIL means threads add little wall-
clock speedup today (the single-threaded path already beats the perf targets by ~1000x) —
the value is the seam: swap ``ThreadPoolExecutor`` for ``ProcessPoolExecutor`` here to get
real parallelism if a heavier simulator ever needs it.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

from core.simulator_interface import Environment, RunResult, SimulatorInterface


def run_matches_parallel(
    simulator: SimulatorInterface,
    matchups: list[list[Any]],
    env: Environment,
    max_workers: int | None = None,
) -> list[RunResult]:
    """Run each matchup (a list of participating entities) via ``simulator.run``, in parallel.

    Order is preserved, so output matches the equivalent serial run exactly.
    """
    if not matchups:
        return []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(lambda m: simulator.run(m, env), matchups))
