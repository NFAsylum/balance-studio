"""Declarative constraint validation.

Constraints are data (``kind`` + ``params``), not code, so a domain or an LLM prompt
can express balance rules without touching the core. The engine evaluates them against
entities produced by an :mod:`core.entity_schema` model.

Supported kinds and their ``params``:

- ``range``            ``{field, min, max}`` — numeric field within [min, max] inclusive.
- ``sum_of_fields``    ``{fields, min?, max?}`` — sum of the named numeric fields in [min, max].
- ``forbidden_combo``  ``{field, tags}`` — violated if the tag_set field contains *all* tags.
- ``required_tag``     ``{field, any_of}`` — violated if the tag_set field contains *none* of them.
- ``unique_across_set````{field}`` — the field value must be unique across the entity set
                        (only meaningful in :meth:`ConstraintEngine.validate_set`).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

ConstraintKind = Literal[
    "range",
    "sum_of_fields",
    "forbidden_combo",
    "required_tag",
    "unique_across_set",
]


class Constraint(BaseModel):
    kind: ConstraintKind
    params: dict[str, Any]


class ValidationResult(BaseModel):
    is_valid: bool
    violations: list[str]


def _get(entity: Any, field: str) -> Any:
    """Read ``field`` from a Pydantic model or a plain dict; None if absent."""
    if isinstance(entity, BaseModel):
        return getattr(entity, field, None)
    if isinstance(entity, dict):
        return entity.get(field)
    return getattr(entity, field, None)


def _require(params: dict[str, Any], key: str, kind: str) -> Any:
    if key not in params:
        raise ValueError(f"constraint '{kind}' requires param '{key}'")
    return params[key]


class ConstraintEngine:
    """Evaluates :class:`Constraint` lists against single entities or whole sets."""

    def validate(self, entity: Any, constraints: list[Constraint]) -> ValidationResult:
        """Validate one entity against per-entity constraints.

        ``unique_across_set`` is set-level and is ignored here; use :meth:`validate_set`.
        """
        violations: list[str] = []
        for c in constraints:
            if c.kind == "unique_across_set":
                continue  # needs the full set
            violations.extend(self._eval_single(entity, c))
        return ValidationResult(is_valid=not violations, violations=violations)

    def validate_set(
        self, entities: list[Any], constraints: list[Constraint]
    ) -> list[ValidationResult]:
        """Validate each entity, folding in set-level ``unique_across_set`` results."""
        per_entity: list[list[str]] = [[] for _ in entities]

        for c in constraints:
            if c.kind == "unique_across_set":
                for idx, msg in self._eval_unique(entities, c):
                    per_entity[idx].append(msg)
            else:
                for i, entity in enumerate(entities):
                    per_entity[i].extend(self._eval_single(entity, c))

        return [
            ValidationResult(is_valid=not v, violations=v) for v in per_entity
        ]

    # -- per-entity evaluation --------------------------------------------

    def _eval_single(self, entity: Any, c: Constraint) -> list[str]:
        if c.kind == "range":
            return self._eval_range(entity, c.params)
        if c.kind == "sum_of_fields":
            return self._eval_sum(entity, c.params)
        if c.kind == "forbidden_combo":
            return self._eval_forbidden_combo(entity, c.params)
        if c.kind == "required_tag":
            return self._eval_required_tag(entity, c.params)
        raise ValueError(f"unknown constraint kind: {c.kind}")

    @staticmethod
    def _eval_range(entity: Any, params: dict[str, Any]) -> list[str]:
        field = _require(params, "field", "range")
        lo = _require(params, "min", "range")
        hi = _require(params, "max", "range")
        val = _get(entity, field)
        if val is None:
            return [f"range: field '{field}' is missing"]
        if not (lo <= val <= hi):
            return [f"range: '{field}'={val} outside [{lo}, {hi}]"]
        return []

    @staticmethod
    def _eval_sum(entity: Any, params: dict[str, Any]) -> list[str]:
        fields = _require(params, "fields", "sum_of_fields")
        lo = params.get("min")
        hi = params.get("max")
        values = [_get(entity, f) for f in fields]
        if any(v is None for v in values):
            missing = [f for f, v in zip(fields, values) if v is None]
            return [f"sum_of_fields: missing field(s) {missing}"]
        total = sum(values)
        if lo is not None and total < lo:
            return [f"sum_of_fields: sum({fields})={total} below min {lo}"]
        if hi is not None and total > hi:
            return [f"sum_of_fields: sum({fields})={total} above max {hi}"]
        return []

    @staticmethod
    def _eval_forbidden_combo(entity: Any, params: dict[str, Any]) -> list[str]:
        field = _require(params, "field", "forbidden_combo")
        tags = _require(params, "tags", "forbidden_combo")
        present = set(_get(entity, field) or [])
        if all(t in present for t in tags):
            return [f"forbidden_combo: '{field}' contains all of {tags}"]
        return []

    @staticmethod
    def _eval_required_tag(entity: Any, params: dict[str, Any]) -> list[str]:
        field = _require(params, "field", "required_tag")
        any_of = _require(params, "any_of", "required_tag")
        present = set(_get(entity, field) or [])
        if not present.intersection(any_of):
            return [f"required_tag: '{field}' has none of {any_of}"]
        return []

    # -- set-level evaluation ---------------------------------------------

    @staticmethod
    def _eval_unique(
        entities: list[Any], c: Constraint
    ) -> list[tuple[int, str]]:
        field = _require(c.params, "field", "unique_across_set")
        seen: dict[Any, list[int]] = {}
        for i, entity in enumerate(entities):
            val = _get(entity, field)
            key = tuple(val) if isinstance(val, list) else val
            seen.setdefault(key, []).append(i)

        out: list[tuple[int, str]] = []
        for key, idxs in seen.items():
            if len(idxs) > 1:
                for i in idxs:
                    out.append(
                        (i, f"unique_across_set: '{field}'={key!r} repeated at indices {idxs}")
                    )
        return out
