"""Multi-objective definitions.

A user composes several :class:`Objective` entries (numeric balance, variety, cohesion, …);
the framework aggregates them into a single score or a Pareto front. The aggregator/Pareto
logic lands in a later sprint; this module currently defines the data model shared by the
scenario, the iterator hat, and the iteration engine.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class Objective(BaseModel):
    metric_name: str
    direction: Literal["minimize", "maximize", "target"]
    target_value: float | None = None
    weight: float = 1.0
