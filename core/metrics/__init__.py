"""Domain-agnostic metrics. Must never import from ``domains/*``."""

from core.metrics.aggregators import aggregate_metrics
from core.metrics.base import Metric, MetricResult
from core.metrics.distribution import DurationStats, WinRateDistribution
from core.metrics.rating import EloMmrRating

__all__ = [
    "Metric",
    "MetricResult",
    "EloMmrRating",
    "WinRateDistribution",
    "DurationStats",
    "aggregate_metrics",
]
