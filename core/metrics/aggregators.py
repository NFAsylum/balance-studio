"""Combine multiple metrics over one batch of runs into a keyed result set.

This is the seam the report engine uses: give it the domain's metrics and the runs, get
back ``{metric_name: MetricResult}`` ready to serialise for the API/UI.
"""

from __future__ import annotations

from core.metrics.base import Metric, MetricResult
from core.simulator_interface import RunResult


def aggregate_metrics(metrics: list[Metric], runs: list[RunResult]) -> dict[str, MetricResult]:
    """Compute every metric over ``runs``, keyed by ``metric.name``.

    Raises ``ValueError`` on duplicate metric names so a report never silently drops one.
    """
    results: dict[str, MetricResult] = {}
    for metric in metrics:
        if metric.name in results:
            raise ValueError(f"duplicate metric name in batch: {metric.name!r}")
        results[metric.name] = metric.compute(runs)
    return results
