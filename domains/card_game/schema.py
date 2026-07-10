"""Card game entity schema.

The primary entity is ``Unit``. An ability is inlined onto the unit as
``ability_kind`` (a closed category) + ``ability_value`` (its magnitude) rather than a
nested object, because the entity DSL models flat entities. A "deck" is simply a list of
``Unit`` instances at simulation time, not a schema of its own.

The core stays domain-agnostic: this module only *describes* the entity via
:class:`~core.entity_schema.EntitySchema`; it imports nothing domain-specific from core.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from core.entity_schema import EntitySchema

_SEED_PATH = Path(__file__).with_name("seed_data.json")

# The four abilities the simulator implements (closed set — every unit has one).
ABILITY_KINDS = ["deal_damage", "heal", "shield", "draw"]

_UNIT_SCHEMA_DICT = {
    "name": "Unit",
    "fields": [
        {"name": "name", "kind": "str", "min_len": 1, "max_len": 40, "description": "Display name"},
        {"name": "cost", "kind": "num", "range": [1, 5], "description": "Mana cost to play"},
        {"name": "hp", "kind": "num", "range": [1, 20], "description": "Health points"},
        {"name": "damage", "kind": "num", "range": [1, 10], "description": "Attack damage per turn"},
        {
            "name": "ability_kind",
            "kind": "cat",
            "enum": ABILITY_KINDS,
            "description": "Which ability triggers when the unit is played",
        },
        {
            "name": "ability_value",
            "kind": "num",
            "range": [0, 10],
            "description": "Magnitude of the ability",
        },
        {
            "name": "description",
            "kind": "str",
            "max_len": 200,
            "required": False,
            "description": "Optional flavor/design note",
        },
    ],
}


def get_schema() -> EntitySchema:
    """Return the :class:`EntitySchema` for a card game ``Unit``."""
    return EntitySchema.from_dict(_UNIT_SCHEMA_DICT)


def load_seed() -> list[BaseModel]:
    """Load ``seed_data.json`` and return validated ``Unit`` model instances."""
    model = get_schema().build_model()
    raw = json.loads(_SEED_PATH.read_text())
    return [model(**entry) for entry in raw]
