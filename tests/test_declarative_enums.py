"""FASE 1.5 — presets declare env behaviour (ability rename / type matchup / seniority ladder)
via the Environment, without breaking deterministic simulation. Empty config == plugin default."""

import pytest
from fastapi.testclient import TestClient

from api.main import app
from domains.card_game.simulator import CardGameSimulator, Deck, MatchEnv
from domains.creature_rpg.schema import load_seed as creature_seed
from domains.creature_rpg.simulator import CreatureRpgSimulator, GauntletEnv
from domains.team_composition.schema import SKILLS
from domains.team_composition.simulator import TeamCompositionSimulator, WorkloadEnv

_TYPES = ["fire", "water", "plant", "ice", "electric", "rock", "wind", "shadow"]


def _card(name, **kw):
    base = {"name": name, "cost": 0, "hp": 30, "damage": 0, "ability_kind": "none", "ability_value": 0}
    base.update(kw)
    return base


# -- card: ability rename --------------------------------------------------


def test_card_ability_map_resolves_renamed_ability():
    sim = CardGameSimulator()
    attacker = _card("Bolt", ability_kind="zap", ability_value=5)
    dummy = _card("Dummy")
    decks = [Deck(id="a", units=[attacker]), Deck(id="b", units=[dummy])]

    plain = sim.run(decks, MatchEnv(seed=1, turn_limit=4))  # "zap" unknown -> no effect
    mapped = sim.run(decks, MatchEnv(seed=1, turn_limit=4, ability_map={"zap": "deal_damage"}))
    # mapped: "zap" behaves like deal_damage -> the opponent hero takes damage
    assert mapped.outcome["final_hero_hp"]["b"] < plain.outcome["final_hero_hp"]["b"]


def test_card_empty_ability_map_is_identity():
    sim = CardGameSimulator()
    decks = [Deck(id="a", units=[_card("A", ability_kind="deal_damage", ability_value=5)]),
             Deck(id="b", units=[_card("B")])]
    assert sim.run(decks, MatchEnv(seed=1)).outcome == sim.run(decks, MatchEnv(seed=1, ability_map={})).outcome


# -- creature: type matchup ------------------------------------------------


def test_creature_resolve_matchups_prefers_env_table():
    sim = CreatureRpgSimulator()
    assert sim._resolve_matchups(GauntletEnv(seed=1)) is sim.matchup_table  # default
    custom = {"fire": {"water": 0.1}}
    assert sim._resolve_matchups(GauntletEnv(seed=1, type_matchup=custom)) == custom


def test_creature_custom_matchup_changes_battles():
    sim = CreatureRpgSimulator()
    creatures = creature_seed()[:5]
    default = sim.tournament(creatures, GauntletEnv(seed=1))
    flat = {a: {b: 0.1 for b in _TYPES} for a in _TYPES}  # everything barely effective
    custom = sim.tournament(creatures, GauntletEnv(seed=1, type_matchup=flat))
    # far weaker attacks -> battles drag differently (durations and/or winners change)
    assert [r.duration_steps for r in default] != [r.duration_steps for r in custom]


# -- team: seniority ladder ------------------------------------------------


def test_team_declarative_seniority_ladder():
    sim = TeamCompositionSimulator()
    person = {"name": "Solo", "seniority": "intern", "skills": list(SKILLS), "preferred_task_types": []}
    slow = sim.run([person], WorkloadEnv(seed=1, seniority_speed={"intern": 0.5}, deadline_days=3))
    fast = sim.run([person], WorkloadEnv(seed=1, seniority_speed={"intern": 3.0}, deadline_days=3))
    # "intern" is not in the plugin's default ladder — the declarative one is used (no KeyError),
    # and a faster multiplier clears more of the workload.
    assert fast.outcome["completion_rate"] > slow.outcome["completion_rate"]


# -- end-to-end: a preset carries sim_config through scenario creation -----


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SCENARIOS_DIR", str(tmp_path))
    with TestClient(app) as c:
        yield c


def test_mtg_preset_carries_sim_config_and_renamed_enum(client):
    resp = client.post("/scenarios", json={"domain": "card_game", "preset_id": "multi-color-tcg"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["sim_config"]["ability_map"]["direct_damage"] == "deal_damage"
    body = client.get(f"/scenarios/{resp.json()['id']}").json()
    ability = next(f for f in body["schema"]["fields"] if f["name"] == "ability_kind")
    assert set(ability["enum"]) == {"direct_damage", "restore_life", "negate", "card_draw"}
