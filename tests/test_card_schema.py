"""Tests for domains.card_game.schema — the Unit entity schema and seed data."""

from core.entity_schema import EntitySchema
from domains.card_game.schema import ABILITY_KINDS, get_schema, load_seed


def test_get_schema_shape():
    schema = get_schema()
    assert isinstance(schema, EntitySchema)
    assert schema.name == "Unit"
    by_name = {f.name: f for f in schema.fields}
    assert set(by_name) == {
        "name",
        "cost",
        "hp",
        "damage",
        "ability_kind",
        "ability_value",
        "description",
    }
    # name is free-form text, not a closed category.
    assert by_name["name"].kind == "str"
    assert by_name["cost"].kind == "num" and by_name["cost"].range == (1, 5)
    assert by_name["hp"].range == (1, 20)
    assert by_name["damage"].range == (1, 10)
    assert by_name["ability_kind"].kind == "cat"
    assert by_name["ability_kind"].enum == ABILITY_KINDS
    # ability_kind is a closed set of the four real abilities (no "none")
    assert ABILITY_KINDS == ["deal_damage", "heal", "shield", "draw"]
    # description is optional (may be omitted by user or LLM)
    assert by_name["description"].kind == "str" and by_name["description"].required is False


def test_description_optional_in_model():
    model = get_schema().build_model()
    # a unit without a description validates; the field defaults to None
    unit = model(name="X", cost=1, hp=1, damage=1, ability_kind="draw", ability_value=0)
    assert unit.description is None


def test_seed_has_ten_units():
    units = load_seed()
    assert len(units) == 10
    # names are unique
    assert len({u.name for u in units}) == 10


def test_all_seed_units_validate():
    # load_seed builds each via the Pydantic model, so a bad row would already raise.
    # Re-validate explicitly through a fresh model and compare by value.
    model = get_schema().build_model()
    for unit in load_seed():
        data = unit.model_dump()
        assert model(**data).model_dump() == data


def test_seed_covers_every_ability_kind():
    kinds = {u.ability_kind for u in load_seed()}
    # seed should exercise the ability space (at least the 4 real abilities present)
    assert {"deal_damage", "heal", "shield", "draw"}.issubset(kinds)
