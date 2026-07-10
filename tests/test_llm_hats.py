"""Tests for the 3 LLM hats (protocols) and their deterministic Fakes."""

from core.entity_schema import EntitySchema
from core.llm_fakes import FakeDesigner, FakeIterator, FakeJudge
from core.llm_hats import (
    DesignerLlm,
    IteratorLlm,
    JudgeResult,
    Modification,
    SubjectiveJudgeLlm,
)


def _card_schema() -> EntitySchema:
    return EntitySchema.from_dict(
        {
            "name": "Unit",
            "fields": [
                {"name": "name", "kind": "str", "min_len": 1, "max_len": 40},
                {"name": "cost", "kind": "num", "range": [1, 5]},
                {"name": "power", "kind": "num", "range": [1, 10]},
                {"name": "ability", "kind": "cat", "enum": ["deal_damage", "heal"]},
                {"name": "legendary", "kind": "bool"},
            ],
        }
    )


def _power_schema() -> EntitySchema:
    return EntitySchema.from_dict(
        {"name": "E", "fields": [{"name": "name", "kind": "str"}, {"name": "power", "kind": "num", "range": [1, 20]}]}
    )


# -- protocol conformance --------------------------------------------------


def test_fakes_satisfy_protocols():
    assert isinstance(FakeDesigner(), DesignerLlm)
    assert isinstance(FakeJudge(), SubjectiveJudgeLlm)
    assert isinstance(FakeIterator(), IteratorLlm)


# -- FakeDesigner ----------------------------------------------------------


def test_designer_returns_n_valid_entities():
    schema = _card_schema()
    entities = FakeDesigner().design("aggro cheap units", schema, [], n=5)
    assert len(entities) == 5
    model = schema.build_model()
    for e in entities:
        model(**e.model_dump())  # re-validates; raises if invalid
    # names are unique
    assert len({e.name for e in entities}) == 5


def test_designer_is_deterministic():
    schema = _card_schema()
    a = FakeDesigner().design("cyberpunk deck", schema, [], n=4)
    b = FakeDesigner().design("cyberpunk deck", schema, [], n=4)
    assert [e.model_dump() for e in a] == [e.model_dump() for e in b]


def test_designer_handles_map_and_tag_set_fields():
    schema = EntitySchema.from_dict(
        {
            "name": "C",
            "fields": [
                {"name": "name", "kind": "str"},
                {"name": "skills", "kind": "tag_set"},
                {"name": "resistances", "kind": "map", "enum": ["fire", "water"]},
            ],
        }
    )
    for entity in FakeDesigner().design("brief", schema, [], 3):
        data = entity.model_dump()
        assert isinstance(data["resistances"], dict)
        assert isinstance(data["skills"], list)


def test_designer_respects_ranges_and_enums():
    schema = _card_schema()
    for e in FakeDesigner().design("x", schema, [], n=20):
        assert 1 <= e.cost <= 5
        assert 1 <= e.power <= 10
        assert e.ability in ("deal_damage", "heal")


# -- FakeJudge -------------------------------------------------------------


def test_judge_returns_score_in_range_with_rationale():
    entities = FakeDesigner().design("x", _card_schema(), [], n=3)
    result = FakeJudge().judge(entities, "variety")
    assert isinstance(result, JudgeResult)
    assert 0.0 <= result.score <= 1.0
    assert "variety" in result.rationale


def test_judge_is_deterministic_and_criterion_sensitive():
    entities = FakeDesigner().design("x", _card_schema(), [], n=3)
    judge = FakeJudge()
    assert judge.judge(entities, "variety").score == judge.judge(entities, "variety").score
    # different criteria generally produce different scores
    assert judge.judge(entities, "variety").score != judge.judge(entities, "cohesion").score


# -- FakeIterator ----------------------------------------------------------


def test_iterator_nerfs_overperformer_and_buffs_underperformer():
    schema = _power_schema()
    model = schema.build_model()
    entities = [model(name="A", power=8), model(name="B", power=8), model(name="C", power=8)]
    sim_metrics = {"winrate": {"A": 0.8, "B": 0.2, "C": 0.5}}
    mods = FakeIterator().propose_changes(entities, sim_metrics, {}, [])

    by_target = {m.target: m for m in mods}
    assert set(by_target) == {"A", "B"}  # C (balanced) untouched
    assert by_target["A"].kind == "edit" and by_target["A"].payload["power"] == 7  # nerf
    assert by_target["B"].payload["power"] == 9  # buff


def test_iterator_reads_report_shaped_metrics():
    schema = _power_schema()
    model = schema.build_model()
    entities = [model(name="A", power=5)]
    report_metrics = {"winrate_distribution": {"data": {"per_entity": {"A": 0.9}}}}
    mods = FakeIterator().propose_changes(entities, report_metrics, {}, [])
    assert len(mods) == 1 and mods[0].target == "A"


def test_iterator_no_proposals_when_no_winrates():
    schema = _power_schema()
    model = schema.build_model()
    entities = [model(name="A", power=5)]
    assert FakeIterator().propose_changes(entities, {}, {}, []) == []


def test_modification_model_shape():
    m = Modification(kind="create", payload={"name": "New"}, reasoning="add variety")
    assert m.target is None and m.kind == "create"
