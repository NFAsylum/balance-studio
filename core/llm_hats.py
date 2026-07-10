"""The three LLM roles ("hats"), as isolated protocols.

Each hat is a distinct capability with its own protocol so the framework can swap a Fake
(dev, free, deterministic) for a real Anthropic implementation (Sprint 6) per role, via
config. Simulation is never one of these — it stays LLM-free so objective results are ground
truth, not model opinion.

- ``DesignerLlm``  — natural-language brief → entities.
- ``SubjectiveJudgeLlm`` — qualitative score (variety, cohesion, thematic consistency).
- ``IteratorLlm`` — state + metrics + objectives → proposed modifications.
"""

from __future__ import annotations

from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from core.constraint_engine import Constraint
from core.entity_schema import EntitySchema
from core.objectives import Objective


class JudgeResult(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    rationale: str


class Modification(BaseModel):
    """A proposed change to the entity set. ``target`` is None only for ``create``."""

    kind: Literal["create", "edit", "delete"]
    target: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    reasoning: str = ""


@runtime_checkable
class DesignerLlm(Protocol):
    def design(
        self,
        brief: str,
        schema: EntitySchema,
        constraints: list[Constraint],
        n: int,
    ) -> list[BaseModel]:
        """Materialise ``n`` entities from a natural-language ``brief``."""
        ...


@runtime_checkable
class SubjectiveJudgeLlm(Protocol):
    def judge(self, entities: list[BaseModel], criterion: str) -> JudgeResult:
        """Score the entity set qualitatively against ``criterion`` (0..1 + rationale)."""
        ...


@runtime_checkable
class IteratorLlm(Protocol):
    def propose_changes(
        self,
        entities: list[BaseModel],
        sim_metrics: dict[str, Any],
        judge_metrics: dict[str, Any],
        objectives: list[Objective],
    ) -> list[Modification]:
        """Propose create/edit/delete modifications given current state + metrics + objectives.

        Authorship guardrail (skip entities last edited by ``user``) is enforced by the
        iteration engine, which has the event history; a bare hat does not.
        """
        ...
