"""Preset catalogue: ready-made scenario starting points per domain."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from core.presets import Preset, PresetStore

router = APIRouter(tags=["presets"])

_store = PresetStore()  # lazy — loads + validates preset files on first request


@router.get("/presets")
def list_presets(domain: str | None = None) -> dict[str, list[dict[str, Any]]]:
    presets = _store.for_domain(domain) if domain else _store.all()
    return {"presets": [p.model_dump() for p in presets]}


@router.get("/presets/{preset_id}")
def get_preset(preset_id: str) -> Preset:
    preset = _store.get(preset_id)
    if preset is None:
        raise HTTPException(status_code=404, detail=f"preset '{preset_id}' not found")
    return preset
