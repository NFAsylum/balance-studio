"""Starter-gallery seeding: creates on an empty store, no-ops otherwise, stays idempotent."""

import uuid

import pytest

from api.registry import registry
from core.scenario import EventLog, Scenario
from scripts.seed_starter_scenarios import STARTERS, seed_starter_scenarios


@pytest.fixture(scope="module")
def loaded_registry():
    registry.load()
    return registry


@pytest.fixture
def event_log(tmp_path):
    return EventLog(base_dir=str(tmp_path))


def test_seeds_all_starters_on_empty_store(event_log, loaded_registry):
    ids = seed_starter_scenarios(event_log, loaded_registry)
    assert len(ids) == len(STARTERS)

    scenarios = event_log.list_scenarios()
    assert len(scenarios) == len(STARTERS)
    for s in scenarios:
        # every starter is populated (non-empty) and carries a preset + visual variant
        head = event_log.head(s.id, s.current_branch)
        assert head > 0, f"starter {s.name!r} has no entity events"
        assert s.preset_id is not None
        assert s.visual_variant is not None


def test_seed_is_idempotent(event_log, loaded_registry):
    first = seed_starter_scenarios(event_log, loaded_registry)
    assert first, "expected the first seed to create scenarios"
    second = seed_starter_scenarios(event_log, loaded_registry)
    assert second == []
    assert len(event_log.list_scenarios()) == len(STARTERS)


def test_no_op_when_a_scenario_already_exists(event_log, loaded_registry):
    event_log.init_scenario(Scenario(id=uuid.uuid4().hex[:12], domain="card_game", name="pre-existing"))
    created = seed_starter_scenarios(event_log, loaded_registry)
    assert created == []
    assert len(event_log.list_scenarios()) == 1


def test_seeded_entities_validate_against_the_effective_schema(event_log, loaded_registry):
    seed_starter_scenarios(event_log, loaded_registry)
    for s in event_log.list_scenarios():
        model = s.effective_schema(loaded_registry).build_model()
        events = event_log.read(s.id, s.current_branch)
        entity_events = [e for e in events if e.kind == "create_entity"]
        assert entity_events, f"{s.name!r} seeded no entities"
        for e in entity_events:
            model(**e.after)  # raises if the seeded entity does not fit the schema
