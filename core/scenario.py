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
from core.paths import safe_under, validate_id

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
    brief: str = ""  # design prompt for the Designer hat
    n_entities: int = 8  # how many entities the design phase targets
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
        # Parse cache: the log is append-only, so file size is a sound invalidation key — a
        # grown file means new events. This turns repeated read()/head() calls (previously each
        # a full re-parse -> O(N^2) across a session) into one parse per size change.
        self._parse_cache: dict[str, tuple[int, list[Event]]] = {}

    # -- paths -------------------------------------------------------------

    def _dir(self, scenario_id: str) -> Path:
        validate_id(scenario_id, "scenario_id")
        return safe_under(self.base, scenario_id)

    def _events_path(self, scenario_id: str) -> Path:
        return self._dir(scenario_id) / "events.jsonl"

    def _manifest_path(self, scenario_id: str) -> Path:
        return self._dir(scenario_id) / "manifest.json"

    # -- scenario / branch lifecycle --------------------------------------

    def init_scenario(self, scenario: Scenario) -> None:
        """Create the scenario folder, an empty event log, and register ``main``."""
        self._dir(scenario.id).mkdir(parents=True, exist_ok=True)
        self._events_path(scenario.id).touch()
        main_meta = {MAIN_BRANCH: {"name": MAIN_BRANCH, "parent_branch": None, "fork_seq": 0}}
        self._write_manifest(scenario, main_meta)

    def _write_manifest(self, scenario: Scenario, branches: dict[str, dict[str, Any]]) -> None:
        payload = {"scenario": scenario.model_dump(mode="json"), "branches": branches}
        self._manifest_path(scenario.id).write_text(json.dumps(payload, indent=2))

    def _read_manifest(self, scenario_id: str) -> tuple[Scenario, dict[str, dict[str, Any]]]:
        data = json.loads(self._manifest_path(scenario_id).read_text())
        return Scenario(**data["scenario"]), data["branches"]

    def scenario(self, scenario_id: str) -> Scenario:
        return self._read_manifest(scenario_id)[0]

    def list_scenarios(self) -> list[Scenario]:
        """Return every scenario under the base dir (folders with a manifest)."""
        if not self.base.exists():
            return []
        scenarios: list[Scenario] = []
        for child in sorted(self.base.iterdir()):
            if (child / "manifest.json").exists():
                scenarios.append(self.scenario(child.name))
        return scenarios

    def branch_ids(self, scenario_id: str) -> list[str]:
        return list(self._read_manifest(scenario_id)[1])

    def branch_meta(self, scenario_id: str, branch_id: str) -> dict[str, Any]:
        return self._read_manifest(scenario_id)[1][branch_id]

    def register_branch(
        self,
        scenario_id: str,
        branch_id: str,
        name: str | None = None,
        parent_branch: str | None = None,
        fork_seq: int = 0,
    ) -> None:
        validate_id(branch_id, "branch_id")
        scenario, branches = self._read_manifest(scenario_id)
        if branch_id not in branches:
            branches[branch_id] = {
                "name": name or branch_id,
                "parent_branch": parent_branch,
                "fork_seq": fork_seq,
            }
            self._write_manifest(scenario, branches)

    def fork_branch(
        self,
        scenario_id: str,
        new_branch: str,
        name: str,
        parent_branch: str,
        parent_seq: int,
    ) -> None:
        """Create ``new_branch`` by copying ``parent_branch``'s events up to ``parent_seq``.

        Copies re-tag ``branch_id`` only (seq/parent_seq/timestamp/content preserved), so each
        branch is self-contained and independent — an event on one never affects the other.
        """
        validate_id(new_branch, "branch_id")
        if new_branch in self.branch_ids(scenario_id):
            raise ValueError(f"branch '{new_branch}' already exists in scenario '{scenario_id}'")
        prefix = self.read(scenario_id, branch_id=parent_branch, up_to_seq=parent_seq)
        self.register_branch(scenario_id, new_branch, name, parent_branch, parent_seq)
        if prefix:
            with self._events_path(scenario_id).open("a", encoding="utf-8") as fh:
                fh.writelines(
                    e.model_copy(update={"branch_id": new_branch}).model_dump_json() + "\n"
                    for e in prefix
                )

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

    def set_scenario_objectives(self, scenario_id: str, objectives: list[Objective]) -> None:
        """Persist the scenario's objective list in the manifest (kept in sync with events)."""
        scenario, branches = self._read_manifest(scenario_id)
        scenario.objectives = objectives
        self._write_manifest(scenario, branches)

    def append_many(self, scenario_id: str, events: list[Event]) -> list[Event]:
        """Append several events to one branch atomically (single file write).

        All events must share a branch (the caller's phase). Seqs are assigned sequentially.
        Nothing is written if the branch is unregistered — this gives the iteration engine
        all-or-nothing steps: a phase that raises before calling this appends no events.
        """
        if not events:
            return []
        branch = events[0].branch_id
        scenario, branches = self._read_manifest(scenario_id)
        if branch not in branches:
            raise ValueError(f"branch '{branch}' not registered for scenario '{scenario_id}'")
        if any(e.branch_id != branch for e in events):
            raise ValueError("append_many requires all events on the same branch")

        head = self.head(scenario_id, branch)
        stored: list[Event] = []
        for offset, event in enumerate(events):
            seq = head + 1 + offset
            parent = seq - 1 if seq > 1 else event.parent_seq
            stored.append(event.model_copy(update={"seq": seq, "parent_seq": parent}))
        with self._events_path(scenario_id).open("a", encoding="utf-8") as fh:
            fh.writelines(e.model_dump_json() + "\n" for e in stored)

        if branch == scenario.current_branch:
            scenario.head_event_seq = stored[-1].seq
            self._write_manifest(scenario, branches)
        return stored

    def read(
        self,
        scenario_id: str,
        branch_id: str | None = None,
        up_to_seq: int | None = None,
    ) -> list[Event]:
        """Return events, optionally filtered by branch and capped at ``up_to_seq`` (inclusive)."""
        events = [
            e
            for e in self._read_all(scenario_id)
            if (branch_id is None or e.branch_id == branch_id)
            and (up_to_seq is None or e.seq <= up_to_seq)
        ]
        if branch_id is not None:
            events.sort(key=lambda e: e.seq)
        return events

    def _read_all(self, scenario_id: str) -> list[Event]:
        """Every event for a scenario, parsed once and cached until the log file grows."""
        path = self._events_path(scenario_id)
        try:
            size = path.stat().st_size
        except FileNotFoundError:
            return []
        cached = self._parse_cache.get(scenario_id)
        if cached is not None and cached[0] == size:
            return cached[1]
        with path.open(encoding="utf-8") as fh:
            events = [Event.model_validate_json(line) for line in fh if line.strip()]
        self._parse_cache[scenario_id] = (size, events)
        return events

    def head(self, scenario_id: str, branch_id: str) -> int:
        """Return the highest seq in ``branch_id`` (0 if the branch has no events yet)."""
        return max((e.seq for e in self._read_all(scenario_id) if e.branch_id == branch_id), default=0)
