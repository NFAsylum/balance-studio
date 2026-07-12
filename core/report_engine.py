"""Consolidate runs + metrics into a serialisable Report for the API/UI.

The report is domain-agnostic: it carries the domain name, run count, content hashes
(for caching and reproducibility), and the metric results keyed by metric name.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from core.metrics.aggregators import aggregate_metrics
from core.metrics.base import Metric, MetricResult
from core.simulator_interface import RunResult


def hash_json(obj: Any) -> str:
    """Stable sha256 of any JSON-able object (sorted keys) — used for cache/report keys."""
    encoded = json.dumps(obj, sort_keys=True, default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


class Report(BaseModel):
    domain: str
    n_runs: int
    entity_set_hash: str
    env_hash: str
    metric_results: dict[str, MetricResult]
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def build_report(
    *,
    domain: str,
    runs: list[RunResult],
    metrics: list[Metric],
    entity_set_hash: str,
    env_hash: str,
    generated_at: datetime | None = None,
) -> Report:
    """Aggregate ``metrics`` over ``runs`` and wrap them in a :class:`Report`."""
    metric_results = aggregate_metrics(metrics, runs)
    return Report(
        domain=domain,
        n_runs=len(runs),
        entity_set_hash=entity_set_hash,
        env_hash=env_hash,
        metric_results=metric_results,
        generated_at=generated_at or datetime.now(timezone.utc),
    )
