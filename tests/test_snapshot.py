"""Tests for core.snapshot — SnapshotStore (zstd), Replay, auto-snapshot."""

from core.scenario import Event, EventLog, Scenario
from core.snapshot import Replay, Snapshot, SnapshotStore


def _setup(tmp_path):
    log = EventLog(base_dir=tmp_path)
    log.init_scenario(Scenario(id="s1", domain="card_game", name="T"))
    store = SnapshotStore(base_dir=tmp_path)
    return log, store, Replay(log, store)


def _create(entity_id, **fields):
    return Event(actor="llm-designer", kind="create_entity", target=entity_id, after=fields)


def test_save_load_round_trip(tmp_path):
    _, store, _ = _setup(tmp_path)
    snap = Snapshot(scenario_id="s1", at_seq=3, entities={"u1": {"hp": 5}}, env={"seed": 1})
    store.save(snap)
    loaded = store.load("s1", 3)
    assert loaded == snap


def test_replay_is_deterministic(tmp_path):
    log, _, replay = _setup(tmp_path)
    log.append("s1", _create("u1", hp=5))
    log.append("s1", _create("u2", hp=9))
    log.append("s1", Event(actor="user", kind="edit_entity", target="u1", after={"hp": 7}))
    log.append("s1", Event(actor="user", kind="delete_entity", target="u2"))
    a = replay.rebuild_state("s1", target_seq=4)
    b = replay.rebuild_state("s1", target_seq=4)
    assert a.entities == b.entities == {"u1": {"hp": 7}}


def test_rebuild_uses_nearest_snapshot(tmp_path):
    log, store, replay = _setup(tmp_path)
    log.append("s1", _create("u1", hp=5))
    log.append("s1", _create("u2", hp=9))
    # Snapshot at seq 2 with a value that CANNOT be reconstructed from events alone,
    # proving the snapshot (not a from-scratch replay) is the base.
    store.save(Snapshot(scenario_id="s1", at_seq=2, entities={"u1": {"hp": 999}, "u2": {"hp": 9}}))
    log.append("s1", Event(actor="user", kind="edit_entity", target="u2", after={"hp": 3}))

    assert store.nearest("s1", 3).at_seq == 2
    state = replay.rebuild_state("s1", target_seq=3)
    # u1 comes from the snapshot (999, not 5); u2 edited after the snapshot
    assert state.entities == {"u1": {"hp": 999}, "u2": {"hp": 3}}


def test_absent_snapshot_replays_from_scratch(tmp_path):
    log, store, replay = _setup(tmp_path)
    log.append("s1", _create("u1", hp=5))
    log.append("s1", _create("u2", hp=9))
    assert store.nearest("s1", 2) is None
    state = replay.rebuild_state("s1", target_seq=2)
    assert state.entities == {"u1": {"hp": 5}, "u2": {"hp": 9}}


def test_compression_reduces_size(tmp_path):
    _, store, _ = _setup(tmp_path)
    # a repetitive snapshot compresses well
    entities = {f"u{i}": {"name": "Repeated Unit Name", "hp": 5, "cost": 2} for i in range(200)}
    snap = Snapshot(scenario_id="s1", at_seq=1, entities=entities)
    path = store.save(snap)
    raw_len = len(snap.model_dump_json().encode())
    compressed_len = path.stat().st_size
    assert compressed_len < raw_len


def test_auto_snapshot_every_interval(tmp_path):
    log, store, replay = _setup(tmp_path)
    for _ in range(5):
        log.append("s1", Event(actor="user", kind="note", target="scenario"))
    assert replay.auto_snapshot_if_due("s1", interval=5) is not None
    assert store.nearest("s1", 5).at_seq == 5
    # not due at a non-multiple
    log.append("s1", Event(actor="user", kind="note", target="scenario"))
    assert replay.auto_snapshot_if_due("s1", interval=5) is None
