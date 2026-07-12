"""Team composition simulator — probabilistic workload completion.

Given a team of people and a workload (task types + deadline), greedily assigns each task to
a capable person with spare capacity (preferring those who prefer the task type), scaling
effort by seniority. Reports completion rate, average completion time, blocked tasks, and the
team's structural skill picture (coverage / redundancy / single points of failure).

Deterministic given the seed (which only shuffles task arrival order).
"""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict

from core.entity_schema import EntitySchema
from core.metrics.base import Metric
from core.simulator_interface import Environment, RunResult, SimulatorInterface
from domains.team_composition.metrics import (
    CompletionRate,
    Redundancy,
    SinglePointOfFailure,
    SkillCoverage,
)
from domains.team_composition.schema import (
    SENIORITY_SPEED,
    TASK_TYPES,
    TASK_TYPES_BY_NAME,
    TaskType,
    get_schema,
)


class WorkloadEnv(Environment):
    model_config = ConfigDict(extra="forbid")

    tasks: list[str] = []  # task type names; empty -> the full catalogue
    deadline_days: int = 10
    hours_per_day: int = 8


@dataclass
class _Worker:
    name: str
    seniority: str
    skills: set[str]
    preferred: set[str]
    remaining: float  # real hours of capacity left
    used: float = 0.0


def _to_dict(person: Any) -> dict[str, Any]:
    return person.model_dump() if isinstance(person, BaseModel) else dict(person)


class TeamCompositionSimulator(SimulatorInterface):
    def entity_schema(self) -> EntitySchema:
        return get_schema()

    def environment_schema(self) -> type[Environment]:
        return WorkloadEnv

    def default_metrics(self) -> list[Metric]:
        return [CompletionRate(), SkillCoverage(), Redundancy(), SinglePointOfFailure()]

    def llm_generation_prompt(self, constraints: list[Any]) -> str:
        return (
            "You are staffing a team. Generate people with a realistic spread of seniority "
            "(junior/mid/senior/lead) and complementary skills so the team covers the workload "
            "without single points of failure. Each person has 2-5 skills."
        )

    def run(self, entities: list[Any], env: Environment) -> RunResult:
        if not isinstance(env, WorkloadEnv):
            env = WorkloadEnv(**env.model_dump())
        people = [_to_dict(p) for p in entities]
        workload = self._workload(env)
        capacity = env.deadline_days * env.hours_per_day

        workers = [
            _Worker(
                name=p["name"],
                seniority=p["seniority"],
                skills=set(p.get("skills", [])),
                preferred=set(p.get("preferred_task_types", [])),
                remaining=float(capacity),
            )
            for p in people
        ]

        order = list(range(len(workload)))
        random.Random(env.seed).shuffle(order)

        completed_times: list[float] = []
        blocked = 0
        for idx in order:
            task = workload[idx]
            worker = self._assign(task, workers)
            if worker is None:
                blocked += 1
                continue
            effort = task.estimated_hours / SENIORITY_SPEED[worker.seniority]
            worker.remaining -= effort
            worker.used += effort
            completed_times.append(worker.used)

        analysis = _team_analysis(workers, workload)
        total = len(workload)
        outcome = {
            "completion_rate": (total - blocked) / total if total else 0.0,
            "avg_completion_hours": (sum(completed_times) / len(completed_times)) if completed_times else 0.0,
            "blocked_tasks": blocked,
            **analysis,
        }
        return RunResult(
            entities_involved=[w.name for w in workers],
            outcome=outcome,
            duration_steps=total,
            seed=env.seed,
        )

    @staticmethod
    def _workload(env: WorkloadEnv) -> list[TaskType]:
        if env.tasks:
            return [TASK_TYPES_BY_NAME[name] for name in env.tasks if name in TASK_TYPES_BY_NAME]
        return list(TASK_TYPES)

    @staticmethod
    def _assign(task: TaskType, workers: list[_Worker]) -> _Worker | None:
        """Pick a capable worker with enough capacity — preferring those who prefer the task."""
        required = set(task.required_skills)
        capable = [w for w in workers if required.issubset(w.skills)]
        if not capable:
            return None
        affordable = [w for w in capable if w.remaining >= task.estimated_hours / SENIORITY_SPEED[w.seniority]]
        if not affordable:
            return None
        # prefer someone who prefers this task type; then the most spare capacity; then name.
        return max(
            affordable,
            key=lambda w: (task.name in w.preferred, w.remaining, w.name),
        )


def _team_analysis(workers: list[_Worker], workload: list[TaskType]) -> dict[str, Any]:
    required = sorted({s for t in workload for s in t.required_skills})
    holders: Counter[str] = Counter()
    for skill in required:
        holders[skill] = sum(1 for w in workers if skill in w.skills)
    covered = [s for s in required if holders[s] > 0]
    return {
        "coverage": len(covered) / len(required) if required else 1.0,
        "missing_skills": [s for s in required if holders[s] == 0],
        "redundancy": (sum(holders.values()) / len(required)) if required else 0.0,
        "spof_skills": [s for s in required if holders[s] == 1],
    }
