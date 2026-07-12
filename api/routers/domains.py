"""Domain-level, scenario-free endpoints: schema/metrics introspection, one-off simulate/generate."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ValidationError

from api.dependencies import require_domain
from api.registry import registry
from core.constraint_engine import Constraint
from core.llm_fakes import FakeDesigner
from core.report_engine import Report, build_report, hash_json

router = APIRouter(tags=["domains"])


class SimulateRequest(BaseModel):
    entities: list[Any]
    env: dict[str, Any]
    n_runs: int = Field(default=1, ge=1, le=100_000)
    metrics: list[str] | None = None


class GenerateRequest(BaseModel):
    n: int = Field(ge=1, le=100)
    constraints: list[dict[str, Any]] = Field(default_factory=list)
    user_intent: str = ""


@router.get("/domains")
def list_domains() -> dict[str, list[str]]:
    return {"domains": registry.names()}


@router.get("/domains/{name}/schema")
def get_schema(name: str) -> dict[str, Any]:
    simulator = require_domain(name)
    return simulator.entity_schema().model_dump()


@router.get("/domains/{name}/metrics")
def domain_metrics(name: str) -> dict[str, list[dict[str, str]]]:
    simulator = require_domain(name)
    return {
        "metrics": [
            {"name": m.name, "kind": m.kind, "description": m.description}
            for m in simulator.default_metrics()
        ]
    }


@router.post("/domains/{name}/simulate", response_model=Report)
def simulate(name: str, request: SimulateRequest) -> Report:
    simulator = require_domain(name)
    env_cls = simulator.environment_schema()

    try:
        base_env = env_cls(**request.env)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors(include_url=False)) from exc

    metrics = simulator.default_metrics()
    if request.metrics is not None:
        wanted = set(request.metrics)
        metrics = [m for m in metrics if m.name in wanted]

    runs = []
    env_fields = base_env.model_dump()
    for i in range(request.n_runs):
        # Vary the seed per run so a batch produces a distribution, not one repeated match.
        env_i = env_cls(**{**env_fields, "seed": base_env.seed + i})
        try:
            runs.append(simulator.run(request.entities, env_i))
        except (ValueError, TypeError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return build_report(
        domain=name,
        runs=runs,
        metrics=metrics,
        entity_set_hash=hash_json(request.entities),
        env_hash=hash_json(request.env),
    )


@router.post("/domains/{name}/generate")
def generate(name: str, request: GenerateRequest) -> dict[str, Any]:
    """Design candidate entities via the deterministic Designer hat (Fake — no API key needed)."""
    simulator = require_domain(name)
    constraints = [Constraint(**c) for c in request.constraints]
    designer = FakeDesigner()
    entities = designer.design(
        brief=request.user_intent,
        schema=simulator.entity_schema(),
        constraints=constraints,
        n=request.n,
    )
    return {"entities": [e.model_dump() for e in entities], "requested": request.n}
