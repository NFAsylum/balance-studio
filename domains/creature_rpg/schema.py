"""Creature RPG entity schema.

The primary entity is ``Creature``. ``resistances`` is a ``map`` (attacker-type -> damage
multiplier) layered on top of the domain's type-matchup table. ``skills`` is a tag_set of
skill names; the skill definitions (power/priority/cooldown/type) live in ``SKILLS`` and are
resolved by the simulator. Types form a ring where each beats the next.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel

from core.entity_schema import EntitySchema

_SEED_PATH = Path(__file__).with_name("seed_data.json")

TYPES = ["fire", "water", "plant", "ice", "electric", "rock", "wind", "shadow"]


class Skill(BaseModel):
    name: str
    type: str
    power: int
    priority: int  # higher acts earlier in the ability queue
    cooldown: int  # turns before it can be used again


# Two skills per type: a strong/slow hit and a quick/weak one.
SKILLS: list[Skill] = []
for _t in TYPES:
    SKILLS.append(Skill(name=f"{_t}_strike", type=_t, power=40, priority=1, cooldown=0))
    SKILLS.append(Skill(name=f"{_t}_burst", type=_t, power=70, priority=0, cooldown=2))

SKILLS_BY_NAME: dict[str, Skill] = {s.name: s for s in SKILLS}
_SKILL_NAMES = list(SKILLS_BY_NAME)

_CREATURE_SCHEMA_DICT = {
    "name": "Creature",
    "fields": [
        {"name": "name", "kind": "str", "min_len": 1, "max_len": 40, "description": "Display name"},
        {"name": "type", "kind": "cat", "enum": TYPES, "description": "Elemental type"},
        {"name": "hp", "kind": "num", "range": [20, 300], "description": "Health points"},
        {"name": "atk", "kind": "num", "range": [10, 150], "description": "Attack stat"},
        {"name": "defense", "kind": "num", "range": [5, 120], "description": "Defense stat"},
        {"name": "skills", "kind": "tag_set", "description": "Skill names this creature can use"},
        {
            "name": "resistances",
            "kind": "map",
            "enum": TYPES,
            "description": "Attacker-type -> damage multiplier (overrides the base matchup)",
        },
    ],
}


def get_schema() -> EntitySchema:
    """Return the :class:`EntitySchema` for a ``Creature``."""
    return EntitySchema.from_dict(_CREATURE_SCHEMA_DICT)


def beats(attacker_type: str) -> str:
    """The type ``attacker_type`` is strong against (next in the ring)."""
    return TYPES[(TYPES.index(attacker_type) + 1) % len(TYPES)]


def beaten_by(defender_type: str) -> str:
    """The type that is strong against ``defender_type`` (previous in the ring)."""
    return TYPES[(TYPES.index(defender_type) - 1) % len(TYPES)]


def generate_seed(n: int = 100) -> list[dict]:
    """Deterministically generate ``n`` creatures spread evenly across the 8 types."""
    creatures: list[dict] = []
    for i in range(n):
        ctype = TYPES[i % len(TYPES)]
        h = int(hashlib.sha256(str(i).encode()).hexdigest(), 16)
        own = [s.name for s in SKILLS if s.type == ctype]
        pool = own + [name for name in _SKILL_NAMES if name not in own]

        k = 2 + h % 3  # 2..4 skills
        skills: list[str] = []
        cursor = h
        while len(skills) < k:
            candidate = pool[cursor % len(pool)]
            if candidate not in skills:
                skills.append(candidate)
            cursor //= 3
            if cursor == 0:
                cursor = h + len(skills)
        if not any(name in own for name in skills):
            skills[0] = own[0]

        creatures.append(
            {
                "name": f"{ctype.capitalize()}-{i:03d}",
                "type": ctype,
                "hp": 20 + h % 281,
                "atk": 10 + (h // 7) % 141,
                "defense": 5 + (h // 13) % 116,
                "skills": skills,
                # weak to its counter (2x), resists what it beats (0.5x)
                "resistances": {beaten_by(ctype): 2.0, beats(ctype): 0.5},
            }
        )
    return creatures


def load_seed() -> list[BaseModel]:
    """Load ``seed_data.json`` and return validated ``Creature`` model instances."""
    model = get_schema().build_model()
    raw = json.loads(_SEED_PATH.read_text())
    return [model(**entry) for entry in raw]
