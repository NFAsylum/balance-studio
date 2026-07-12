"""Branch management within a scenario: list, fork (create), and diff two branches."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.dependencies import load_scenario, services
from core.branching import DiffReport

router = APIRouter(tags=["branches"])


class CreateBranchRequest(BaseModel):
    parent_seq: int = Field(ge=0)
    name: str


@router.get("/scenarios/{scenario_id}/branches")
def list_branches(scenario_id: str) -> dict[str, list[dict[str, Any]]]:
    load_scenario(scenario_id)
    return {"branches": [b.model_dump() for b in services.branch.list(scenario_id)]}


@router.post("/scenarios/{scenario_id}/branches")
def create_branch(scenario_id: str, request: CreateBranchRequest) -> dict[str, Any]:
    load_scenario(scenario_id)
    try:
        branch_id = services.branch.create(scenario_id, request.parent_seq, request.name)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"branch_id": branch_id}


@router.get("/scenarios/{scenario_id}/branches/{branch_a}/diff/{branch_b}", response_model=DiffReport)
def diff_branches(scenario_id: str, branch_a: str, branch_b: str) -> DiffReport:
    load_scenario(scenario_id)
    known = services.event_log.branch_ids(scenario_id)
    for branch in (branch_a, branch_b):
        if branch not in known:
            raise HTTPException(status_code=404, detail=f"branch '{branch}' not found")
    return services.branch.diff(scenario_id, branch_a, branch_b)
