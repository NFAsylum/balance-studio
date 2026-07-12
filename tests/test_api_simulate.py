"""Tests for the domain-agnostic API: registry discovery, simulate, and errors."""

import pytest
from fastapi.testclient import TestClient

from api.main import app
from domains.card_game.schema import load_seed


@pytest.fixture(scope="module")
def client():
    # `with` triggers the lifespan startup, which loads the domain registry.
    with TestClient(app) as c:
        yield c


def _decks():
    units = [u.model_dump() for u in load_seed()]
    return [
        {"id": "aggro", "units": units[:5]},
        {"id": "control", "units": units[5:]},
    ]


def test_registry_discovers_card_game(client):
    resp = client.get("/domains")
    assert resp.status_code == 200
    assert "card_game" in resp.json()["domains"]


def test_get_schema(client):
    resp = client.get("/domains/card_game/schema")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Unit"


def test_simulate_happy_path_returns_report(client):
    body = {"entities": _decks(), "env": {"seed": 42}, "n_runs": 10}
    resp = client.post("/domains/card_game/simulate", json=body)
    assert resp.status_code == 200, resp.text
    report = resp.json()
    assert report["domain"] == "card_game"
    assert report["n_runs"] == 10
    # default metrics are present and keyed by name
    assert set(report["metric_results"]) == {"elo_mmr", "winrate_distribution", "duration_stats"}
    assert report["metric_results"]["elo_mmr"]["kind"] == "rating"
    assert report["entity_set_hash"] and report["env_hash"]


def test_simulate_metric_filter(client):
    body = {"entities": _decks(), "env": {"seed": 1}, "n_runs": 3, "metrics": ["elo_mmr"]}
    resp = client.post("/domains/card_game/simulate", json=body)
    assert resp.status_code == 200
    assert set(resp.json()["metric_results"]) == {"elo_mmr"}


def test_unknown_domain_404(client):
    resp = client.post("/domains/nope/simulate", json={"entities": [], "env": {"seed": 1}})
    assert resp.status_code == 404


def test_malformed_body_422(client):
    # missing required "entities" field
    resp = client.post("/domains/card_game/simulate", json={"env": {"seed": 1}})
    assert resp.status_code == 422


def test_invalid_env_422(client):
    # unknown env field -> MatchEnv forbids extras
    body = {"entities": _decks(), "env": {"seed": 1, "bogus": 9}, "n_runs": 1}
    resp = client.post("/domains/card_game/simulate", json=body)
    assert resp.status_code == 422


def test_generate_returns_entities_via_fake_designer(client):
    resp = client.post("/domains/card_game/generate", json={"n": 3, "user_intent": "aggro"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["requested"] == 3
    assert len(body["entities"]) == 3
    # generated units validate against the card schema (schema-shaped output)
    assert all("ability_kind" in u for u in body["entities"])


def test_list_domain_metrics(client):
    resp = client.get("/domains/card_game/metrics")
    assert resp.status_code == 200
    names = {m["name"] for m in resp.json()["metrics"]}
    assert {"elo_mmr", "winrate_distribution"}.issubset(names)
    assert client.get("/domains/nope/metrics").status_code == 404
