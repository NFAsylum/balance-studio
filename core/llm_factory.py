"""Select the LLM hat implementations by backend.

``LLM_BACKEND=fake``  -> deterministic Fakes (dev/tests, no network)
``LLM_BACKEND=local`` -> local OpenAI-compatible server (llama-server)
``LLM_BACKEND=anthropic`` -> not implemented (superseded by the local backend)
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from core.llm_hats import DesignerLlm, IteratorLlm, SubjectiveJudgeLlm


@dataclass
class Hats:
    designer: DesignerLlm
    judge: SubjectiveJudgeLlm
    iterator: IteratorLlm


def build_hats(backend: str | None = None) -> Hats:
    backend = (backend or os.getenv("LLM_BACKEND", "fake")).lower()
    if backend == "fake":
        from core.llm_fakes import FakeDesigner, FakeIterator, FakeJudge

        return Hats(FakeDesigner(), FakeJudge(), FakeIterator())
    if backend == "local":
        from core.llm_local import LocalDesigner, LocalIterator, LocalJudge

        return Hats(LocalDesigner(), LocalJudge(), LocalIterator())
    if backend == "anthropic":
        raise NotImplementedError(
            "the 'anthropic' backend is not implemented — use LLM_BACKEND=fake or local"
        )
    raise ValueError(f"unknown LLM_BACKEND: {backend!r} (expected fake|local|anthropic)")
