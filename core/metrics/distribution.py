"""Distribution metrics — win-rate spread and run-duration stats.

Both are domain-agnostic: they read only ``entities_involved``, ``outcome['winner']``,
and ``duration_steps`` from runs.
"""

from __future__ import annotations

import statistics
from collections import Counter

from core.metrics.base import Metric, MetricResult, winner_of
from core.simulator_interface import RunResult

# An entity whose win rate deviates from the mean by more than this many standard
# deviations is flagged as an outlier (over/under-powered).
_OUTLIER_SIGMA = 2.0


class WinRateDistribution(Metric):
    """Per-entity win rate plus the spread (mean, std) and outliers across entities."""

    name = "winrate_distribution"
    kind = "distribution"
    description = "Win rate per entity, dispersion, and outliers."

    def compute(self, runs: list[RunResult]) -> MetricResult:
        appearances: Counter[str] = Counter()
        wins: Counter[str] = Counter()

        for run in runs:
            for entity in run.entities_involved:
                appearances[entity] += 1
            winner = winner_of(run)
            if winner is not None:
                wins[winner] += 1

        per_entity = {
            entity: wins[entity] / count for entity, count in appearances.items() if count > 0
        }
        rates = list(per_entity.values())

        mean = statistics.fmean(rates) if rates else 0.0
        std = statistics.pstdev(rates) if len(rates) > 1 else 0.0
        outliers = (
            [e for e, r in per_entity.items() if abs(r - mean) > _OUTLIER_SIGMA * std]
            if std > 0
            else []
        )

        return MetricResult(
            kind=self.kind,
            name=self.name,
            data={
                "mean": mean,
                "std": std,
                "outliers": sorted(outliers),
                "per_entity": per_entity,
            },
        )


class DurationStats(Metric):
    """Distribution of run lengths (``duration_steps``) — flags degenerate fast/slow play."""

    name = "duration_stats"
    kind = "distribution"
    description = "Mean, std, min, and max of run duration in steps."

    def compute(self, runs: list[RunResult]) -> MetricResult:
        durations = [run.duration_steps for run in runs]
        if not durations:
            data = {"mean": 0.0, "std": 0.0, "min": 0, "max": 0}
        else:
            data = {
                "mean": statistics.fmean(durations),
                "std": statistics.pstdev(durations) if len(durations) > 1 else 0.0,
                "min": min(durations),
                "max": max(durations),
            }
        return MetricResult(kind=self.kind, name=self.name, data=data)
