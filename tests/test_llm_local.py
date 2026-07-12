"""Tests for core.llm_local + factory, using a mocked OpenAI client (no network)."""

import json
import types

import pytest

from core.llm_anthropic import AnthropicDesigner, AnthropicIterator, AnthropicJudge
from core.llm_client import AnthropicJsonChat
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


def _fake_anthropic_client(tool_input):
    """Stand-in Anthropic client whose messages.create returns one tool_use block."""

    class _Messages:
        def __init__(self):
            self.calls = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            block = types.SimpleNamespace(type="tool_use", name="emit_json", input=tool_input)
            return types.SimpleNamespace(content=[block])

    messages = _Messages()
    client = types.SimpleNamespace(messages=messages)
    client._messages = messages
    return client


def test_factory_returns_anthropic_hats():
    # Lazy client — no ANTHROPIC_API_KEY / network touched at construction time.
    hats = build_hats("anthropic")
    assert isinstance(hats, Hats)
    assert isinstance(hats.designer, AnthropicDesigner)
    assert isinstance(hats.judge, AnthropicJudge)
    assert isinstance(hats.iterator, AnthropicIterator)


def test_anthropic_transport_returns_tool_input_dict():
    client = _fake_anthropic_client({"score": 0.7, "rationale": "ok"})
    chat = AnthropicJsonChat(client=client, model="claude-sonnet-4-6")
    out = chat.chat_json("sys", "user", temperature=0.3)
    assert out == {"score": 0.7, "rationale": "ok"}
    assert client._messages.calls[0]["tool_choice"]["name"] == "emit_json"


def test_anthropic_designer_reuses_local_hat_logic():
    # Same hat code as local, different transport — designs valid entities from a tool reply.
    client = _fake_anthropic_client({"entities": [_unit("Ace"), _unit("Bolt")]})
    designer = AnthropicDesigner(client=client)
    out = designer.design("aggro", get_schema(), [], 2)
    assert {u.model_dump()["name"] for u in out} == {"Ace", "Bolt"}
