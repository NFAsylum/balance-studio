"""Team composition entity schema.

The entity is a ``Person`` (name, seniority, skills, preferred task types). Task types are a
domain registry (name + required skills + estimated hours) consumed by the simulator's
``WorkloadEnv``. This is the extensibility demo: a whole new domain (people/workload instead
of cards/creatures) plugging into the same core with no core changes.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel

from core.entity_schema import EntitySchema

_SEED_PATH = Path(__file__).with_name("seed_data.json")

SENIORITY = ["junior", "mid", "senior", "lead"]
# Seniority multiplies how many hours of work a person clears per capacity-hour.
SENIORITY_SPEED = {"junior": 0.7, "mid": 1.0, "senior": 1.4, "lead": 1.7}

SKILLS = [
    "python",
    "javascript",
    "typescript",
    "sql",
    "design",
    "ml",
    "devops",
    "security",
    "mobile",
    "data",
    "pm",
    "qa",
]


class TaskType(BaseModel):
    name: str
    required_skills: list[str]
    estimated_hours: int


def _make_task_types() -> list[TaskType]:
    """20 deterministic task types spanning the skill set."""
    tasks: list[TaskType] = []
    for i in range(20):
        h = int(hashlib.sha256(f"task{i}".encode()).hexdigest(), 16)
        n_req = 1 + h % 3  # 1..3 required skills
        req = sorted({SKILLS[(h // (7 ** k)) % len(SKILLS)] for k in range(n_req + 1)})[:n_req]
        tasks.append(TaskType(name=f"task_{i:02d}", required_skills=req, estimated_hours=4 + h % 37))
    return tasks


TASK_TYPES: list[TaskType] = _make_task_types()
TASK_TYPES_BY_NAME: dict[str, TaskType] = {t.name: t for t in TASK_TYPES}

_PERSON_SCHEMA_DICT = {
    "name": "Person",
    "fields": [
        {"name": "name", "kind": "str", "min_len": 1, "max_len": 40, "description": "Full name"},
        {"name": "seniority", "kind": "cat", "enum": SENIORITY, "description": "Experience level"},
        {"name": "skills", "kind": "tag_set", "description": "Skills this person has"},
        {
            "name": "preferred_task_types",
            "kind": "tag_set",
            "description": "Task types this person prefers",
        },
    ],
}


def get_schema() -> EntitySchema:
    """Return the :class:`EntitySchema` for a ``Person``."""
    return EntitySchema.from_dict(_PERSON_SCHEMA_DICT)


_FIRST_NAMES = [
    "Ana", "Bruno", "Clara", "Diego", "Elena", "Felipe", "Gabi", "Hugo", "Iris", "João",
    "Kira", "Lucas", "Maya", "Nina", "Otto", "Paula", "Quinn", "Rafa", "Sofia", "Théo",
]
_LAST_NAMES = ["Alves", "Braga", "Costa", "Dias", "Faria", "Gomes", "Lima", "Melo", "Nunes", "Rocha"]


def _person_name(i: int) -> str:
    return f"{_FIRST_NAMES[i % len(_FIRST_NAMES)]} {_LAST_NAMES[(i // len(_FIRST_NAMES)) % len(_LAST_NAMES)]}"


def generate_seed(n: int = 50) -> list[dict]:
    """Deterministically generate ``n`` people across seniorities and skills."""
    people: list[dict] = []
    for i in range(n):
        h = int(hashlib.sha256(f"person{i}".encode()).hexdigest(), 16)
        seniority = SENIORITY[i % len(SENIORITY)]
        n_skills = 2 + h % 4  # 2..5 skills
        skills = sorted({SKILLS[(h // (5 ** k)) % len(SKILLS)] for k in range(n_skills + 2)})[:n_skills]
        n_pref = 1 + h % 3  # 1..3 preferred task types
        prefs = sorted({f"task_{((h // (3 ** k)) % 20):02d}" for k in range(n_pref + 1)})[:n_pref]
        people.append(
            {
                "name": _person_name(i),
                "seniority": seniority,
                "skills": skills,
                "preferred_task_types": prefs,
            }
        )
    return people


def load_seed() -> list[BaseModel]:
    """Load ``seed_data.json`` and return validated ``Person`` model instances."""
    model = get_schema().build_model()
    raw = json.loads(_SEED_PATH.read_text())
    return [model(**entry) for entry in raw]
