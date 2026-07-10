"""Tests for the scenario workflow API (all Fake-backed): happy path + 404 + 422."""

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SCENARIOS_DIR", str(tmp_path))
    with TestClient(app) as c:
        yield c


def _new_scenario(client, **overrides):
    body = {"domain": "card_game", "name": "T", "brief": "aggro cheap", "n_entities": 4}
    body.update(overrides)
    resp = client.post("/scenarios", json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _unit(name="Custom", cost=2):
    return {"name": name, "cost": cost, "hp": 5, "damage": 3, "ability_kind": "heal", "ability_value": 2}


def test_create_and_get_scenario(client):
    sid = _new_scenario(client)
    resp = client.get(f"/scenarios/{sid}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["scenario"]["domain"] == "card_game"
    assert body["entities"] == {}
    assert body["head_seq"] == 0


def test_iterate_design_then_simulate(client):
    sid = _new_scenario(client)
    design = client.post(f"/scenarios/{sid}/iterate", json={"phase": "design"})
    assert design.status_code == 200
    assert design.json()["events_appended"] == 4

    entities = client.get(f"/scenarios/{sid}").json()["entities"]
    assert len(entities) == 4

    sim = client.post(f"/scenarios/{sid}/iterate", json={"phase": "simulate"})
    assert sim.status_code == 200
    assert sim.json()["phase"] == "simulate"
    assert sim.json()["details"]["winrate"]


def test_manual_entity_crud(client):
    sid = _new_scenario(client)
    assert client.post(f"/scenarios/{sid}/entities", json={"entity": _unit("Ace")}).status_code == 200
    assert "Ace" in client.get(f"/scenarios/{sid}").json()["entities"]

    edited = client.patch(f"/scenarios/{sid}/entities/Ace", json={"entity": _unit("Ace", cost=4)})
    assert edited.status_code == 200 and edited.json()["kind"] == "edit_entity"
    assert client.get(f"/scenarios/{sid}").json()["entities"]["Ace"]["cost"] == 4

    assert client.delete(f"/scenarios/{sid}/entities/Ace").status_code == 200
    assert "Ace" not in client.get(f"/scenarios/{sid}").json()["entities"]


def test_objectives_and_history(client):
    sid = _new_scenario(client)
    objs = {"objectives": [{"metric_name": "winrate_std", "direction": "minimize", "weight": 1.0}]}
    assert client.post(f"/scenarios/{sid}/objectives", json=objs).status_code == 200
    history = client.get(f"/scenarios/{sid}/history").json()["events"]
    assert any(e["kind"] == "set_objective" for e in history)


def test_branch_create_and_diff(client):
    sid = _new_scenario(client)
    client.post(f"/scenarios/{sid}/iterate", json={"phase": "design"})  # some events to fork from
    head = client.get(f"/scenarios/{sid}").json()["head_seq"]

    created = client.post(f"/scenarios/{sid}/branches", json={"parent_seq": head, "name": "alt"})
    assert created.status_code == 200 and created.json()["branch_id"] == "alt"

    diff = client.get(f"/scenarios/{sid}/branches/main/diff/alt")
    assert diff.status_code == 200
    body = diff.json()
    assert body["branch_a"] == "main" and body["branch_b"] == "alt"
    # freshly forked: identical, no exclusive events
    assert body["exclusive_events_a"] == 0 and body["exclusive_events_b"] == 0


# -- error cases -----------------------------------------------------------


def test_unknown_scenario_404(client):
    assert client.get("/scenarios/deadbeef").status_code == 404


def test_unknown_domain_on_create_404(client):
    assert client.post("/scenarios", json={"domain": "nope"}).status_code == 404


def test_bad_phase_422(client):
    sid = _new_scenario(client)
    assert client.post(f"/scenarios/{sid}/iterate", json={"phase": "dance"}).status_code == 422


def test_invalid_entity_422(client):
    sid = _new_scenario(client)
    bad = {"entity": {"name": "X", "cost": 99, "hp": 5, "damage": 3, "ability_kind": "heal", "ability_value": 2}}
    assert client.post(f"/scenarios/{sid}/entities", json=bad).status_code == 422


def test_diff_unknown_branch_404(client):
    sid = _new_scenario(client)
    assert client.get(f"/scenarios/{sid}/branches/main/diff/ghost").status_code == 404
