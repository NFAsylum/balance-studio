"""Event-based iteration engine.

No rigid state machine — each ``step`` reads the *current* materialised state (via replay),
runs one phase against the LLM hats / simulator, and appends the resulting events atomically.
Because every step rebuilds state fresh, a user event injected between steps is automatically
incorporated. The iterator hat's proposals are filtered by authorship: an entity whose last
change was made by the user is never overwritten.
"""

from __future__ import annotations

import os
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from core.cache_backend import DiskCacheBackend
from core.llm_hats import DesignerLlm, IteratorLlm, SubjectiveJudgeLlm
from core.scenario import Event, EventLog
from core.sim_cache import IncrementalSimRunner, SimCache
from core.simulator_interface import SimulatorInterface
from core.snapshot import Replay

Phase = Literal["design", "iterate", "simulate", "judge"]
_ENTITY_KINDS = {"create_entity", "edit_entity", "delete_entity"}
_MOD_TO_KIND = {"create": "create_entity", "edit": "edit_entity", "delete": "delete_entity"}
_JUDGE_CRITERION = "variety"


class StepResult(BaseModel):
    phase: str
    events_appended: int
    details: dict[str, Any] = Field(default_factory=dict)


class LoopResult(BaseModel):
    steps: list[StepResult]
    converged: bool
    injections_detected: int


