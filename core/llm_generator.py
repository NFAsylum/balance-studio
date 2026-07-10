"""LLM candidate generator.

Given an :class:`~core.entity_schema.EntitySchema`, ask Claude to emit a batch of entities
via a forced ``tool_use`` call, validate each against the schema, drop the ones that violate
constraints, and retry (feeding the errors back into the prompt) until enough valid entities
accumulate or the retry budget is exhausted.

The LLM is a *candidate source*, not part of the critical loop — the framework runs fine
with hand-authored entities, so generation failures degrade to "fewer entities returned",
never a crash.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from pydantic import BaseModel, ValidationError

from core.constraint_engine import Constraint, ConstraintEngine
from core.entity_schema import EntitySchema

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-4-6")
_MAX_RETRIES = 3
_MAX_TOKENS = 4096


class LlmGenerator:
    """Generates schema-valid, constraint-satisfying entities via Claude ``tool_use``."""

    def __init__(self, client: Any, schema: EntitySchema, model: str | None = None):
        self.client = client  # an anthropic.Anthropic-like client
        self.schema = schema
        self.model = model or _DEFAULT_MODEL
        self._engine = ConstraintEngine()

    def generate(
        self,
        n: int,
        constraints: list[Constraint] | None = None,
        seed_examples: list[BaseModel] | None = None,
        user_intent: str = "",
        domain_prompt: str = "",
    ) -> list[BaseModel]:
        """Return up to ``n`` validated entities satisfying ``constraints``.

        Retries up to ``_MAX_RETRIES`` times; each retry appends the previous batch's
        validation/constraint errors to the prompt so the model can correct itself.
        """
        constraints = constraints or []
        model_cls = self.schema.build_model()
        collected: list[BaseModel] = []
        errors_feedback: list[str] = []

        for attempt in range(_MAX_RETRIES + 1):
            if len(collected) >= n:
                break
            need = n - len(collected)
            raw_entities = self._call_llm(need, constraints, user_intent, domain_prompt, errors_feedback)
            errors_feedback = []

            for raw in raw_entities:
                entity = self._validate_one(model_cls, raw, constraints, errors_feedback)
                if entity is not None:
                    collected.append(entity)

            if errors_feedback:
                logger.info(
                    "generate attempt %d: %d/%d valid so far, %d rejected",
                    attempt + 1,
                    len(collected),
                    n,
                    len(errors_feedback),
                )

        if len(collected) < n:
            logger.warning("generate returned %d of %d requested entities", len(collected), n)
        return collected[:n]

    # -- validation --------------------------------------------------------

    def _validate_one(
        self,
        model_cls: type[BaseModel],
        raw: dict[str, Any],
        constraints: list[Constraint],
        errors_feedback: list[str],
    ) -> BaseModel | None:
        """Validate one raw entity against schema then constraints; log+record rejects."""
        try:
            entity = model_cls(**raw)
        except ValidationError as exc:
            msg = f"{raw} -> schema error: {exc.errors(include_url=False)}"
            logger.info("dropping schema-invalid entity: %s", msg)
            errors_feedback.append(msg)
            return None

        result = self._engine.validate(entity, constraints)
        if not result.is_valid:
            msg = f"{raw} -> constraint violations: {result.violations}"
            logger.info("dropping constraint-violating entity: %s", msg)
            errors_feedback.append(msg)
            return None
        return entity

    # -- LLM call ----------------------------------------------------------

    def _call_llm(
        self,
        n: int,
        constraints: list[Constraint],
        user_intent: str,
        domain_prompt: str,
        errors_feedback: list[str],
    ) -> list[dict[str, Any]]:
        tool = self._batch_tool(n)
        system = self._build_system_prompt(domain_prompt)
        prompt = self._build_user_prompt(n, constraints, user_intent, errors_feedback)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=_MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            tools=[tool],
            tool_choice={"type": "tool", "name": tool["name"]},
        )
        return self._extract_entities(response)

    @staticmethod
    def _extract_entities(response: Any) -> list[dict[str, Any]]:
        """Pull the ``entities`` list out of the forced tool_use block."""
        for block in response.content:
            if getattr(block, "type", None) == "tool_use":
                # block.input is already a parsed dict per the Anthropic SDK.
                return list(block.input.get("entities", []))
        logger.warning("no tool_use block in LLM response; returning no entities")
        return []

    def _batch_tool(self, n: int) -> dict[str, Any]:
        entity_schema = self.schema.to_llm_schema()["input_schema"]
        return {
            "name": f"emit_{self.schema.name.lower()}_batch",
            "description": f"Emit exactly {n} valid {self.schema.name} entities.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "entities": {"type": "array", "items": entity_schema},
                },
                "required": ["entities"],
                "additionalProperties": False,
            },
        }

    @staticmethod
    def _build_system_prompt(domain_prompt: str) -> str:
        base = (
            "You are a game-balance designer generating candidate entities for a simulation. "
            "Always call the provided tool with a well-formed batch. Respect every field's "
            "type and range, and honour all stated constraints."
        )
        return f"{base}\n\n{domain_prompt}".strip() if domain_prompt else base

    def _build_user_prompt(
        self,
        n: int,
        constraints: list[Constraint],
        user_intent: str,
        errors_feedback: list[str],
    ) -> str:
        parts = [f"Generate {n} distinct {self.schema.name} entities."]
        if user_intent:
            parts.append(f"Design intent: {user_intent}")
        if constraints:
            constraint_json = json.dumps([c.model_dump() for c in constraints], indent=2)
            parts.append(f"They must satisfy these constraints:\n{constraint_json}")
        if errors_feedback:
            joined = "\n".join(f"- {e}" for e in errors_feedback)
            parts.append(
                "The previous attempt produced invalid entities. Fix these problems and "
                f"do not repeat them:\n{joined}"
            )
        return "\n\n".join(parts)
