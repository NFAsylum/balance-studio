"""Tests for domains.team_composition.metrics — coverage, redundancy, SPOF, completion."""

from core.simulator_interface import RunResult
from domains.team_composition.metrics import (
    CompletionRate,
    Redundancy,
    SinglePointOfFailure,
    SkillCoverage,
)


def _run(**outcome):
    return RunResult(entities_involved=["a", "b"], outcome=outcome, duration_steps=1, seed=1)


def test_completion_rate_averages_over_runs():
    runs = [_run(completion_rate=0.8), _run(completion_rate=0.6)]
    data = CompletionRate().compute(runs).data
    assert data["mean"] == 0.7 and data["min"] == 0.6 and data["max"] == 0.8


def test_skill_coverage_reads_structural_outcome():
    runs = [_run(coverage=0.75, missing_skills=["ml"])]
    data = SkillCoverage().compute(runs).data
    assert data["coverage"] == 0.75 and data["missing_skills"] == ["ml"]


def test_redundancy():
    assert Redundancy().compute([_run(redundancy=2.5)]).data["redundancy"] == 2.5


def test_single_point_of_failure_lists_and_counts():
    data = SinglePointOfFailure().compute([_run(spof_skills=["security", "ml"])]).data
    assert data["spof_skills"] == ["security", "ml"] and data["count"] == 2
