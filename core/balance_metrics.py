"""Balance-quality measures used by the balancing experiment (B6.5 follow-up).

- **Dispersion** (lower = more balanced): win-rate spread is already computed by
  ``WinRateDistribution`` (its ``data["std"]``); this module adds the reusable **variety**
  guardrail so we can tell "balanced" apart from "homogenised".
"""

from __future__ import annotations

import statistics
from typing import Any

from core.entity_schema import EntitySchema


def variety_score(entities: list[dict[str, Any]], schema: EntitySchema) -> float:
    """Mean pairwise Gower distance across entities (higher = more varied), in [0, 1].

    Per-field distance in [0, 1]: ``num`` = |Δ| / range; ``cat``/``bool`` = 0 if equal else 1;
    ``tag_set`` = Jaccard distance; ``str``/``map`` ignored. Works for any domain (numeric,
    categorical, or tag-based). Returns 0.0 for < 2 entities.
    """
    fields = [f for f in schema.fields if f.kind in ("num", "cat", "bool", "tag_set")]
    if len(entities) < 2 or not fields:
        return 0.0

    def field_distance(field, a: Any, b: Any) -> float:
        if field.kind == "num":
            lo, hi = field.range or (0.0, 1.0)
            span = hi - lo or 1.0
            return min(1.0, abs(float(a or 0.0) - float(b or 0.0)) / span)
        if field.kind in ("cat", "bool"):
            return 0.0 if a == b else 1.0
        # tag_set -> Jaccard distance
        sa, sb = set(a or []), set(b or [])
        union = sa | sb
        return 1.0 - (len(sa & sb) / len(union)) if union else 0.0

    def pair_distance(e1: dict, e2: dict) -> float:
        return statistics.fmean(field_distance(f, e1.get(f.name), e2.get(f.name)) for f in fields)

    distances = [
        pair_distance(entities[i], entities[j])
        for i in range(len(entities))
        for j in range(i + 1, len(entities))
    ]
    return statistics.fmean(distances) if distances else 0.0


def pct_delta(before: float, after: float) -> float:
    """Signed percent change from ``before`` to ``after`` (0.0 if before is 0)."""
    return 0.0 if before == 0 else round((after - before) / before * 100, 1)
