"""Health probe: liveness plus the *live* LLM backend/model and readiness signals.

The model reported for the ``local`` backend is the one the server actually has loaded (queried
via ``core.llm_client.detect_local_model``), not just the env hint — llama-server will serve a
different model than requested without complaining, so the env config is a hint, not the truth.
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter

from api.dependencies import services
from api.registry import registry
from core.llm_client import _ANTHROPIC_MODEL, detect_local_model

router = APIRouter(tags=["health"])


def _llm_status() -> tuple[str, str]:
    """``(backend, model)`` — the model actually in use, resolved per backend."""
    backend = os.getenv("LLM_BACKEND", "fake").lower()
    if backend == "fake":
        return backend, "fake"
    if backend == "local":
        return backend, detect_local_model() or "local-unreachable"
    if backend == "anthropic":
        return backend, os.getenv("ANTHROPIC_MODEL", _ANTHROPIC_MODEL)
    return backend, "unknown"


@router.get("/health")
def health() -> dict[str, Any]:
    backend, model = _llm_status()
    return {
        "status": "ok",
        "backend_llm": backend,
        "llm_model": model,
        "domains_loaded": registry.names(),
        "event_log_ready": hasattr(services, "event_log"),
    }
