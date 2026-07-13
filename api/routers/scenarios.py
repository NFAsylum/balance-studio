"""Scenario lifecycle: list/create, read (with time-travel), iterate phase, objectives, history."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ValidationError

from api.dependencies import load_scenario, require_domain, services
from api.registry import registry
from core.iteration_engine import StepResult
from core.objectives import Objective
from core.presets import PresetStore
from core.scenario import Scenario

router = APIRouter(tags=["scenarios"])

_presets = PresetStore()


class CreateScenarioRequest(BaseModel):
    domain: str
    name: str = Field(default="Untitled scenario", max_length=200)
    brief: str = Field(default="", max_length=500)  # free text -> Designer prompt; cap to limit injection
    n_entities: int = Field(default=8, ge=1, le=200)
    preset_id: str | None = None  # start from a preset (schema + constraints + objectives + variant)
    schema_overrides: dict[str, Any] = Field(default_factory=dict)  # extra edits on top of the preset
    constraints: list[dict[str, Any]] | None = None  # design-time constraints (None = keep preset's)
    visual_variant: str | None = None  # override the preset's default view


def _merge_overrides(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    """Concatenate field ops (base first) so later ops — the user's — win field-by-field."""
    fields = list(base.get("fields", [])) + list(extra.get("fields", []))
    return {"fields": fields} if fields else {}


class IterateRequest(BaseModel):
    phase: Literal["design", "iterate", "simulate", "judge"]


class ObjectivesRequest(BaseModel):
    objectives: list[Objective]


@router.get("/scenarios")
def list_scenarios() -> dict[str, list[dict[str, Any]]]:
    return {"scenarios": [s.model_dump() for s in services.event_log.list_scenarios()]}


@router.post("/scenarios")
def create_scenario(request: CreateScenarioRequest) -> Scenario:
    simulator = require_domain(request.domain)  # 404 if the domain isn't registered

    preset = None
    if request.preset_id:
        preset = _presets.get(request.preset_id)
        if preset is None:
            raise HTTPException(status_code=422, detail=f"unknown preset '{request.preset_id}'")
        if preset.domain != request.domain:
            raise HTTPException(
                status_code=422,
                detail=f"preset '{request.preset_id}' is for domain '{preset.domain}', not '{request.domain}'",
            )

    overrides = _merge_overrides(preset.schema_overrides if preset else {}, request.schema_overrides)
    # Fail early (422) if the combined overrides don't apply to the real plugin schema.
    try:
        simulator.entity_schema().with_overrides(overrides)
    except (ValueError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail=f"invalid schema_overrides: {exc}") from exc

    objectives = [Objective(**o) for o in preset.default_objectives] if preset else []

    scenario = Scenario(
        id=uuid.uuid4().hex[:12],
        domain=request.domain,
        name=request.name,
        brief=request.brief,
        n_entities=request.n_entities,
        preset_id=request.preset_id,
        schema_overrides=overrides,
        constraints=request.constraints if request.constraints is not None else (preset.default_constraints if preset else []),
        sim_config=preset.sim_config if preset else {},
        visual_variant=request.visual_variant or (preset.default_visual_variant if preset else None),
        objectives=objectives,
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
        "schema": scenario.effective_schema(registry).model_dump(),  # plugin schema + overrides
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
