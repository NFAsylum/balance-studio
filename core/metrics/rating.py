"""Rating metrics.

``EloMmrRating`` assigns each entity a skill rating from head-to-head runs. This is a
pragmatic sequential-Elo implementation (the historical ancestor of Elo-MMR): it is
deterministic given run order and yields a sensible entity -> rating map. A full Bayesian
Elo-MMR (per the referenced paper) can replace it behind the same interface later.
"""

from __future__ import annotations

from core.metrics.base import Metric, MetricResult, winner_of
from core.simulator_interface import RunResult

_INITIAL_RATING = 1500.0
_K_FACTOR = 32.0


class EloMmrRating(Metric):
    """Elo-style rating per entity, updated sequentially over 1v1 runs."""

    name = "elo_mmr"
    kind = "rating"
    description = "Skill rating per entity from head-to-head results."

    def __init__(self, initial: float = _INITIAL_RATING, k_factor: float = _K_FACTOR):
        self.initial = initial
        self.k_factor = k_factor

    def compute(self, runs: list[RunResult]) -> MetricResult:
        ratings: dict[str, float] = {}

        def rating(entity: str) -> float:
            return ratings.setdefault(entity, self.initial)

        for run in runs:
            involved = run.entities_involved
            if len(involved) != 2:
                # Rating is defined for 1v1; ensure participants exist in the map anyway.
                for e in involved:
                    rating(e)
                continue
            a, b = involved
            ra, rb = rating(a), rating(b)
            winner = winner_of(run)
            if winner == a:
                score_a = 1.0
            elif winner == b:
                score_a = 0.0
            else:
                score_a = 0.5  # draw or no winner
            expected_a = 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))
            ratings[a] = ra + self.k_factor * (score_a - expected_a)
            ratings[b] = rb + self.k_factor * ((1.0 - score_a) - (1.0 - expected_a))

        return MetricResult(kind=self.kind, name=self.name, data=dict(ratings))
