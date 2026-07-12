"""Metric ABC and the uniform result envelope.

Every metric consumes a list of :class:`~core.simulator_interface.RunResult` and returns
a :class:`MetricResult`. The ``kind`` field lets the API/UI render any metric generically
(a rating renders as a bar chart, a distribution as a histogram) without knowing the
domain. Metrics are domain-agnostic — they must never import from ``domains/*``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from core.simulator_interface import RunResult


class MetricResult(BaseModel):
    """Uniform envelope so the report engine and UI treat every metric the same.

    ``kind`` drives generic rendering (e.g. ``"rating"``, ``"distribution"``); ``data``
    holds the metric-specific payload (JSON-serialisable).
    """

    kind: str
    name: str
    data: dict[str, Any]


class Metric(ABC):
    """Base class for all metrics. Concrete metrics set ``name``/``kind`` and implement
    :meth:`compute`."""

    name: str = "metric"
    kind: str = "generic"
    description: str = ""

    @abstractmethod
    def compute(self, runs: list[RunResult]) -> MetricResult:
        """Reduce a batch of runs to a :class:`MetricResult`. Pure; no I/O."""


def winner_of(run: RunResult) -> str | None:
    """Read the winning entity id from a run by the shared ``outcome['winner']`` convention.

    Returns ``None`` for draws or non-competitive runs. Centralised so every metric reads
    outcomes the same way without hardcoding domain structure.
    """
    winner = run.outcome.get("winner")
    if winner is None:
        return None
    return str(winner)
