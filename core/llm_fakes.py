"""Deterministic, cost-free stand-ins for the three LLM hats.

Every Fake is a pure function of its inputs (hash-derived), so demos and tests reproduce
exactly. They implement the same protocols as the real Anthropic hats (Sprint 6), so the
iteration engine is written once against the protocol and the backend is swapped by config.
"""

from __future__ import annotations

import hashlib
from typing import Any

from pydantic import BaseModel

from core.constraint_engine import Constraint
from core.entity_schema import EntitySchema, FieldSpec
from core.llm_hats import JudgeResult, Modification
from core.objectives import Objective

# Winrate thresholds the FakeIterator reacts to.
_OVERPOWERED = 0.6
_UNDERPOWERED = 0.4


def _hash_int(*parts: Any) -> int:
    return int(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest(), 16)


class FakeDesigner:
    """Generates schema-valid entities deterministically from the brief + index."""

    def design(
        self,
        brief: str,
        schema: EntitySchema,
        constraints: list[Constraint],
        n: int,
    ) -> list[BaseModel]:
        model = schema.build_model()
        return [model(**self._entity(schema, brief, i)) for i in range(n)]

    def _entity(self, schema: EntitySchema, brief: str, i: int) -> dict[str, Any]:
        return {f.name: self._value(f, brief, i) for f in schema.fields}

    @staticmethod
    def _value(field: FieldSpec, brief: str, i: int) -> Any:
        h = _hash_int(brief, i, field.name)
        if field.kind == "num":
            if field.range is not None:
                lo, hi = field.range
                return lo + (h % (int(hi - lo) + 1))
            return h % 100
        if field.kind == "cat":
            assert field.enum is not None
            return field.enum[h % len(field.enum)]
        if field.kind == "bool":
            return bool(h % 2)
        if field.kind == "str":
            stem = (brief.split()[0] if brief.strip() else field.name).replace(" ", "")
            token = f"{stem}-{i}"
            if field.max_len is not None:
                token = token[: field.max_len]
            if field.min_len is not None and len(token) < field.min_len:
                token = (token + "x" * field.min_len)[: field.min_len]
            return token
        return []  # tag_set


class FakeJudge:
    """Returns a deterministic 0..1 score derived from the criterion + entities."""

    def judge(self, entities: list[BaseModel], criterion: str) -> JudgeResult:
        payload = [e.model_dump() for e in entities]
        score = (_hash_int(criterion, payload) % 1001) / 1000.0
        return JudgeResult(
            score=score,
            rationale=f"FakeJudge[{criterion}] over {len(entities)} entities (deterministic).",
        )


class FakeIterator:
    """Mechanical proposals: nerf overperformers, buff underperformers (first numeric field)."""

    def propose_changes(
        self,
        entities: list[BaseModel],
        sim_metrics: dict[str, Any],
        judge_metrics: dict[str, Any],
        objectives: list[Objective],
    ) -> list[Modification]:
        winrates = self._winrates(sim_metrics)
        mods: list[Modification] = []
        for entity in entities:
            data = entity.model_dump()
            key = data.get("name") or data.get("id")
            if key is None or key not in winrates:
                continue
            field = self._first_numeric_field(data)
            if field is None:
                continue
            winrate = winrates[key]
            if winrate > _OVERPOWERED:
                mods.append(self._tweak(key, data, field, -1, winrate, "nerf", _OVERPOWERED))
            elif winrate < _UNDERPOWERED:
                mods.append(self._tweak(key, data, field, +1, winrate, "buff", _UNDERPOWERED))
        return mods

    @staticmethod
    def _tweak(
        key: str, data: dict[str, Any], field: str, delta: int, winrate: float, verb: str, thr: float
    ) -> Modification:
        payload = dict(data)
        payload[field] = data[field] + delta
        return Modification(
            kind="edit",
            target=key,
            payload=payload,
            reasoning=f"{key} winrate {winrate:.0%} crosses {thr:.0%}; {verb} {field} by {delta:+d}",
        )

    @staticmethod
    def _first_numeric_field(data: dict[str, Any]) -> str | None:
        for name, value in data.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return name
        return None

    @staticmethod
    def _winrates(sim_metrics: dict[str, Any]) -> dict[str, float]:
        """Accept either a flat ``{'winrate': {id: rate}}`` or a report-shaped metric block."""
        if "winrate" in sim_metrics:
            return sim_metrics["winrate"]
        block = sim_metrics.get("winrate_distribution")
        if isinstance(block, dict):
            data = block.get("data", block)
            return data.get("per_entity", {})
        return {}
