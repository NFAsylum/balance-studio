"""/health — backend/model reporting across fake, local (active/unreachable), anthropic."""

import httpx
import pytest
from fastapi.testclient import TestClient

from api.main import app
from core import llm_client


@pytest.fixture(autouse=True)
def _clear_model_cache():
    llm_client._MODEL_CACHE.clear()
    yield
    llm_client._MODEL_CACHE.clear()


def _client(tmp_path, monkeypatch, backend="fake", local_url=None):
    """A TestClient whose lifespan boots with the given LLM backend (env set pre-startup)."""
    monkeypatch.setenv("SCENARIOS_DIR", str(tmp_path))
    monkeypatch.setenv("LLM_BACKEND", backend)
    if local_url is not None:
        monkeypatch.setenv("LOCAL_LLM_URL", local_url)
    else:
        monkeypatch.delenv("LOCAL_LLM_URL", raising=False)
    return TestClient(app)


def _fake_models_response(model_id):
    class _Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"data": [{"id": model_id}]}

    return _Resp()


def test_health_fake_backend(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch, backend="fake") as c:
        r = c.get("/health")
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "ok"
        assert d["backend_llm"] == "fake"
        assert d["llm_model"] == "fake"
        assert "card_game" in d["domains_loaded"]
        assert d["event_log_ready"] is True


def test_health_local_active(tmp_path, monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda url, timeout: _fake_models_response("qwen2.5-coder-7b"))
    with _client(tmp_path, monkeypatch, backend="local", local_url="http://server:8080/v1") as c:
        d = c.get("/health").json()
        assert d["backend_llm"] == "local"
        assert d["llm_model"] == "qwen2.5-coder-7b"


def test_health_local_unreachable(tmp_path, monkeypatch):
    def _boom(url, timeout):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "get", _boom)
    with _client(tmp_path, monkeypatch, backend="local", local_url="http://server:8080/v1") as c:
        d = c.get("/health").json()
        assert d["backend_llm"] == "local"
        assert d["llm_model"] == "local-unreachable"


def test_health_anthropic_reports_configured_model(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-test-9")
    with _client(tmp_path, monkeypatch, backend="anthropic") as c:
        d = c.get("/health").json()
        assert d["backend_llm"] == "anthropic"
        assert d["llm_model"] == "claude-test-9"


def test_detect_local_model_caches_within_ttl(monkeypatch):
    monkeypatch.setenv("LOCAL_LLM_URL", "http://server:8080/v1")
    calls = {"n": 0}

    def _counting_get(url, timeout):
        calls["n"] += 1
        return _fake_models_response("m1")

    monkeypatch.setattr(httpx, "get", _counting_get)
    assert llm_client.detect_local_model() == "m1"
    assert llm_client.detect_local_model() == "m1"
    assert calls["n"] == 1  # second call served from the 30s cache, no extra HTTP round-trip


def test_detect_local_model_none_when_url_unset(monkeypatch):
    monkeypatch.delenv("LOCAL_LLM_URL", raising=False)
    assert llm_client.detect_local_model() is None
