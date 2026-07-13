"""Presets — ready-made scenario starting points (real games/teams, not "example values").

A preset bundles a domain, a set of ``schema_overrides`` (applied on top of the plugin schema
— see :meth:`EntitySchema.with_overrides`), default constraints/objectives, and the default
visual variant. Files live under ``presets/<domain>/<id>.json``.

Important constraint (by design): domain simulators hardcode their *categorical* enums (a
creature's ``type`` matchup table, a card's ``ability_kind`` effects, a person's ``seniority``
speed). Presets therefore rescale **numeric ranges** and add **flavour fields** freely — that
is what makes YuGiOh (HP→5000, level 1-12) differ from Hearthstone (mana 0-10, hp 1-30) — but
they do not replace those sim-critical enums, which would break deterministic simulation.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from core.entity_schema import EntitySchema


class Preset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    domain: str
    description: str = ""
    schema_overrides: dict[str, Any] = {}
    default_constraints: list[dict[str, Any]] = []
    default_objectives: list[dict[str, Any]] = []
    default_visual_variant: str | None = None
    sim_config: dict[str, Any] = {}  # declarative env config: ability_map / type_matchup / seniority_speed
    examples: list[dict[str, Any]] = []  # illustrative entities (real cards/creatures) for reference/few-shot

    def apply_to(self, base_schema: EntitySchema) -> EntitySchema:
        """Return the effective schema this preset produces (raises if overrides are invalid)."""
        return base_schema.with_overrides(self.schema_overrides)


class PresetStore:
    """Loads and indexes presets from ``<base_dir>/<domain>/*.json`` (cached after first read)."""

    def __init__(self, base_dir: str | Path | None = None):
        self.base = Path(base_dir or os.getenv("PRESETS_DIR", "presets"))
        self._cache: dict[str, Preset] | None = None

    def _load(self) -> dict[str, Preset]:
        if self._cache is not None:
            return self._cache
        presets: dict[str, Preset] = {}
        if self.base.exists():
            for path in sorted(self.base.glob("*/*.json")):
                data = json.loads(path.read_text())
                try:
                    preset = Preset.model_validate(data)
                except Exception as exc:  # noqa: BLE001 - re-raise with the offending file
                    raise ValueError(f"invalid preset {path}: {exc}") from exc
                if preset.domain != path.parent.name:
                    raise ValueError(
                        f"preset {path}: domain '{preset.domain}' does not match folder '{path.parent.name}'"
                    )
                if preset.id in presets:
                    raise ValueError(f"duplicate preset id '{preset.id}' ({path})")
                presets[preset.id] = preset
        self._cache = presets
        return presets

    def all(self) -> list[Preset]:
        return list(self._load().values())

    def for_domain(self, domain: str) -> list[Preset]:
        return [p for p in self._load().values() if p.domain == domain]

    def get(self, preset_id: str) -> Preset | None:
        return self._load().get(preset_id)
