"""Tests for core.llm_generator using a mocked Anthropic client."""

from core.constraint_engine import Constraint
from core.entity_schema import EntitySchema
from core.llm_generator import _MAX_RETRIES, LlmGenerator


class _ToolUseBlock:
    def __init__(self, entities):
        self.type = "tool_use"
        self.input = {"entities": entities}


class _TextBlock:
    type = "text"
    text = "here you go"


class _Response:
    def __init__(self, entities):
        # include a text block to prove extraction picks the tool_use block
        self.content = [_TextBlock(), _ToolUseBlock(entities)]


class _FakeMessages:
    def __init__(self, batches):
        self._batches = list(batches)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        entities = self._batches.pop(0) if self._batches else []
        return _Response(entities)


class _FakeClient:
    def __init__(self, batches):
        self.messages = _FakeMessages(batches)


def _schema():
    return EntitySchema.from_dict(
        {
            "name": "Widget",
            "fields": [
                {"name": "name", "kind": "str", "max_len": 20},
                {"name": "cost", "kind": "num", "range": [1, 5]},
            ],
        }
    )


def test_retry_then_success_yields_three_entities():
    client = _FakeClient(
        [
            [{"name": "x", "cost": 99}, {"name": "y", "cost": 100}, {"name": "z", "cost": 50}],
            [{"name": "a", "cost": 1}, {"name": "b", "cost": 2}, {"name": "c", "cost": 3}],
        ]
    )
    out = LlmGenerator(client, _schema()).generate(n=3)
    assert len(out) == 3
    assert len(client.messages.calls) == 2  # first batch invalid, retried


def test_all_valid_first_call_no_retry():
    client = _FakeClient([[{"name": "a", "cost": 1}, {"name": "b", "cost": 2}, {"name": "c", "cost": 3}]])
    out = LlmGenerator(client, _schema()).generate(n=3)
    assert len(out) == 3
    assert len(client.messages.calls) == 1


def test_constraint_violations_filtered_and_topped_up():
    # cost 5 is schema-valid but violates the constraint (max 3); 'a' is dropped, then topped up.
    client = _FakeClient(
        [
            [{"name": "a", "cost": 5}, {"name": "b", "cost": 2}, {"name": "c", "cost": 3}],
            [{"name": "d", "cost": 1}],
        ]
    )
    constraints = [Constraint(kind="range", params={"field": "cost", "min": 1, "max": 3})]
    out = LlmGenerator(client, _schema()).generate(n=3, constraints=constraints)
    assert len(out) == 3
    assert all(o.cost <= 3 for o in out)


def test_max_retries_exhausted_returns_partial():
    client = _FakeClient([[{"name": "x", "cost": 99}] for _ in range(_MAX_RETRIES + 5)])
    out = LlmGenerator(client, _schema()).generate(n=3)
    assert out == []
    assert len(client.messages.calls) == _MAX_RETRIES + 1  # initial + retries, then stops


def test_forced_tool_choice_and_model_passed():
    client = _FakeClient([[{"name": "a", "cost": 1}]])
    gen = LlmGenerator(client, _schema())
    gen.generate(n=1)
    kwargs = client.messages.calls[0]
    assert kwargs["tool_choice"] == {"type": "tool", "name": "emit_widget_batch"}
    assert kwargs["model"] == gen.model
    assert kwargs["tools"][0]["name"] == "emit_widget_batch"
    # the entity object schema is nested under the batch array items
    items = kwargs["tools"][0]["input_schema"]["properties"]["entities"]["items"]
    assert items["type"] == "object"
    assert set(items["required"]) == {"name", "cost"}


def test_error_feedback_included_in_retry_prompt():
    client = _FakeClient(
        [
            [{"name": "x", "cost": 99}],
            [{"name": "a", "cost": 1}],
        ]
    )
    LlmGenerator(client, _schema()).generate(n=1)
    retry_prompt = client.messages.calls[1]["messages"][0]["content"]
    assert "previous attempt" in retry_prompt.lower()
    assert "cost" in retry_prompt  # the offending field surfaces in the feedback


def test_missing_tool_use_block_is_handled():
    class _Empty:
        content = [_TextBlock()]

    class _EmptyMessages:
        def __init__(self):
            self.calls = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            return _Empty()

    class _EmptyClient:
        messages = _EmptyMessages()

    out = LlmGenerator(_EmptyClient(), _schema()).generate(n=2)
    assert out == []
