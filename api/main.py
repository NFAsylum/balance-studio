"""FastAPI app: wiring only.

Middleware (CORS, write auth + rate limit) and shared services live in ``api.dependencies``;
the endpoints live in ``api.routers.*`` (one module per resource group). Adding a domain adds
routes for free via the registry — no change here.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import dependencies as deps
from api.routers import branches, domains, entities, health, presets, scenarios
from core.paths import InvalidId

app = FastAPI(title="Balance Studio", lifespan=deps.lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=deps.ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key"],
    allow_credentials=True,
)
app.middleware("http")(deps.guard_writes)
app.add_exception_handler(InvalidId, deps.invalid_id_handler)

for module in (health, domains, presets, scenarios, entities, branches):
    app.include_router(module.router)
