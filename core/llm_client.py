"""Transport clients for the JSON-returning LLM hats.

The three hats (Designer/Judge/Iterator) are transport-agnostic: they build a system+user
prompt and expect a JSON object back. The *only* thing that differs between running against a
local llama-server and the real Anthropic API is how that round-trip happens — so that is the
one thing we abstract here. Adding a backend is a new ``JsonChat``, not a new set of hats.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Protocol

_TIMEOUT = 180  # local server has no 429 to back off from; Anthropic calls are short
_ANTHROPIC_MODEL = "claude-sonnet-4-6"
_ANTHROPIC_MAX_TOKENS = 4096


class JsonChat(Protocol):
    """A transport that turns a system+user prompt into a JSON object."""

    def chat_json(self, system: str, user: str, temperature: float) -> dict[str, Any]: ...


# -- OpenAI-compatible (local llama-server) -------------------------------


def _get_client() -> Any:
    """Return an OpenAI client pointed at the local server. Raises if the URL is unset."""
    import openai

    url = os.getenv("LOCAL_LLM_URL")
    if not url:
        raise RuntimeError("LOCAL_LLM_URL is not set (required for LLM_BACKEND=local)")
    return openai.OpenAI(base_url=url, api_key="local", timeout=_TIMEOUT)


class OpenAIJsonChat:
    """Talks to an OpenAI-compatible server (llama-server) with JSON response mode."""

    def __init__(self, client: Any | None = None, model: str | None = None):
        self._client = client
        self.model = model or os.getenv("LOCAL_LLM_MODEL", "local")

    @property
    def client(self) -> Any:
        if self._client is None:
            self._client = _get_client()
        return self._client

    def chat_json(self, system: str, user: str, temperature: float) -> dict[str, Any]:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_format={"type": "json_object"},
            temperature=temperature,
        )
        return parse_json(response.choices[0].message.content or "")


# -- Anthropic API --------------------------------------------------------


class AnthropicJsonChat:
    """Talks to the real Anthropic API. Forces a single tool call so the response is a JSON
    object by construction (no fence/prose parsing needed). Needs ``ANTHROPIC_API_KEY``."""

    _TOOL = {
        "name": "emit_json",
        "description": "Return the requested JSON object.",
        "input_schema": {"type": "object"},
    }

    def __init__(self, client: Any | None = None, model: str | None = None):
        self._client = client
        self.model = model or os.getenv("ANTHROPIC_MODEL", _ANTHROPIC_MODEL)

    @property
    def client(self) -> Any:
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(timeout=_TIMEOUT)  # reads ANTHROPIC_API_KEY
        return self._client

    def chat_json(self, system: str, user: str, temperature: float) -> dict[str, Any]:
        message = self.client.messages.create(
            model=self.model,
            max_tokens=_ANTHROPIC_MAX_TOKENS,
            temperature=temperature,
            system=system + "\nRespond by calling emit_json with the requested JSON object.",
            tools=[self._TOOL],
            tool_choice={"type": "tool", "name": self._TOOL["name"]},
            messages=[{"role": "user", "content": user}],
        )
        for block in message.content:
            if getattr(block, "type", None) == "tool_use":
                return dict(block.input) if isinstance(block.input, dict) else {}
        return {}


def parse_json(content: str) -> Any:
    """Parse model output into JSON, tolerating markdown fences and surrounding prose.

    Small models often wrap JSON in ```json fences, add commentary, or emit a second object
    after the first — so we scan for the first brace and use ``raw_decode``, which stops at the
    end of the first valid JSON value and ignores trailing data.
    """
    text = content.strip()
    if not text:
        return {}
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        for i, ch in enumerate(text):
            if ch in "{[":
                try:
                    obj, _ = decoder.raw_decode(text[i:])
                    return obj
                except json.JSONDecodeError:
                    continue
        return {}
