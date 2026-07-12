"""Branching + diff over the scenario event log.

A branch forks from a point in a parent branch (the fork copies the shared prefix, so each
branch is self-contained). Diffing two branches reports the events unique to each, the
entities that diverged, and any divergence in the latest per-entity win rate.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from core.scenario import MAIN_BRANCH, EventLog
from core.snapshot import Replay


class BranchInfo(BaseModel):
    branch_id: str
    name: str
    head_seq: int
    event_count: int


class EntityDiff(BaseModel):
    only_in_a: list[str] = Field(default_factory=list)
    only_in_b: list[str] = Field(default_factory=list)
    changed: list[str] = Field(default_factory=list)


class DiffReport(BaseModel):
    branch_a: str
    branch_b: str
    exclusive_events_a: int
    exclusive_events_b: int
    entities: EntityDiff
    metrics_diff: dict[str, dict[str, float | None]]  # entity -> {"a": rate, "b": rate}


def _signature(event) -> str:
    """Content signature ignoring branch_id — copied-prefix events match across branches."""
    data = event.model_dump(mode="json")
    data.pop("branch_id", None)
    return json.dumps(data, sort_keys=True)


class Branch:
    def __init__(self, event_log: EventLog, replay: Replay):
        self.events = event_log
        self.replay = replay

    def create(
        self, scenario_id: str, parent_seq: int, name: str, parent_branch: str = MAIN_BRANCH
    ) -> str:
        """Fork a new branch named ``name`` from ``parent_branch`` at ``parent_seq``."""
        branch_id = name
        self.events.fork_branch(scenario_id, branch_id, name, parent_branch, parent_seq)
        return branch_id

    def list(self, scenario_id: str) -> list[BranchInfo]:
        infos: list[BranchInfo] = []
        for branch_id in self.events.branch_ids(scenario_id):
            meta = self.events.branch_meta(scenario_id, branch_id)
            events = self.events.read(scenario_id, branch_id=branch_id)
            infos.append(
                BranchInfo(
                    branch_id=branch_id,
                    name=meta["name"],
                    head_seq=max((e.seq for e in events), default=0),
                    event_count=len(events),
                )
            )
        return infos

    def diff(self, scenario_id: str, branch_a: str, branch_b: str) -> DiffReport:
        events_a = self.events.read(scenario_id, branch_id=branch_a)
        events_b = self.events.read(scenario_id, branch_id=branch_b)
        sigs_a = {_signature(e) for e in events_a}
        sigs_b = {_signature(e) for e in events_b}
        exclusive_a = sum(1 for e in events_a if _signature(e) not in sigs_b)
        exclusive_b = sum(1 for e in events_b if _signature(e) not in sigs_a)

        state_a = self.replay.rebuild_state(scenario_id, self._head(events_a), branch_a)
        state_b = self.replay.rebuild_state(scenario_id, self._head(events_b), branch_b)
        entities = self._entity_diff(state_a.entities, state_b.entities)

        winrate_a = self._latest_winrate(events_a)
        winrate_b = self._latest_winrate(events_b)
        metrics_diff = {
            key: {"a": winrate_a.get(key), "b": winrate_b.get(key)}
            for key in set(winrate_a) | set(winrate_b)
            if winrate_a.get(key) != winrate_b.get(key)
        }

        return DiffReport(
            branch_a=branch_a,
            branch_b=branch_b,
            exclusive_events_a=exclusive_a,
            exclusive_events_b=exclusive_b,
            entities=entities,
            metrics_diff=metrics_diff,
        )

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _head(events) -> int:
        return max((e.seq for e in events), default=0)

    @staticmethod
    def _entity_diff(a: dict[str, Any], b: dict[str, Any]) -> EntityDiff:
        return EntityDiff(
            only_in_a=sorted(set(a) - set(b)),
            only_in_b=sorted(set(b) - set(a)),
            changed=sorted(k for k in set(a) & set(b) if a[k] != b[k]),
        )

    @staticmethod
    def _latest_winrate(events) -> dict[str, float]:
        for event in reversed(events):
            if event.kind == "simulate" and event.after:
                metrics = event.after.get("metrics", {})
                return metrics.get("winrate_distribution", {}).get("data", {}).get("per_entity", {})
        return {}
