"""Team composition metrics: skill coverage, redundancy, single points of failure.

These read the structural analysis the simulator embeds in each ``RunResult.outcome`` (the
team-vs-workload skill picture is the same across runs, so run[0] suffices), plus the
completion rate averaged over runs. All sit on the core :class:`Metric` base.
"""

from __future__ import annotations

import statistics

from core.metrics.base import Metric, MetricResult
from core.simulator_interface import RunResult


def _first_outcome(runs: list[RunResult]) -> dict:
    return runs[0].outcome if runs else {}


class CompletionRate(Metric):
    name = "completion_rate"
    kind = "distribution"
    description = "Mean fraction of workload tasks completed before the deadline."

    def compute(self, runs: list[RunResult]) -> MetricResult:
        rates = [r.outcome.get("completion_rate", 0.0) for r in runs]
        return MetricResult(
            kind=self.kind,
            name=self.name,
            data={
                "mean": statistics.fmean(rates) if rates else 0.0,
                "min": min(rates, default=0.0),
                "max": max(rates, default=0.0),
            },
        )


class SkillCoverage(Metric):
    name = "skill_coverage"
    kind = "coverage"
    description = "Fraction of workload-required skills the team collectively has."

    def compute(self, runs: list[RunResult]) -> MetricResult:
        outcome = _first_outcome(runs)
        return MetricResult(
            kind=self.kind,
            name=self.name,
            data={
                "coverage": outcome.get("coverage", 0.0),
                "missing_skills": outcome.get("missing_skills", []),
            },
        )


class Redundancy(Metric):
    name = "redundancy"
    kind = "index"
    description = "Average number of people per required skill (higher = more resilient)."

    def compute(self, runs: list[RunResult]) -> MetricResult:
        outcome = _first_outcome(runs)
        return MetricResult(
            kind=self.kind,
            name=self.name,
            data={"redundancy": outcome.get("redundancy", 0.0)},
        )


class SinglePointOfFailure(Metric):
    name = "single_point_of_failure"
    kind = "coverage"
    description = "Required skills held by exactly one person (losing them blocks work)."

    def compute(self, runs: list[RunResult]) -> MetricResult:
        outcome = _first_outcome(runs)
        spof = outcome.get("spof_skills", [])
        return MetricResult(
            kind=self.kind,
            name=self.name,
            data={"spof_skills": spof, "count": len(spof)},
        )
