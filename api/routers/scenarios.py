"""Scenario lifecycle: list/create, read (with time-travel), iterate phase, objectives, history."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from api.dependencies import load_scenario, require_domain, services
from core.iteration_engine import StepResult
from core.objectives import Objective
from core.scenario import Scenario

router = APIRouter(tags=["scenarios"])


class CreateScenarioRequest(BaseModel):
    domain: str
    name: str = Field(default="Untitled scenario", max_length=200)
    brief: str = Field(default="", max_length=500)  # free text -> Designer prompt; cap to limit injection
    n_entities: int = Field(default=8, ge=1, le=200)


class IterateRequest(BaseModel):
    phase: Literal["design", "iterate", "simulate", "judge"]


class ObjectivesRequest(BaseModel):
    objectives: list[Objective]


@router.get("/scenarios")
def list_scenarios() -> dict[str, list[dict[str, Any]]]:
    return {"scenarios": [s.model_dump() for s in services.event_log.list_scenarios()]}


@router.post("/scenarios")
def create_scenario(request: CreateScenarioRequest) -> Scenario:
    require_domain(request.domain)  # 404 if the domain isn't registered
    scenario = Scenario(
        id=uuid.uuid4().hex[:12],
        domain=request.domain,
        name=request.name,
        brief=request.brief,
        n_entities=request.n_entities,
    )
    services.event_log.init_scenario(scenario)
    return scenario


@router.get("/scenarios/{scenario_id}")
def get_scenario(scenario_id: str, at_seq: int | None = None) -> dict[str, Any]:
    """Current state, or the read-only state at ``at_seq`` (timeline scrubbing)."""
    scenario = load_scenario(scenario_id)
    branch = scenario.current_branch
    head = services.event_log.head(scenario_id, branch)
    target = head if at_seq is None else min(at_seq, head)
    state = services.replay.rebuild_state(scenario_id, target, branch)
    return {
        "scenario": scenario.model_dump(),
        "entities": state.entities,
        "head_seq": head,
        "at_seq": target,
    }


@router.post("/scenarios/{scenario_id}/iterate", response_model=StepResult)
def iterate(scenario_id: str, request: IterateRequest) -> StepResult:
    load_scenario(scenario_id)
    return services.engine.step(scenario_id, request.phase)


@router.post("/scenarios/{scenario_id}/objectives")
def set_objectives(scenario_id: str, request: ObjectivesRequest) -> dict[str, Any]:
    load_scenario(scenario_id)
    Objective.set_via_event(services.event_log, scenario_id, request.objectives)
    return {"objectives": [o.model_dump() for o in request.objectives]}


@router.get("/scenarios/{scenario_id}/history")
def get_history(scenario_id: str) -> dict[str, Any]:
    scenario = load_scenario(scenario_id)
    events = services.event_log.read(scenario_id, branch_id=scenario.current_branch)
    return {"events": [e.model_dump(mode="json") for e in events]}
