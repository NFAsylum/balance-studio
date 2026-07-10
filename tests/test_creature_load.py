"""Tests for domains.creature_rpg.schema — 100-creature seed, validation, load perf."""

import time
from collections import Counter

from core.entity_schema import EntitySchema
from core.llm_fakes import FakeDesigner
from domains.creature_rpg.schema import TYPES, get_schema, load_seed


def test_schema_shape():
    schema = get_schema()
    assert isinstance(schema, EntitySchema)
    by_name = {f.name: f for f in schema.fields}
    assert by_name["type"].kind == "cat" and by_name["type"].enum == TYPES
    assert by_name["resistances"].kind == "map"
    assert by_name["skills"].kind == "tag_set"


def test_seed_has_100_across_8_types():
    creatures = load_seed()
    assert len(creatures) == 100
    per_type = Counter(c.type for c in creatures)
    assert set(per_type) == set(TYPES)
    assert all(12 <= n <= 13 for n in per_type.values())


def test_each_creature_has_2_to_4_skills():
    for c in load_seed():
        assert 2 <= len(c.skills) <= 4


def test_all_creatures_validate():
    model = get_schema().build_model()
    for c in load_seed():
        data = c.model_dump()
        assert model(**data).model_dump() == data


def test_fake_designer_generates_valid_creatures():
    # regression: the map field (resistances) must be generated as a dict, not a list
    designed = FakeDesigner().design("balanced roster", get_schema(), [], 8)
    assert len(designed) == 8  # each validates on construction (map -> dict)
    assert all(isinstance(c.model_dump()["resistances"], dict) for c in designed)


def test_load_perf():
    start = time.perf_counter()
    creatures = load_seed()
    elapsed = time.perf_counter() - start
    assert len(creatures) == 100
    assert elapsed < 1.0  # design target: load 100 (scaling to 200) in < 1s
