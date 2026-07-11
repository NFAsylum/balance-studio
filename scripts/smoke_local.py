"""Smoke-test the local LLM hats against the running llama-server.

Run: LLM_BACKEND=local poetry run python scripts/smoke_local.py
Requires LOCAL_LLM_URL to point at a reachable OpenAI-compatible endpoint.
"""

from __future__ import annotations

import os
import time

from core.llm_local import LocalDesigner, LocalIterator, LocalJudge, _get_client
from domains.card_game.schema import get_schema, load_seed


def _timed(label: str, fn):
    start = time.perf_counter()
    result = fn()
    elapsed = time.perf_counter() - start
    print(f"[{elapsed:6.2f}s] {label}")
    return result


def main() -> None:
    url = os.getenv("LOCAL_LLM_URL", "(unset)")
    print(f"LOCAL_LLM_URL = {url}")

    client = _get_client()
    models = _timed("GET /v1/models", lambda: list(client.models.list()))
    print(f"  models: {[m.id for m in models]}")

    schema = get_schema()
    seed = load_seed()

    designed = _timed(
        "Designer.design(n=2)",
        lambda: LocalDesigner(client=client).design("aggro deck with cheap units", schema, [], 2),
    )
    print(f"  designed {len(designed)} units: {[u.model_dump()['name'] for u in designed]}")

    verdict = _timed(
        "Judge.judge(variety, 3 seed cards)",
        lambda: LocalJudge(client=client).judge(seed[:3], "variety"),
    )
    print(f"  variety score = {verdict.score:.2f} — {verdict.rationale}")

    sim_metrics = {"winrate": {u.model_dump()["name"]: 0.5 + 0.1 * i for i, u in enumerate(seed[:3])}}
    mods = _timed(
        "Iterator.propose_changes",
        lambda: LocalIterator(client=client).propose_changes(seed[:3], sim_metrics, {"variety": verdict.score}, []),
    )
    print(f"  proposed {len(mods)} modifications:")
    for m in mods:
        print(f"    - {m.kind} {m.target}: {m.reasoning}")

    print("\nsmoke OK")


if __name__ == "__main__":
    main()
