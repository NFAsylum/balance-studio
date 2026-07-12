"""Creature RPG metrics: tier emergence, dominance, and usage coverage.

These are domain metrics but operate only on generic :class:`RunResult` fields
(``entities_involved`` + ``outcome['winner']``) — they read nothing creature-specific,
so they sit on the core :class:`~core.metrics.base.Metric` base like any other metric.
"""

from __future__ import annotations

import math
from collections import Counter

from core.metrics.base import Metric, MetricResult, winner_of
from core.simulator_interface import RunResult

_TIERS = ["S", "A", "B", "C", "D"]


def _win_rates(runs: list[RunResult]) -> dict[str, float]:
    appearances: Counter[str] = Counter()
    wins: Counter[str] = Counter()
    for run in runs:
        for entity in run.entities_involved:
            appearances[entity] += 1
        winner = winner_of(run)
        if winner is not None:
            wins[winner] += 1
    return {e: wins[e] / n for e, n in appearances.items() if n > 0}


def _appearances(runs: list[RunResult]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for run in runs:
        for entity in run.entities_involved:
            counter[entity] += 1
    return counter


class TierEmergence(Metric):
    """Buckets entities into S/A/B/C/D tiers by win-rate quantile."""

    name = "tier_emergence"
    kind = "tier"
    description = "Entities grouped into S/A/B/C/D tiers by win rate."

    def compute(self, runs: list[RunResult]) -> MetricResult:
        rates = _win_rates(runs)
        ranked = sorted(rates, key=lambda e: (-rates[e], e))
        n = len(ranked)
        tiers: dict[str, list[str]] = {t: [] for t in _TIERS}
        by_entity: dict[str, str] = {}
        for i, entity in enumerate(ranked):
            tier = _TIERS[min(len(_TIERS) - 1, int((i / n) * len(_TIERS)))] if n else "D"
            tiers[tier].append(entity)
            by_entity[entity] = tier
        return MetricResult(
            kind=self.kind, name=self.name, data={"tiers": tiers, "by_entity": by_entity}
        )


class DominanceIndex(Metric):
    """Fraction of decisive matches won by a top-percentile entity (default top 5%)."""

    name = "dominance_index"
    kind = "index"
    description = "Share of decided matches won by the top-percentile entities."

    def __init__(self, top_fraction: float = 0.05):
        self.top_fraction = top_fraction

    def compute(self, runs: list[RunResult]) -> MetricResult:
        rates = _win_rates(runs)
        ranked = sorted(rates, key=lambda e: (-rates[e], e))
        top_k = max(1, math.ceil(len(ranked) * self.top_fraction)) if ranked else 0
        top = set(ranked[:top_k])

        decided = [w for w in (winner_of(r) for r in runs) if w is not None]
        index = sum(1 for w in decided if w in top) / len(decided) if decided else 0.0
        return MetricResult(
            kind=self.kind,
            name=self.name,
            data={"dominance_index": index, "top_entities": sorted(top)},
        )


class UsageCoverage(Metric):
    """How many entities appear in at least ``min_matches`` matches."""

    name = "usage_coverage"
    kind = "coverage"
    description = "Count of entities seen in at least a minimum number of matches."

    def __init__(self, min_matches: int = 1):
        self.min_matches = min_matches

    def compute(self, runs: list[RunResult]) -> MetricResult:
        appearances = _appearances(runs)
        covered = sum(1 for n in appearances.values() if n >= self.min_matches)
        return MetricResult(
            kind=self.kind,
            name=self.name,
            data={
                "covered": covered,
                "total": len(appearances),
                "min_matches": self.min_matches,
                "appearances": dict(appearances),
            },
        )
