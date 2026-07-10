"""Tests for core.objectives — weighted score, Pareto front, set_via_event."""

import pytest

from core.objectives import Candidate, Objective, ObjectiveAggregator
from core.scenario import EventLog, Scenario


def test_score_single_objective():
    objs = [Objective(metric_name="wr", direction="maximize", weight=1.0)]
    assert ObjectiveAggregator.score(objs, {"wr": 0.7}) == 0.7


def test_weight_zero_is_ignored():
    objs = [
        Objective(metric_name="wr", direction="maximize", weight=1.0),
        Objective(metric_name="std", direction="minimize", weight=0.0),
    ]
    # std would subtract if weighted, but weight 0 drops it
    assert ObjectiveAggregator.score(objs, {"wr": 0.7, "std": 0.3}) == 0.7


def test_target_value_penalises_distance():
    objs = [Objective(metric_name="balance", direction="target", target_value=0.5, weight=2.0)]
    assert ObjectiveAggregator.score(objs, {"balance": 0.5}) == 0.0
    assert ObjectiveAggregator.score(objs, {"balance": 0.7}) == pytest.approx(-0.4)  # -|0.7-0.5|*2


def test_pareto_front_with_two_conflicting_objectives():
    objs = [
        Objective(metric_name="a", direction="maximize"),
        Objective(metric_name="b", direction="maximize"),
    ]
    candidates = [
        Candidate(id="c1", metric_results={"a": 1.0, "b": 0.0}),
        Candidate(id="c2", metric_results={"a": 0.0, "b": 1.0}),
        Candidate(id="c3", metric_results={"a": 0.5, "b": 0.5}),
        Candidate(id="c4", metric_results={"a": 0.0, "b": 0.0}),  # dominated by all
    ]
    front = {c.id for c in ObjectiveAggregator.pareto_check(objs, candidates)}
    assert front == {"c1", "c2", "c3"}
    assert "c4" not in front


def test_set_via_event_records_and_mirrors_to_manifest(tmp_path):
    log = EventLog(base_dir=tmp_path)
    log.init_scenario(Scenario(id="s1", domain="card_game", name="T"))
    objs = [Objective(metric_name="wr", direction="target", target_value=0.5)]
    stored = Objective.set_via_event(log, "s1", objs)
    assert stored.kind == "set_objective"
    assert log.head("s1", "main") == 1
    # manifest reflects the objectives so the iteration engine sees them
    assert log.scenario("s1").objectives == objs
