"""Anthropic-backed hats — production path (``LLM_BACKEND=anthropic``).

There is no hat logic here: the Designer/Judge/Iterator prompt-building, JSON parsing, schema
validation and retry all live in :mod:`core.llm_local` and are reused verbatim. The only thing
that changes for a cloud backend is the transport, so these classes just inject an
:class:`~core.llm_client.AnthropicJsonChat`. Needs ``ANTHROPIC_API_KEY`` (model via
``ANTHROPIC_MODEL``, default ``claude-sonnet-4-6``).
"""

from __future__ import annotations

from typing import Any

from core.llm_client import AnthropicJsonChat
from core.llm_local import LocalDesigner, LocalIterator, LocalJudge


class AnthropicDesigner(LocalDesigner):
    def __init__(self, client: Any | None = None, model: str | None = None):
        super().__init__(transport=AnthropicJsonChat(client=client, model=model))


class AnthropicJudge(LocalJudge):
    def __init__(self, client: Any | None = None, model: str | None = None):
        super().__init__(transport=AnthropicJsonChat(client=client, model=model))


class AnthropicIterator(LocalIterator):
    def __init__(self, client: Any | None = None, model: str | None = None):
        super().__init__(transport=AnthropicJsonChat(client=client, model=model))
