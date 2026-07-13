"""Tests for core.presets + the /presets endpoints."""

import json

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.registry import discover_domains
from core.presets import PresetStore

DOMAINS = ("card_game", "creature_rpg", "team_composition")


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SCENARIOS_DIR", str(tmp_path))
    with TestClient(app) as c:
        yield c


def test_ships_at_least_three_presets_per_domain():
    store = PresetStore()
    assert len(store.all()) >= 9
    for domain in DOMAINS:
        assert len(store.for_domain(domain)) >= 3, domain


def test_all_presets_apply_to_their_domain_schema():
    reg = discover_domains()
    for preset in PresetStore().all():
        base = reg.get(preset.domain).entity_schema()
        preset.apply_to(base).build_model()  # raises if overrides are invalid for the real schema


def test_get_by_id_and_missing():
    store = PresetStore()
    assert store.get("high-scale-duel") is not None
    assert store.get("does-not-exist") is None


def test_override_actually_rescales_range():
    reg = discover_domains()
    duel = PresetStore().get("high-scale-duel").apply_to(reg.get("card_game").entity_schema())
    assert next(f for f in duel.fields if f.name == "hp").range == (1, 5000)


def test_malformed_preset_fails_clearly(tmp_path):
    # a preset whose override is invalid for *any* schema: a num field with an enum
    (tmp_path / "card_game").mkdir()
    bad = {"id": "broken", "name": "Broken", "domain": "card_game",
           "schema_overrides": {"fields": [{"name": "hp", "enum": ["a", "b"]}]}}
    (tmp_path / "card_game" / "broken.json").write_text(json.dumps(bad))
    store = PresetStore(base_dir=tmp_path)
    preset = store.get("broken")  # loads structurally fine
    with pytest.raises((ValueError, Exception)):
        preset.apply_to(discover_domains().get("card_game").entity_schema())


def test_domain_folder_mismatch_raises(tmp_path):
    (tmp_path / "card_game").mkdir()
    wrong = {"id": "x", "name": "X", "domain": "creature_rpg"}  # folder says card_game
    (tmp_path / "card_game" / "x.json").write_text(json.dumps(wrong))
    with pytest.raises(ValueError, match="does not match folder"):
        PresetStore(base_dir=tmp_path).all()


# -- endpoints -------------------------------------------------------------


def test_list_presets_endpoint_filters_by_domain(client):
    body = client.get("/presets?domain=card_game").json()["presets"]
    assert len(body) >= 3 and all(p["domain"] == "card_game" for p in body)


def test_get_preset_endpoint_and_404(client):
    assert client.get("/presets/modern-mana-tcg").json()["id"] == "modern-mana-tcg"
    assert client.get("/presets/nope").status_code == 404


def test_preset_examples_validate_against_effective_schema():
    reg = discover_domains()
    for preset in PresetStore().all():
        eff = preset.apply_to(reg.get(preset.domain).entity_schema())
        model = eff.build_model()
        for ex in preset.examples:
            model(**ex)  # raises if an example is invalid for its own preset


def test_elemental_preset_declares_full_18_type_chart():
    reg = discover_domains()
    elemental = PresetStore().get("elemental-creatures-classic")
    eff = elemental.apply_to(reg.get("creature_rpg").entity_schema())
    assert len(next(f for f in eff.fields if f.name == "type").enum) == 18
    matchup = elemental.sim_config["type_matchup"]
    assert len(matchup) == 18 and all(len(row) == 18 for row in matchup.values())
    assert matchup["water"]["fire"] == 2.0 and matchup["electric"]["ground"] == 0.0  # real chart
