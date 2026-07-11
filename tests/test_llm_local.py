"""Tests for core.llm_local + factory, using a mocked OpenAI client (no network)."""

import json
import types

import pytest

from core.llm_factory import Hats, build_hats
from core.llm_local import LocalDesigner, LocalIterator, LocalJudge, _get_client
from domains.card_game.schema import get_schema


def _fake_client(*json_payloads):
    """A stand-in OpenAI client whose chat.completions.create returns queued JSON strings."""
    contents = [json.dumps(p) if not isinstance(p, str) else p for p in json_payloads]

    class _Completions:
        def __init__(self):
            self.calls = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            content = contents.pop(0) if contents else "{}"
            return types.SimpleNamespace(
                choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=content))]
            )

    completions = _Completions()
    client = types.SimpleNamespace(chat=types.SimpleNamespace(completions=completions))
    client._completions = completions
    return client


def _unit(name, cost=2, ak="heal", av=2):
    return {"name": name, "cost": cost, "hp": 5, "damage": 3, "ability_kind": ak, "ability_value": av}


def _models():
    return get_schema().build_model()


def test_designer_returns_valid_entities():
    client = _fake_client({"entities": [_unit("Ace"), _unit("Bolt")]})
    out = LocalDesigner(client=client).design("aggro", get_schema(), [], 2)
    assert len(out) == 2
    assert {u.model_dump()["name"] for u in out} == {"Ace", "Bolt"}


def test_designer_retries_after_invalid_json():
    # first response: schema-invalid (cost out of range) -> 0 valid; second: valid -> 2
    client = _fake_client(
        {"entities": [_unit("Bad", cost=99)]},
        {"entities": [_unit("Ace"), _unit("Bolt")]},
    )
    out = LocalDesigner(client=client).design("aggro", get_schema(), [], 2)
    assert len(out) == 2
    assert len(client._completions.calls) == 2  # retried once


def test_judge_returns_scored_result_clamped():
    model = _models()
    entities = [model(**_unit("A")), model(**_unit("B"))]
    client = _fake_client({"score": 1.5, "rationale": "very diverse"})  # out of range -> clamp
    result = LocalJudge(client=client).judge(entities, "variety")
    assert 0.0 <= result.score <= 1.0 and result.score == 1.0
    assert result.rationale == "very diverse"


def test_iterator_filters_user_owned_targets():
    model = _models()
    entities = [model(**_unit("X")), model(**_unit("Y"))]
    client = _fake_client(
        {
            "modifications": [
                {"kind": "edit", "target": "X", "payload": _unit("X", cost=1), "reasoning": "nerf"},
                {"kind": "edit", "target": "Y", "payload": _unit("Y", cost=1), "reasoning": "nerf"},
            ]
        }
    )
    mods = LocalIterator(client=client).propose_changes(entities, {}, {}, [], user_owned={"X"})
    assert [m.target for m in mods] == ["Y"]  # X is user-owned -> dropped


def test_factory_returns_local_hats(monkeypatch):
    monkeypatch.setenv("LOCAL_LLM_URL", "http://localhost:9/v1")
    hats = build_hats("local")
    assert isinstance(hats, Hats)
    assert isinstance(hats.designer, LocalDesigner)
    assert isinstance(hats.judge, LocalJudge)
    assert isinstance(hats.iterator, LocalIterator)


def test_missing_local_url_raises(monkeypatch):
    monkeypatch.delenv("LOCAL_LLM_URL", raising=False)
    with pytest.raises(RuntimeError, match="LOCAL_LLM_URL"):
        _get_client()


def test_anthropic_backend_not_implemented():
    with pytest.raises(NotImplementedError):
        build_hats("anthropic")
