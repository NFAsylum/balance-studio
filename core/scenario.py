"""Scenario state as an append-only event log.

The work on a scenario is a sequence of immutable events, not a mutable blob. Every change
— by the user or by an LLM hat — is appended to ``scenarios/<id>/events.jsonl``. State at
any point is rebuilt by replaying events (see :mod:`core.snapshot`). This gives time-travel,
branching, and portable scenarios (the whole ``scenarios/<id>/`` folder is the artifact).

``seq`` is monotonic *within a branch*; ``branch_id`` isolates parallel lines of exploration.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from core.objectives import Objective

Actor = Literal["user", "llm-designer", "llm-judge", "llm-iterator"]
EventKind = Literal[
    "create_entity",
    "edit_entity",
    "delete_entity",
    "simulate",
    "evaluate_subjective",
    "set_objective",
    "note",
]

MAIN_BRANCH = "main"


class Event(BaseModel):
    """One immutable change in a scenario's history."""

    seq: int = 0  # assigned by EventLog.append (monotonic per branch)
    parent_seq: int | None = None
    branch_id: str = MAIN_BRANCH
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actor: Actor
    kind: EventKind
    target: str  # entity_id or "scenario"
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Scenario(BaseModel):
    id: str
    domain: str
    name: str
    objectives: list[Objective] = Field(default_factory=list)
    head_event_seq: int = 0
    current_branch: str = MAIN_BRANCH


class EventLog:
    """Append-only event storage under ``<base_dir>/<scenario_id>/``.

    A branch must be registered before events can be appended to it (``main`` is registered
    when the scenario is created). Appending to an unknown branch raises ``ValueError``.
    """

    def __init__(self, base_dir: str | Path = "scenarios"):
        self.base = Path(base_dir)

    # -- paths -------------------------------------------------------------

    def _dir(self, scenario_id: str) -> Path:
        return self.base / scenario_id

    def _events_path(self, scenario_id: str) -> Path:
        return self._dir(scenario_id) / "events.jsonl"

    def _manifest_path(self, scenario_id: str) -> Path:
        return self._dir(scenario_id) / "manifest.json"

    # -- scenario / branch lifecycle --------------------------------------

    def init_scenario(self, scenario: Scenario) -> None:
        """Create the scenario folder, an empty event log, and register ``main``."""
        self._dir(scenario.id).mkdir(parents=True, exist_ok=True)
        self._events_path(scenario.id).touch()
        self._write_manifest(scenario, [MAIN_BRANCH])

    def _write_manifest(self, scenario: Scenario, branches: list[str]) -> None:
        payload = {"scenario": scenario.model_dump(mode="json"), "branches": branches}
        self._manifest_path(scenario.id).write_text(json.dumps(payload, indent=2))

    def _read_manifest(self, scenario_id: str) -> tuple[Scenario, list[str]]:
        data = json.loads(self._manifest_path(scenario_id).read_text())
        return Scenario(**data["scenario"]), data["branches"]

    def scenario(self, scenario_id: str) -> Scenario:
        return self._read_manifest(scenario_id)[0]

    def branches(self, scenario_id: str) -> list[str]:
        return self._read_manifest(scenario_id)[1]

    def register_branch(self, scenario_id: str, branch_id: str) -> None:
        scenario, branches = self._read_manifest(scenario_id)
        if branch_id not in branches:
            branches.append(branch_id)
            self._write_manifest(scenario, branches)

    # -- events ------------------------------------------------------------

    def append(self, scenario_id: str, event: Event) -> Event:
        """Append ``event`` to its branch, assigning an authoritative ``seq``/``parent_seq``.

        Returns the stored event (with seq filled in). Raises if the branch is unregistered.
        """
        scenario, branches = self._read_manifest(scenario_id)
        if event.branch_id not in branches:
            raise ValueError(
                f"branch '{event.branch_id}' not registered for scenario '{scenario_id}'"
            )
        head = self.head(scenario_id, event.branch_id)
        # First event of a non-main branch keeps the caller's parent_seq (the fork point);
        # otherwise parent is the previous event in this branch.
        parent = head if head > 0 else event.parent_seq
        stored = event.model_copy(update={"seq": head + 1, "parent_seq": parent})
        with self._events_path(scenario_id).open("a", encoding="utf-8") as fh:
            fh.write(stored.model_dump_json() + "\n")

        if stored.branch_id == scenario.current_branch:
            scenario.head_event_seq = stored.seq
            self._write_manifest(scenario, branches)
        return stored

    def read(
        self,
        scenario_id: str,
        branch_id: str | None = None,
        up_to_seq: int | None = None,
    ) -> list[Event]:
        """Return events, optionally filtered by branch and capped at ``up_to_seq`` (inclusive)."""
        events: list[Event] = []
        path = self._events_path(scenario_id)
        if not path.exists():
            return events
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                event = Event.model_validate_json(line)
                if branch_id is not None and event.branch_id != branch_id:
                    continue
                if up_to_seq is not None and event.seq > up_to_seq:
                    continue
                events.append(event)
        if branch_id is not None:
            events.sort(key=lambda e: e.seq)
        return events

    def head(self, scenario_id: str, branch_id: str) -> int:
        """Return the highest seq in ``branch_id`` (0 if the branch has no events yet)."""
        seqs = [e.seq for e in self.read(scenario_id, branch_id=branch_id)]
        return max(seqs, default=0)
