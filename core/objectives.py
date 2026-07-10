"""Multi-objective definitions + aggregation.

A user composes several :class:`Objective` entries (numeric balance, variety, cohesion, …).
:class:`ObjectiveAggregator` collapses them into one weighted score, or — when objectives
conflict — returns the Pareto front of candidate designs so trade-offs stay visible.

Values are treated as already scalarised per metric name; higher aggregate score is better.
No cross-metric normalisation is applied (weights are the tuning knob).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from core.scenario import Event, EventLog


class Objective(BaseModel):
    metric_name: str
    direction: Literal["minimize", "maximize", "target"]
    target_value: float | None = None
    weight: float = 1.0

    @staticmethod
    def set_via_event(
        event_log: EventLog, scenario_id: str, objectives: list[Objective]
    ) -> Event:
        """Record objectives as a ``set_objective`` event and mirror them into the manifest."""
        from core.scenario import Event  # local import avoids a scenario<->objectives cycle

        event = Event(
            actor="user",
            kind="set_objective",
            target="scenario",
            after={"objectives": [o.model_dump() for o in objectives]},
        )
        stored = event_log.append(scenario_id, event)
        event_log.set_scenario_objectives(scenario_id, objectives)
        return stored


class Candidate(BaseModel):
    id: str
    metric_results: dict[str, float] = Field(default_factory=dict)


class ObjectiveAggregator:
    @staticmethod
    def _utility(objective: Objective, value: float) -> float:
        """Map a raw metric value to a 'higher is better' utility for its direction."""
        if objective.direction == "maximize":
            return value
        if objective.direction == "minimize":
            return -value
        target = objective.target_value if objective.target_value is not None else 0.0
        return -abs(value - target)  # 'target': closer is better

    @staticmethod
    def score(objectives: list[Objective], metric_results: dict[str, float]) -> float:
        """Weighted sum of per-objective utilities. Weight 0 or a missing metric is ignored."""
        total = 0.0
        for objective in objectives:
            if objective.weight == 0 or objective.metric_name not in metric_results:
                continue
            total += objective.weight * ObjectiveAggregator._utility(
                objective, metric_results[objective.metric_name]
            )
        return total

    @staticmethod
    def pareto_check(
        objectives: list[Objective], candidates: list[Candidate]
    ) -> list[Candidate]:
        """Return the non-dominated candidates (the Pareto front) across all objectives."""
        utils = [
            [ObjectiveAggregator._utility(o, c.metric_results.get(o.metric_name, 0.0)) for o in objectives]
            for c in candidates
        ]
        front: list[Candidate] = []
        for i, candidate in enumerate(candidates):
            if not any(_dominates(utils[j], utils[i]) for j in range(len(candidates)) if j != i):
                front.append(candidate)
        return front


def _dominates(a: list[float], b: list[float]) -> bool:
    """True if utility vector ``a`` dominates ``b`` (>= on all, > on at least one)."""
    return all(x >= y for x, y in zip(a, b)) and any(x > y for x, y in zip(a, b))
