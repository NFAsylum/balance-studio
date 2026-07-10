"""Tests for core.constraint_engine — declarative constraint validation."""

from core.constraint_engine import Constraint, ConstraintEngine
from core.entity_schema import EntitySchema

ENGINE = ConstraintEngine()


def _unit(**kwargs):
    """Build a card-like entity model instance from kwargs."""
    schema = EntitySchema.from_dict(
        {
            "name": "Unit",
            "fields": [
                {"name": "name", "kind": "cat", "enum": ["a", "b", "c", "d"]},
                {"name": "cost", "kind": "num", "range": [0, 10]},
                {"name": "hp", "kind": "num", "range": [0, 100]},
                {"name": "damage", "kind": "num", "range": [0, 100]},
                {"name": "tags", "kind": "tag_set"},
            ],
        }
    )
    model = schema.build_model()
    defaults = {"name": "a", "cost": 1, "hp": 10, "damage": 1, "tags": []}
    defaults.update(kwargs)
    return model(**defaults)


# -- range ----------------------------------------------------------------


def test_range_happy():
    r = ENGINE.validate(_unit(cost=3), [Constraint(kind="range", params={"field": "cost", "min": 1, "max": 5})])
    assert r.is_valid and r.violations == []


def test_range_violation():
    r = ENGINE.validate(_unit(cost=9), [Constraint(kind="range", params={"field": "cost", "min": 1, "max": 5})])
    assert not r.is_valid
    assert "cost" in r.violations[0]


# -- sum_of_fields --------------------------------------------------------


def test_sum_of_fields_happy():
    c = Constraint(kind="sum_of_fields", params={"fields": ["hp", "damage"], "max": 30})
    r = ENGINE.validate(_unit(hp=20, damage=5), [c])
    assert r.is_valid


def test_sum_of_fields_violation():
    c = Constraint(kind="sum_of_fields", params={"fields": ["hp", "damage"], "min": 5, "max": 30})
    r = ENGINE.validate(_unit(hp=40, damage=5), [c])
    assert not r.is_valid
    assert "above max" in r.violations[0]


# -- forbidden_combo ------------------------------------------------------


def test_forbidden_combo_happy():
    c = Constraint(kind="forbidden_combo", params={"field": "tags", "tags": ["stealth", "taunt"]})
    r = ENGINE.validate(_unit(tags=["stealth"]), [c])  # only one of the two
    assert r.is_valid


def test_forbidden_combo_violation():
    c = Constraint(kind="forbidden_combo", params={"field": "tags", "tags": ["stealth", "taunt"]})
    r = ENGINE.validate(_unit(tags=["stealth", "taunt", "cheap"]), [c])
    assert not r.is_valid


# -- required_tag ---------------------------------------------------------


def test_required_tag_happy():
    c = Constraint(kind="required_tag", params={"field": "tags", "any_of": ["aggro", "control"]})
    r = ENGINE.validate(_unit(tags=["control"]), [c])
    assert r.is_valid


def test_required_tag_violation():
    c = Constraint(kind="required_tag", params={"field": "tags", "any_of": ["aggro", "control"]})
    r = ENGINE.validate(_unit(tags=["combo"]), [c])
    assert not r.is_valid


# -- unique_across_set ----------------------------------------------------


def test_unique_across_set_happy():
    entities = [_unit(name="a"), _unit(name="b"), _unit(name="c")]
    results = ENGINE.validate_set(entities, [Constraint(kind="unique_across_set", params={"field": "name"})])
    assert all(r.is_valid for r in results)


def test_unique_across_set_violation():
    entities = [_unit(name="a"), _unit(name="a"), _unit(name="b")]
    results = ENGINE.validate_set(entities, [Constraint(kind="unique_across_set", params={"field": "name"})])
    assert not results[0].is_valid
    assert not results[1].is_valid
    assert results[2].is_valid


def test_unique_across_set_skipped_in_single_validate():
    # A single-entity validate cannot judge uniqueness, so it must not flag it.
    r = ENGINE.validate(_unit(name="a"), [Constraint(kind="unique_across_set", params={"field": "name"})])
    assert r.is_valid


# -- combined + dict entities --------------------------------------------


def test_validate_set_combines_per_entity_and_set_level():
    entities = [_unit(name="a", cost=9), _unit(name="a", cost=2)]
    constraints = [
        Constraint(kind="range", params={"field": "cost", "min": 1, "max": 5}),
        Constraint(kind="unique_across_set", params={"field": "name"}),
    ]
    results = ENGINE.validate_set(entities, constraints)
    # entity 0: range + uniqueness violations; entity 1: uniqueness only
    assert len(results[0].violations) == 2
    assert len(results[1].violations) == 1


def test_works_on_plain_dict_entities():
    r = ENGINE.validate({"cost": 3}, [Constraint(kind="range", params={"field": "cost", "min": 1, "max": 5})])
    assert r.is_valid
