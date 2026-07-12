"""Shared services, app lifespan, request guards, and helpers used by the API routers.

Kept out of ``main.py`` so that file stays a thin wiring layer. The ``services`` singleton is
populated once in :func:`lifespan` and imported by reference everywhere.
"""

from __future__ import annotations

import logging
import os
import time
from collections import deque
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from api.registry import registry
from core.branching import Branch
from core.iteration_engine import IterationEngine
from core.llm_factory import build_hats
from core.scenario import EventLog, Scenario
from core.snapshot import Replay, SnapshotStore

logger = logging.getLogger(__name__)


class Services:
    """Startup-initialised shared services (LLM hats selected by ``LLM_BACKEND``)."""

    event_log: EventLog
    replay: Replay
    branch: Branch
    engine: IterationEngine


services = Services()


@asynccontextmanager
async def lifespan(app: FastAPI):
    registry.load()
    base_dir = os.getenv("SCENARIOS_DIR", "scenarios")
    services.event_log = EventLog(base_dir=base_dir)
    services.replay = Replay(services.event_log, SnapshotStore(base_dir=base_dir))
    services.branch = Branch(services.event_log, services.replay)
    hats = build_hats()  # LLM_BACKEND=fake|local|anthropic
    services.engine = IterationEngine(
        services.event_log,
        services.replay,
        registry.all(),
        hats.designer,
        hats.judge,
        hats.iterator,
    )
    logger.info("domains loaded: %s | LLM backend: %s", registry.names(), os.getenv("LLM_BACKEND", "fake"))
    yield


# -- request guards (CORS list, API key, rate limit, path-traversal handler) ----

ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
_API_KEY = os.getenv("BALANCE_API_KEY")
_WRITE_METHODS = {"POST", "PATCH", "DELETE"}
_RATE_LIMIT_PER_MIN = int(os.getenv("WRITE_RATE_LIMIT_PER_MIN", "60"))
_rate_state: dict[str, deque[float]] = {}

if not _API_KEY:
    logger.warning("running without API key auth (dev mode) — set BALANCE_API_KEY to require X-API-Key on writes")


async def invalid_id_handler(request: Request, exc: Exception) -> JSONResponse:
    """A traversal-unsafe scenario/branch id never reaches disk — it 422s here."""
    return JSONResponse(status_code=422, content={"detail": str(exc)})


def _rate_limited(client: str) -> bool:
    now = time.monotonic()
    window = _rate_state.setdefault(client, deque())
    while window and now - window[0] > 60.0:
        window.popleft()
    if len(window) >= _RATE_LIMIT_PER_MIN:
        return True
    window.append(now)
    return False


async def guard_writes(request: Request, call_next):
    """Enforce API key + rate limit on state-changing requests (reads stay open)."""
    if request.method in _WRITE_METHODS:
        if _API_KEY and request.headers.get("X-API-Key") != _API_KEY:
            return JSONResponse(status_code=401, content={"detail": "invalid or missing API key"})
        client = request.headers.get("fly-client-ip") or (request.client.host if request.client else "unknown")
        if _rate_limited(client):
            return JSONResponse(status_code=429, content={"detail": "rate limit exceeded (writes)"})
    return await call_next(request)


# -- shared helpers ------------------------------------------------------------


def require_domain(name: str):
    simulator = registry.get(name)
    if simulator is None:
        raise HTTPException(status_code=404, detail=f"domain '{name}' not found")
    return simulator


def load_scenario(scenario_id: str) -> Scenario:
    try:
        return services.event_log.scenario(scenario_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"scenario '{scenario_id}' not found") from exc


def validate_entity(domain: str, data: dict[str, Any]) -> dict[str, Any]:
    simulator = require_domain(domain)
    model = simulator.entity_schema().build_model()
    try:
        return model(**data).model_dump()
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors(include_url=False)) from exc
