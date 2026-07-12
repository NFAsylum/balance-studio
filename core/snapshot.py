"""Snapshots + replay.

A snapshot is materialised state at a point in the event log, stored zstd-compressed at
``scenarios/<id>/snapshots/<branch>-seq-<N>.json.zst``. Replay rebuilds state at any target
seq by loading the nearest snapshot at or before it and applying the events in between — so
time-travel stays fast even on long histories. Auto-snapshot every ``interval`` events keeps
that gap bounded.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import zstandard
from pydantic import BaseModel, Field

from core.paths import safe_under, validate_id
from core.scenario import MAIN_BRANCH, Event, EventLog

_ENTITY_EVENTS = {"create_entity", "edit_entity", "delete_entity"}


class Snapshot(BaseModel):
    scenario_id: str
    at_seq: int
    branch_id: str = MAIN_BRANCH
    entities: dict[str, dict[str, Any]] = Field(default_factory=dict)
    env: dict[str, Any] = Field(default_factory=dict)
    sim_results_index: dict[str, str] = Field(default_factory=dict)


class SnapshotInfo(BaseModel):
    scenario_id: str
    at_seq: int
    branch_id: str


class State(BaseModel):
    """Materialised entity state at a point in a branch's history."""

    scenario_id: str
    at_seq: int
    branch_id: str
    entities: dict[str, dict[str, Any]] = Field(default_factory=dict)
    env: dict[str, Any] = Field(default_factory=dict)


class SnapshotStore:
    """Persists compressed snapshots under ``<base_dir>/<scenario_id>/snapshots/``."""

    def __init__(self, base_dir: str | Path = "scenarios"):
        self.base = Path(base_dir)

    def _dir(self, scenario_id: str) -> Path:
        validate_id(scenario_id, "scenario_id")
        return safe_under(self.base, scenario_id, "snapshots")

    def _path(self, scenario_id: str, branch_id: str, at_seq: int) -> Path:
        validate_id(branch_id, "branch_id")
        return safe_under(self._dir(scenario_id), f"{branch_id}-seq-{at_seq}.json.zst")

    def save(self, snapshot: Snapshot) -> Path:
        self._dir(snapshot.scenario_id).mkdir(parents=True, exist_ok=True)
        raw = snapshot.model_dump_json().encode("utf-8")
        compressed = zstandard.ZstdCompressor().compress(raw)
        path = self._path(snapshot.scenario_id, snapshot.branch_id, snapshot.at_seq)
        path.write_bytes(compressed)
        return path

    def load(self, scenario_id: str, at_seq: int, branch_id: str = MAIN_BRANCH) -> Snapshot:
        compressed = self._path(scenario_id, branch_id, at_seq).read_bytes()
        raw = zstandard.ZstdDecompressor().decompress(compressed)
        return Snapshot.model_validate_json(raw)

    def list(self, scenario_id: str, branch_id: str = MAIN_BRANCH) -> list[SnapshotInfo]:
        directory = self._dir(scenario_id)
        if not directory.exists():
            return []
        infos: list[SnapshotInfo] = []
        for path in directory.glob(f"{branch_id}-seq-*.json.zst"):
            at_seq = int(path.stem.split("-seq-")[1].removesuffix(".json"))
            infos.append(SnapshotInfo(scenario_id=scenario_id, at_seq=at_seq, branch_id=branch_id))
        infos.sort(key=lambda s: s.at_seq)
        return infos

    def nearest(
        self, scenario_id: str, target_seq: int, branch_id: str = MAIN_BRANCH
    ) -> SnapshotInfo | None:
        """Return the latest snapshot at or before ``target_seq``, or None."""
        candidates = [s for s in self.list(scenario_id, branch_id) if s.at_seq <= target_seq]
        return max(candidates, key=lambda s: s.at_seq, default=None)


def _apply_event(entities: dict[str, dict[str, Any]], event: Event) -> None:
    """Fold one event into the entity map. Non-entity events are ignored."""
    if event.kind == "create_entity" or event.kind == "edit_entity":
        entities[event.target] = event.after or {}
    elif event.kind == "delete_entity":
        entities.pop(event.target, None)


class Replay:
    """Rebuilds state from snapshots + events."""

    def __init__(self, event_log: EventLog, snapshot_store: SnapshotStore):
        self.events = event_log
        self.snapshots = snapshot_store

    def rebuild_state(
        self, scenario_id: str, target_seq: int, branch_id: str = MAIN_BRANCH
    ) -> State:
        """Load the nearest snapshot ≤ target_seq, then apply events up to target_seq."""
        info = self.snapshots.nearest(scenario_id, target_seq, branch_id)
        if info is not None:
            snap = self.snapshots.load(scenario_id, info.at_seq, branch_id)
            entities = dict(snap.entities)
            env = dict(snap.env)
            from_seq = info.at_seq
        else:
            entities, env, from_seq = {}, {}, 0

        for event in self.events.read(scenario_id, branch_id=branch_id, up_to_seq=target_seq):
            if event.seq <= from_seq:
                continue
            if event.kind in _ENTITY_EVENTS:
                _apply_event(entities, event)

        return State(
            scenario_id=scenario_id,
            at_seq=target_seq,
            branch_id=branch_id,
            entities=entities,
            env=env,
        )

    def snapshot_now(
        self,
        scenario_id: str,
        branch_id: str = MAIN_BRANCH,
        env: dict[str, Any] | None = None,
    ) -> Snapshot:
        """Materialise and persist a snapshot at the branch's current head."""
        head = self.events.head(scenario_id, branch_id)
        state = self.rebuild_state(scenario_id, head, branch_id)
        snapshot = Snapshot(
            scenario_id=scenario_id,
            at_seq=head,
            branch_id=branch_id,
            entities=state.entities,
            env=env if env is not None else state.env,
        )
        self.snapshots.save(snapshot)
        return snapshot

    def auto_snapshot_if_due(
        self,
        scenario_id: str,
        branch_id: str = MAIN_BRANCH,
        interval: int = 50,
        env: dict[str, Any] | None = None,
    ) -> Snapshot | None:
        """Snapshot when the branch head is a positive multiple of ``interval``."""
        head = self.events.head(scenario_id, branch_id)
        if head > 0 and head % interval == 0:
            return self.snapshot_now(scenario_id, branch_id, env)
        return None
