"""Tests for core.iteration_engine — steps, auto loop, injection/authorship, atomicity."""

import pytest

from core.iteration_engine import IterationEngine
from core.llm_fakes import FakeDesigner, FakeIterator, FakeJudge
from core.llm_hats import Modification
from core.scenario import Event, EventLog, Scenario
from core.snapshot import Replay, SnapshotStore
from domains.card_game.simulator import CardGameSimulator


def _valid_unit(name, hp=5):
    return {
        "name": name,
        "cost": 2,
        "hp": hp,
        "damage": 3,
        "ability_kind": "heal",
        "ability_value": 2,
    }


class _NoopIterator:
    def propose_changes(self, entities, sim_metrics, judge_metrics, objectives):
        return []


class _StubIterator:
    """Proposes a harmless edit for every entity, ignoring metrics."""

    def propose_changes(self, entities, sim_metrics, judge_metrics, objectives):
        mods = []
        for e in entities:
            data = e.model_dump()
            payload = dict(data)
            payload["hp"] = min(20, data["hp"] + 1)
            mods.append(Modification(kind="edit", target=data["name"], payload=payload, reasoning="stub"))
        return mods


class _RaisingDesigner:
    def design(self, *args, **kwargs):
        raise RuntimeError("boom")


def _engine(tmp_path, *, designer=None, iterator=None, n_entities=4):
    log = EventLog(base_dir=tmp_path)
    replay = Replay(log, SnapshotStore(base_dir=tmp_path))
    engine = IterationEngine(
        log,
        replay,
        {"card_game": CardGameSimulator()},
        designer or FakeDesigner(),
        FakeJudge(),
        iterator or FakeIterator(),
        n_runs=30,
    )
    log.init_scenario(
        Scenario(id="s1", domain="card_game", name="T", brief="aggro cheap", n_entities=n_entities)
    )
    return log, replay, engine


def test_step_design_creates_entities(tmp_path):
    log, replay, engine = _engine(tmp_path)
    result = engine.step("s1", "design")
    assert result.events_appended == 4
    assert log.head("s1", "main") == 4
    state = replay.rebuild_state("s1", 4)
    assert len(state.entities) == 4


def test_step_simulate_records_metrics(tmp_path):
    log, _, engine = _engine(tmp_path)
    engine.step("s1", "design")
    result = engine.step("s1", "simulate")
    assert result.events_appended == 1
    assert result.details["winrate"]  # per-unit winrate present
    assert any(e.kind == "simulate" for e in log.read("s1", branch_id="main"))


def test_step_judge_records_score(tmp_path):
    _, _, engine = _engine(tmp_path)
    engine.step("s1", "design")
    result = engine.step("s1", "judge")
    assert 0.0 <= result.details["score"] <= 1.0


def test_auto_loop_converges_with_noop_iterator(tmp_path):
    _, _, engine = _engine(tmp_path, iterator=_NoopIterator())
    result = engine.auto_loop("s1", max_steps=5)
    assert result.converged is True
    phases = [s.phase for s in result.steps]
    assert phases[:4] == ["design", "simulate", "judge", "iterate"]


def test_user_injection_and_authorship_guardrail(tmp_path):
    log, replay, engine = _engine(tmp_path, iterator=_StubIterator())
    # An entity created by an LLM hat: the iterator may edit it.
    log.append("s1", Event(actor="llm-designer", kind="create_entity", target="Y", after=_valid_unit("Y")))
    applied_first = engine.step("s1", "iterate")
    assert applied_first.details["applied"] == 1
    assert applied_first.details["skipped_user_owned"] == []

    # Now the USER edits Y (an injection). The iterator must not overwrite it afterwards.
    log.append("s1", Event(actor="user", kind="edit_entity", target="Y", after=_valid_unit("Y", hp=12)))
    applied_second = engine.step("s1", "iterate")
    assert applied_second.details["applied"] == 0
    assert applied_second.details["skipped_user_owned"] == ["Y"]
    # the engine sees the user's version (hp=12), proving the injection was incorporated
    state = replay.rebuild_state("s1", log.head("s1", "main"))
    assert state.entities["Y"]["hp"] == 12


def test_atomic_rollback_on_error(tmp_path):
    log, _, engine = _engine(tmp_path, designer=_RaisingDesigner())
    with pytest.raises(RuntimeError):
        engine.step("s1", "design")
    # nothing was committed — the phase raised before append_many
    assert log.head("s1", "main") == 0
