"""Tests for core.entity_schema — the declarative entity DSL."""

import pytest
from pydantic import ValidationError

from core.entity_schema import EntitySchema, FieldSpec


def _schema(field: dict) -> EntitySchema:
    return EntitySchema.from_dict({"name": "Thing", "fields": [field]})


# -- num ------------------------------------------------------------------


def test_num_field_range_enforced():
    Model = _schema({"name": "cost", "kind": "num", "range": [1, 5]}).build_model()
    assert Model(cost=3).cost == 3
    with pytest.raises(ValidationError):
        Model(cost=6)  # above max
    with pytest.raises(ValidationError):
        Model(cost=0)  # below min


def test_num_field_without_range_accepts_any_number():
    Model = _schema({"name": "score", "kind": "num"}).build_model()
    assert Model(score=-42.5).score == -42.5


# -- cat ------------------------------------------------------------------


def test_cat_field_enum_enforced():
    Model = _schema(
        {"name": "element", "kind": "cat", "enum": ["fire", "water"]}
    ).build_model()
    assert Model(element="fire").element == "fire"
    with pytest.raises(ValidationError):
        Model(element="earth")  # not in enum


# -- bool -----------------------------------------------------------------


def test_bool_field():
    Model = _schema({"name": "legendary", "kind": "bool"}).build_model()
    assert Model(legendary=True).legendary is True
    with pytest.raises(ValidationError):
        Model(legendary="not-a-bool-ish")


# -- tag_set --------------------------------------------------------------


def test_tag_set_field():
    Model = _schema({"name": "tags", "kind": "tag_set"}).build_model()
    assert Model(tags=["aggro", "cheap"]).tags == ["aggro", "cheap"]
    assert Model(tags=[]).tags == []
    with pytest.raises(ValidationError):
        Model(tags="not-a-list")


# -- str ------------------------------------------------------------------


def test_str_field_no_constraints():
    Model = _schema({"name": "title", "kind": "str"}).build_model()
    assert Model(title="anything goes").title == "anything goes"
    assert Model(title="").title == ""


def test_str_field_min_max_len():
    Model = _schema({"name": "name", "kind": "str", "min_len": 2, "max_len": 5}).build_model()
    assert Model(name="abc").name == "abc"
    with pytest.raises(ValidationError):
        Model(name="a")  # below min_len
    with pytest.raises(ValidationError):
        Model(name="toolong")  # above max_len


def test_str_field_llm_schema_and_invalid_spec():
    schema = _schema({"name": "name", "kind": "str", "min_len": 1, "max_len": 40})
    prop = schema.to_llm_schema()["input_schema"]["properties"]["name"]
    assert prop == {"type": "string", "minLength": 1, "maxLength": 40}
    # min_len/max_len are str-only; using them on another kind is an error.
    with pytest.raises(ValidationError):
        FieldSpec(name="x", kind="num", min_len=1)
    # inverted length bounds
    with pytest.raises(ValidationError):
        FieldSpec(name="x", kind="str", min_len=5, max_len=2)


# -- extra fields forbidden ----------------------------------------------


def test_extra_fields_rejected():
    Model = _schema({"name": "cost", "kind": "num", "range": [1, 5]}).build_model()
    with pytest.raises(ValidationError):
        Model(cost=3, hallucinated=99)


# -- invalid field specs --------------------------------------------------


def test_invalid_specs_raise():
    # cat without enum
    with pytest.raises(ValidationError):
        FieldSpec(name="x", kind="cat")
    # num with inverted range
    with pytest.raises(ValidationError):
        FieldSpec(name="x", kind="num", range=(5, 1))
    # range on a non-num field
    with pytest.raises(ValidationError):
        FieldSpec(name="x", kind="bool", range=(1, 2))
    # enum on a non-cat field
    with pytest.raises(ValidationError):
        FieldSpec(name="x", kind="tag_set", enum=["a"])
    # unknown kind
    with pytest.raises(ValidationError):
        FieldSpec(name="x", kind="mystery")
    # duplicate field names in a schema
    with pytest.raises(ValidationError):
        EntitySchema.from_dict(
            {"name": "T", "fields": [{"name": "a", "kind": "bool"}, {"name": "a", "kind": "bool"}]}
        )


# -- to_llm_schema (Anthropic tool_use) ----------------------------------


def test_to_llm_schema_shape():
    schema = EntitySchema.from_dict(
        {
            "name": "Unit",
            "fields": [
                {"name": "cost", "kind": "num", "range": [1, 5], "description": "mana cost"},
                {"name": "element", "kind": "cat", "enum": ["fire", "water"]},
                {"name": "legendary", "kind": "bool"},
                {"name": "tags", "kind": "tag_set"},
            ],
        }
    )
    tool = schema.to_llm_schema()

    # Anthropic tool_use requires name + input_schema (an object JSON Schema).
    assert tool["name"] == "emit_unit"
    assert "description" in tool
    input_schema = tool["input_schema"]
    assert input_schema["type"] == "object"
    assert set(input_schema["required"]) == {"cost", "element", "legendary", "tags"}

    props = input_schema["properties"]
    assert props["cost"] == {
        "description": "mana cost",
        "type": "number",
        "minimum": 1,
        "maximum": 5,
    }
    assert props["element"] == {"type": "string", "enum": ["fire", "water"]}
    assert props["legendary"] == {"type": "boolean"}
    assert props["tags"] == {"type": "array", "items": {"type": "string"}}


def test_to_llm_schema_matches_built_model_acceptance():
    """A payload satisfying the emitted JSON schema also validates in the model."""
    schema = EntitySchema.from_dict(
        {
            "name": "Unit",
            "fields": [
                {"name": "cost", "kind": "num", "range": [1, 5]},
                {"name": "element", "kind": "cat", "enum": ["fire", "water"]},
                {"name": "legendary", "kind": "bool"},
                {"name": "tags", "kind": "tag_set"},
            ],
        }
    )
    Model = schema.build_model()
    payload = {"cost": 2, "element": "water", "legendary": False, "tags": ["control"]}
    assert Model(**payload).cost == 2
