"""FastAPI app exposing domain-agnostic balance endpoints.

Routing is by domain ``{name}``; the handlers never branch on which domain it is — they
call the plugin's :class:`~core.simulator_interface.SimulatorInterface`. Adding a domain
adds routes for free via the registry.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ValidationError

from api.registry import registry
from core.constraint_engine import Constraint
from core.report_engine import Report, build_report, hash_json

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    registry.load()
    logger.info("domains loaded: %s", registry.names())
    yield


app = FastAPI(title="Balance Studio", lifespan=lifespan)


class SimulateRequest(BaseModel):
    entities: list[Any]
    env: dict[str, Any]
    n_runs: int = Field(default=1, ge=1, le=100_000)
    metrics: list[str] | None = None


class GenerateRequest(BaseModel):
    n: int = Field(ge=1, le=100)
    constraints: list[dict[str, Any]] = Field(default_factory=list)
    user_intent: str = ""


def _require_domain(name: str):
    simulator = registry.get(name)
    if simulator is None:
        raise HTTPException(status_code=404, detail=f"domain '{name}' not found")
    return simulator


@app.get("/domains")
def list_domains() -> dict[str, list[str]]:
    return {"domains": registry.names()}


@app.get("/domains/{name}/schema")
def get_schema(name: str) -> dict[str, Any]:
    simulator = _require_domain(name)
    return simulator.entity_schema().model_dump()


@app.post("/domains/{name}/simulate", response_model=Report)
def simulate(name: str, request: SimulateRequest) -> Report:
    simulator = _require_domain(name)
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


@app.post("/domains/{name}/generate")
def generate(name: str, request: GenerateRequest) -> dict[str, Any]:
    simulator = _require_domain(name)
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY not configured")

    try:
        import anthropic

        client = anthropic.Anthropic()
    except Exception as exc:  # noqa: BLE001 - surface any client init failure as 503
        raise HTTPException(status_code=503, detail=f"LLM client unavailable: {exc}") from exc

    from core.llm_generator import LlmGenerator

    constraints = [Constraint(**c) for c in request.constraints]
    generator = LlmGenerator(client, simulator.entity_schema())
    entities = generator.generate(
        n=request.n,
        constraints=constraints,
        user_intent=request.user_intent,
        domain_prompt=simulator.llm_generation_prompt(constraints),
    )
    return {"entities": [e.model_dump() for e in entities], "requested": request.n}
