"""Manual entity CRUD within a scenario (user edits — recorded as ``actor="user"`` events)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.dependencies import load_scenario, services, validate_entity
from core.scenario import Event

router = APIRouter(tags=["entities"])


class EntityRequest(BaseModel):
    entity: dict[str, Any]


@router.post("/scenarios/{scenario_id}/entities")
def add_entity(scenario_id: str, request: EntityRequest) -> dict[str, Any]:
    scenario = load_scenario(scenario_id)
    data = validate_entity(scenario.domain, request.entity)
    target = str(data["name"])
    event = Event(
        branch_id=scenario.current_branch,
        actor="user",
        kind="create_entity",
        target=target,
        after=data,
    )
    return services.event_log.append(scenario_id, event).model_dump(mode="json")


@router.patch("/scenarios/{scenario_id}/entities/{entity_id}")
def edit_entity(scenario_id: str, entity_id: str, request: EntityRequest) -> dict[str, Any]:
    scenario = load_scenario(scenario_id)
    branch = scenario.current_branch
    state = services.replay.rebuild_state(scenario_id, services.event_log.head(scenario_id, branch), branch)
    if entity_id not in state.entities:
        raise HTTPException(status_code=404, detail=f"entity '{entity_id}' not found")
    data = validate_entity(scenario.domain, request.entity)
    # The URL path is the identity: an edit must not silently rename (would desync the state
    # key from the entity's own `name`). Rename via delete + create instead.
    if data.get("name") and str(data["name"]) != entity_id:
        raise HTTPException(
            status_code=422,
            detail=f"entity name '{data['name']}' does not match path '{entity_id}'; "
            "rename via delete + create",
        )
    event = Event(
        branch_id=branch,
        actor="user",
        kind="edit_entity",
        target=entity_id,
        before=state.entities[entity_id],
        after=data,
    )
    return services.event_log.append(scenario_id, event).model_dump(mode="json")


@router.delete("/scenarios/{scenario_id}/entities/{entity_id}")
def delete_entity(scenario_id: str, entity_id: str) -> dict[str, Any]:
    scenario = load_scenario(scenario_id)
    branch = scenario.current_branch
    state = services.replay.rebuild_state(scenario_id, services.event_log.head(scenario_id, branch), branch)
    if entity_id not in state.entities:
        raise HTTPException(status_code=404, detail=f"entity '{entity_id}' not found")
    event = Event(
        branch_id=branch,
        actor="user",
        kind="delete_entity",
        target=entity_id,
        before=state.entities[entity_id],
    )
    return services.event_log.append(scenario_id, event).model_dump(mode="json")
