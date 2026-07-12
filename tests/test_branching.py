"""Tests for core.branching — fork, list, diff, and branch independence."""

from core.branching import Branch
from core.scenario import Event, EventLog, Scenario
from core.snapshot import Replay, SnapshotStore


def _setup(tmp_path):
    log = EventLog(base_dir=tmp_path)
    log.init_scenario(Scenario(id="s1", domain="card_game", name="T"))
    branch = Branch(log, Replay(log, SnapshotStore(base_dir=tmp_path)))
    return log, branch


def _create(entity_id, **fields):
    return Event(actor="llm-designer", kind="create_entity", target=entity_id, after=fields)


def test_create_branch_copies_prefix(tmp_path):
    log, branch = _setup(tmp_path)
    log.append("s1", _create("u1", hp=5))
    log.append("s1", _create("u2", hp=9))
    branch_id = branch.create("s1", parent_seq=2, name="alt")
    assert branch_id == "alt"
    # alt inherits the 2-event prefix
    assert log.head("s1", "alt") == 2
    assert len(log.read("s1", branch_id="alt")) == 2


def test_list_branches(tmp_path):
    log, branch = _setup(tmp_path)
    log.append("s1", _create("u1", hp=5))
    branch.create("s1", parent_seq=1, name="experiment")
    infos = {b.branch_id: b for b in branch.list("s1")}
    assert set(infos) == {"main", "experiment"}
    assert infos["main"].event_count == 1
    assert infos["experiment"].name == "experiment"
    assert infos["experiment"].head_seq == 1


def test_branches_are_independent(tmp_path):
    log, branch = _setup(tmp_path)
    log.append("s1", _create("u1", hp=5))
    branch.create("s1", parent_seq=1, name="alt")
    # append only to alt
    log.append("s1", Event(actor="user", kind="edit_entity", target="u1", after={"hp": 99}, branch_id="alt"))
    assert log.head("s1", "main") == 1  # main untouched
    assert log.head("s1", "alt") == 2


def test_diff_reports_exclusive_events_symmetrically(tmp_path):
    log, branch = _setup(tmp_path)
    log.append("s1", _create("u1", hp=5))
    branch.create("s1", parent_seq=1, name="alt")
    # diverge: different second event on each branch
    log.append("s1", Event(actor="user", kind="note", target="scenario", metadata={"m": "main-note"}))
    log.append("s1", Event(actor="user", kind="note", target="scenario", metadata={"m": "alt-note"}, branch_id="alt"))

    d = branch.diff("s1", "main", "alt")
    assert d.exclusive_events_a == 1
    assert d.exclusive_events_b == 1
    # symmetry: swapping arguments swaps the counts
    d2 = branch.diff("s1", "alt", "main")
    assert d2.exclusive_events_a == d.exclusive_events_b
    assert d2.exclusive_events_b == d.exclusive_events_a


def test_diff_reports_divergent_entities(tmp_path):
    log, branch = _setup(tmp_path)
    log.append("s1", _create("shared", hp=5))
    log.append("s1", _create("common", hp=3))
    branch.create("s1", parent_seq=2, name="alt")
    # main edits 'common'; alt adds a new entity
    log.append("s1", Event(actor="user", kind="edit_entity", target="common", after={"hp": 10}))
    log.append("s1", _create("alt_only", hp=1).model_copy(update={"branch_id": "alt"}))

    d = branch.diff("s1", "main", "alt")
    assert d.entities.only_in_b == ["alt_only"]
    assert "common" in d.entities.changed
    assert d.entities.only_in_a == []
