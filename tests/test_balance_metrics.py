"""Tests for core.balance_metrics — variety score + percent delta."""

from core.balance_metrics import pct_delta, variety_score
from core.entity_schema import EntitySchema

_SCHEMA = EntitySchema.from_dict(
    {
        "name": "U",
        "fields": [
            {"name": "name", "kind": "str"},
            {"name": "cost", "kind": "num", "range": [1, 5]},
            {"name": "hp", "kind": "num", "range": [1, 20]},
        ],
    }
)


def test_variety_zero_for_identical_entities():
    ents = [{"name": "a", "cost": 3, "hp": 10}, {"name": "b", "cost": 3, "hp": 10}]
    assert variety_score(ents, _SCHEMA) == 0.0


def test_variety_positive_and_ordered():
    tight = [{"name": "a", "cost": 3, "hp": 10}, {"name": "b", "cost": 3, "hp": 11}]
    spread = [{"name": "a", "cost": 1, "hp": 1}, {"name": "b", "cost": 5, "hp": 20}]
    assert variety_score(spread, _SCHEMA) > variety_score(tight, _SCHEMA) > 0.0


def test_variety_normalises_by_range():
    # hp spans a 20-wide range; a full-hp swing should count ~1.0 in normalised space,
    # like a full cost swing — not dominate it.
    a = variety_score([{"name": "a", "cost": 1, "hp": 1}, {"name": "b", "cost": 1, "hp": 20}], _SCHEMA)
    b = variety_score([{"name": "a", "cost": 1, "hp": 1}, {"name": "b", "cost": 5, "hp": 1}], _SCHEMA)
    assert abs(a - b) < 0.01  # both ~1.0 normalised distance


def test_variety_handles_edge_cases():
    assert variety_score([], _SCHEMA) == 0.0
    assert variety_score([{"name": "a", "cost": 3, "hp": 5}], _SCHEMA) == 0.0


def test_variety_works_for_categorical_and_tag_fields():
    # team-style schema (no numeric fields) must still yield a signal
    schema = EntitySchema.from_dict(
        {
            "name": "P",
            "fields": [
                {"name": "name", "kind": "str"},
                {"name": "seniority", "kind": "cat", "enum": ["junior", "senior"]},
                {"name": "skills", "kind": "tag_set"},
            ],
        }
    )
    same = [
        {"name": "a", "seniority": "junior", "skills": ["python"]},
        {"name": "b", "seniority": "junior", "skills": ["python"]},
    ]
    diverse = [
        {"name": "a", "seniority": "junior", "skills": ["python"]},
        {"name": "b", "seniority": "senior", "skills": ["design", "sql"]},
    ]
    assert variety_score(diverse, schema) > variety_score(same, schema) == 0.0


def test_pct_delta():
    assert pct_delta(0.28, 0.11) == -60.7
    assert pct_delta(0.0, 0.5) == 0.0
