"""Tests for domains.team_composition.schema — Person schema + 50-person seed + task types."""

from core.entity_schema import EntitySchema
from domains.team_composition.schema import SENIORITY, TASK_TYPES, get_schema, load_seed


def test_schema_shape():
    schema = get_schema()
    assert isinstance(schema, EntitySchema)
    by_name = {f.name: f for f in schema.fields}
    assert set(by_name) == {"name", "seniority", "skills", "preferred_task_types"}
    assert by_name["seniority"].kind == "cat" and by_name["seniority"].enum == SENIORITY
    assert by_name["skills"].kind == "tag_set"
    assert by_name["preferred_task_types"].kind == "tag_set"


def test_seed_has_50_people_across_seniorities():
    people = load_seed()
    assert len(people) == 50
    seniorities = {p.seniority for p in people}
    assert seniorities == set(SENIORITY)


def test_twenty_task_types_all_have_requirements():
    assert len(TASK_TYPES) == 20
    assert all(t.required_skills for t in TASK_TYPES)
    assert all(t.estimated_hours > 0 for t in TASK_TYPES)


def test_all_people_validate():
    model = get_schema().build_model()
    for p in load_seed():
        data = p.model_dump()
        assert model(**data).model_dump() == data
        assert 2 <= len(p.skills) <= 5