class IterationEngine:
    def __init__(
        self,
        event_log: EventLog,
        replay: Replay,
        domains: dict[str, SimulatorInterface],
        designer: DesignerLlm,
        judge: SubjectiveJudgeLlm,
        iterator: IteratorLlm,
        sim_seed: int = 42,
        n_runs: int = 100,
        snapshot_interval: int = 50,
    ):
        self.events = event_log
        self.replay = replay
        self.domains = domains
        self.designer = designer
        self.judge = judge
        self.iterator = iterator
        self.sim_seed = sim_seed
        self.n_runs = n_runs
        self.snapshot_interval = snapshot_interval

    # -- public API --------------------------------------------------------

    def step(self, scenario_id: str, phase: Phase) -> StepResult:
        scenario = self.events.scenario(scenario_id)
        branch = scenario.current_branch
        head = self.events.head(scenario_id, branch)
        state = self.replay.rebuild_state(scenario_id, head, branch)
        simulator = self.domains[scenario.domain]
        model = simulator.entity_schema().build_model()
        instances = [model(**data) for data in state.entities.values()]

        if phase == "design":
            return self._design(scenario_id, branch, scenario, state.entities)
        if phase == "simulate":
            return self._simulate(scenario_id, branch, simulator, instances)
        if phase == "judge":
            return self._judge(scenario_id, branch, instances)
        if phase == "iterate":
            return self._iterate(scenario_id, branch, scenario, state.entities, instances)
        raise ValueError(f"unknown phase: {phase}")  # pragma: no cover

    def auto_loop(
        self, scenario_id: str, max_steps: int = 10, stop_on_convergence: bool = True
    ) -> LoopResult:
        scenario = self.events.scenario(scenario_id)
        branch = scenario.current_branch
        steps: list[StepResult] = []
        injections = 0

        state = self.replay.rebuild_state(scenario_id, self.events.head(scenario_id, branch), branch)
        if not state.entities:
            steps.append(self.step(scenario_id, "design"))

        expected_head = self.events.head(scenario_id, branch)
        converged = False
        for _ in range(max_steps):
            if self.events.head(scenario_id, branch) != expected_head:
                injections += 1  # a non-engine event landed between cycles
            steps.append(self.step(scenario_id, "simulate"))
            steps.append(self.step(scenario_id, "judge"))
            iterate = self.step(scenario_id, "iterate")
            steps.append(iterate)
            self.replay.auto_snapshot_if_due(scenario_id, branch, self.snapshot_interval)
            expected_head = self.events.head(scenario_id, branch)
            if stop_on_convergence and iterate.details.get("applied", 0) == 0:
                converged = True
                break

        return LoopResult(steps=steps, converged=converged, injections_detected=injections)

    # -- phases ------------------------------------------------------------

    def _design(self, scenario_id, branch, scenario, existing) -> StepResult:
        if existing:
            return StepResult(phase="design", events_appended=0, details={"skipped": "not empty"})
        designed = self.designer.design(scenario.brief, self.domains[scenario.domain].entity_schema(), [], scenario.n_entities)
        events = [
            Event(branch_id=branch, actor="llm-designer", kind="create_entity", target=d["name"], after=d)
            for d in (e.model_dump() for e in designed)
        ]
        stored = self.events.append_many(scenario_id, events)
        return StepResult(phase="design", events_appended=len(stored), details={"n_designed": len(designed)})

    def _simulate(self, scenario_id, branch, simulator, instances) -> StepResult:
        if not instances:
            return StepResult(phase="simulate", events_appended=0, details={"skipped": "no entities"})
        env = simulator.environment_schema()(seed=self.sim_seed)
        # Incremental cache per scenario: re-running only re-simulates matchups that changed.
        # Disk (dev, portable per-scenario dir) or Redis (prod) via CACHE_BACKEND; keys are
        # namespaced by scenario so a shared Redis stays isolated.
        cache = SimCache(self._cache_backend(scenario_id), key_prefix=scenario_id)
        runner = IncrementalSimRunner(simulator, cache, self.events)
        report = runner.run(scenario_id, instances, env, self.n_runs, kind="full", branch=branch)
        winrate = report.metrics.get("winrate_distribution", {}).get("data", {}).get("per_entity", {})
        return StepResult(
            phase="simulate",
            events_appended=1,
            details={
                "n_runs": report.n_runs,
                "winrate": winrate,
                "matchups_reused": report.matchups_reused,
                "matchups_computed": report.matchups_computed,
            },
        )

    def _judge(self, scenario_id, branch, instances) -> StepResult:
        if not instances:
            return StepResult(phase="judge", events_appended=0, details={"skipped": "no entities"})
        result = self.judge.judge(instances, _JUDGE_CRITERION)
        event = Event(
            branch_id=branch,
            actor="llm-judge",
            kind="evaluate_subjective",
            target="scenario",
            after={"criterion": _JUDGE_CRITERION, "score": result.score},
            metadata={"rationale": result.rationale},
        )
        self.events.append_many(scenario_id, [event])
        return StepResult(phase="judge", events_appended=1, details={"score": result.score})

    def _iterate(self, scenario_id, branch, scenario, entities_data, instances) -> StepResult:
        if not instances:
            return StepResult(phase="iterate", events_appended=0, details={"skipped": "no entities"})
        sim_metrics = {"winrate": self._latest_winrate(scenario_id, branch)}
        judge_metrics = self._latest_judge(scenario_id, branch)
        mods = self.iterator.propose_changes(instances, sim_metrics, judge_metrics, scenario.objectives)

        model_cls = self.domains[scenario.domain].entity_schema().build_model()
        last_actor = self._last_actor_by_target(scenario_id, branch)
        events: list[Event] = []
        skipped: list[str] = []
        rejected = 0
        for mod in mods:
            # Authorship guardrail: never overwrite an entity the user last touched.
            if mod.target and last_actor.get(mod.target) == "user":
                skipped.append(mod.target)
                continue
            # Reject create/edit whose payload doesn't validate — never commit invalid state.
            if mod.kind != "delete" and not _valid_payload(model_cls, mod.payload):
                rejected += 1
                continue
            target = mod.target or str(mod.payload.get("name", "new_entity"))
            events.append(
                Event(
                    branch_id=branch,
                    actor="llm-iterator",
                    kind=_MOD_TO_KIND[mod.kind],
                    target=target,
                    before=entities_data.get(target) if mod.target else None,
                    after=None if mod.kind == "delete" else mod.payload,
                    metadata={"reasoning": mod.reasoning},
                )
            )
        stored = self.events.append_many(scenario_id, events) if events else []
        return StepResult(
            phase="iterate",
            events_appended=len(stored),
            details={
                "proposed": len(mods),
                "applied": len(stored),
                "skipped_user_owned": skipped,
                "rejected_invalid": rejected,
            },
        )

    # -- helpers -----------------------------------------------------------

    def _cache_backend(self, scenario_id: str):
        if os.getenv("CACHE_BACKEND", "disk").lower() == "redis":
            from core.cache_backend import RedisCacheBackend

            return RedisCacheBackend()
        return DiskCacheBackend(self.events.base / scenario_id / "sim_cache")

    def _last_actor_by_target(self, scenario_id, branch) -> dict[str, str]:
        actors: dict[str, str] = {}
        for event in self.events.read(scenario_id, branch_id=branch):
            if event.kind in _ENTITY_KINDS:
                actors[event.target] = event.actor
        return actors

    def _latest_winrate(self, scenario_id, branch) -> dict[str, float]:
        for event in reversed(self.events.read(scenario_id, branch_id=branch)):
            if event.kind == "simulate" and event.after:
                metrics = event.after.get("metrics", {})
                return metrics.get("winrate_distribution", {}).get("data", {}).get("per_entity", {})
        return {}

    def _latest_judge(self, scenario_id, branch) -> dict[str, float]:
        for event in reversed(self.events.read(scenario_id, branch_id=branch)):
            if event.kind == "evaluate_subjective" and event.after:
                return {event.after["criterion"]: event.after["score"]}
        return {}


def _valid_payload(model_cls: type[BaseModel], payload: dict[str, Any]) -> bool:
    """True if an iterator's modification payload validates against the entity schema."""
    try:
        model_cls(**payload)
        return True
    except (ValidationError, TypeError):
        return False
