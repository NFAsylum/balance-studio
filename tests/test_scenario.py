"""Tests for core.scenario — Event, Scenario, and the append-only EventLog."""

import pytest

from core.scenario import Event, EventLog, Scenario


def _log(tmp_path) -> EventLog:
    log = EventLog(base_dir=tmp_path)
    log.init_scenario(Scenario(id="s1", domain="card_game", name="Test"))
    return log


def _event(kind="note", actor="user", target="scenario", branch_id="main", **md) -> Event:
    return Event(actor=actor, kind=kind, target=target, branch_id=branch_id, metadata=md)


def test_append_and_read_round_trip(tmp_path):
    log = _log(tmp_path)
    log.append("s1", _event(note="hello"))
    events = log.read("s1")
    assert len(events) == 1
    assert events[0].metadata["note"] == "hello"
    assert events[0].kind == "note"


def test_sequencing_is_monotonic_per_branch(tmp_path):
    log = _log(tmp_path)
    for i in range(3):
        log.append("s1", _event(note=f"n{i}"))
    seqs = [e.seq for e in log.read("s1", branch_id="main")]
    assert seqs == [1, 2, 3]
    parents = [e.parent_seq for e in log.read("s1", branch_id="main")]
    assert parents == [None, 1, 2]


def test_head_tracks_last_seq(tmp_path):
    log = _log(tmp_path)
    assert log.head("s1", "main") == 0
    log.append("s1", _event())
    log.append("s1", _event())
    assert log.head("s1", "main") == 2
    assert log.scenario("s1").head_event_seq == 2


def test_branch_isolation(tmp_path):
    log = _log(tmp_path)
    log.register_branch("s1", "alt")
    log.append("s1", _event(note="m1", branch_id="main"))
    log.append("s1", _event(note="m2", branch_id="main"))
    log.append("s1", _event(note="a1", branch_id="alt"))

    main = log.read("s1", branch_id="main")
    alt = log.read("s1", branch_id="alt")
    assert [e.metadata["note"] for e in main] == ["m1", "m2"]
    assert [e.metadata["note"] for e in alt] == ["a1"]
    # each branch numbers seq independently
    assert log.head("s1", "main") == 2
    assert log.head("s1", "alt") == 1


def test_up_to_seq_slice(tmp_path):
    log = _log(tmp_path)
    for i in range(5):
        log.append("s1", _event(note=f"n{i}"))
    sliced = log.read("s1", branch_id="main", up_to_seq=3)
    assert [e.seq for e in sliced] == [1, 2, 3]


def test_append_to_unregistered_branch_fails(tmp_path):
    log = _log(tmp_path)
    with pytest.raises(ValueError, match="not registered"):
        log.append("s1", _event(branch_id="ghost"))
