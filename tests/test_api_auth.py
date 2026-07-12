"""Write-protection (audit #03): API key on mutations, per-IP rate limit, restricted CORS.

We drive a nonexistent-scenario write (`POST /iterate`) so requests that pass the middleware
land on a fast 404 handler — no disk writes, and 401/429 (middleware) is cleanly distinct."""

import pytest
from fastapi.testclient import TestClient

from api import dependencies as apideps
from api.main import app

_WRITE = "/scenarios/nope/iterate"
_BODY = {"phase": "simulate"}


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    apideps._rate_state.clear()
    monkeypatch.setattr(apideps, "_RATE_LIMIT_PER_MIN", 1000)  # generous unless a test lowers it
    yield
    apideps._rate_state.clear()


def test_write_without_key_is_401_when_key_configured(monkeypatch, client):
    monkeypatch.setattr(apideps, "_API_KEY", "secret")
    assert client.post(_WRITE, json=_BODY).status_code == 401


def test_write_with_wrong_key_is_401(monkeypatch, client):
    monkeypatch.setattr(apideps, "_API_KEY", "secret")
    assert client.post(_WRITE, json=_BODY, headers={"X-API-Key": "nope"}).status_code == 401


def test_write_with_correct_key_passes_middleware(monkeypatch, client):
    monkeypatch.setattr(apideps, "_API_KEY", "secret")
    # Passes auth -> reaches handler -> 404 (scenario 'nope' doesn't exist). Not 401.
    assert client.post(_WRITE, json=_BODY, headers={"X-API-Key": "secret"}).status_code == 404


def test_no_key_configured_allows_writes(monkeypatch, client):
    monkeypatch.setattr(apideps, "_API_KEY", None)  # dev mode
    assert client.post(_WRITE, json=_BODY).status_code == 404


def test_rate_limit_returns_429(monkeypatch, client):
    monkeypatch.setattr(apideps, "_API_KEY", None)
    monkeypatch.setattr(apideps, "_RATE_LIMIT_PER_MIN", 2)
    assert client.post(_WRITE, json=_BODY).status_code == 404
    assert client.post(_WRITE, json=_BODY).status_code == 404
    assert client.post(_WRITE, json=_BODY).status_code == 429  # 3rd exceeds the limit


def test_cors_allows_configured_origin_only(client):
    ok = client.get("/domains", headers={"Origin": "http://localhost:3000"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:3000"
    evil = client.get("/domains", headers={"Origin": "http://evil.example"})
    assert evil.headers.get("access-control-allow-origin") != "http://evil.example"
