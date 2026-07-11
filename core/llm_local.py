"""Local LLM hats — Designer/Judge/Iterator backed by an OpenAI-compatible server.

Targets a llama-server (e.g. Qwen2.5-Coder-7B) at ``LOCAL_LLM_URL``. Small models are
unreliable with raw ``tools`` calling, so we force JSON via ``response_format`` and validate
the output against the domain schema ourselves, retrying with error feedback. No API key or
rate limiting — the server is local and free.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from core.constraint_engine import Constraint, ConstraintEngine
from core.entity_schema import EntitySchema
from core.llm_hats import JudgeResult, Modification
from core.objectives import Objective

logger = logging.getLogger(__name__)

_TIMEOUT = 180  # Iterator prompts can be long; local server has no 429 to back off from
_MAX_RETRIES = 3
_PROMPTS_DIR = Path(__file__).with_name("prompts")


def _get_client() -> Any:
    """Return an OpenAI client pointed at the local server. Raises if URL is unset."""
    import openai

    url = os.getenv("LOCAL_LLM_URL")
    if not url:
        raise RuntimeError("LOCAL_LLM_URL is not set (required for LLM_BACKEND=local)")
    return openai.OpenAI(base_url=url, api_key="local", timeout=_TIMEOUT)


def _model() -> str:
    return os.getenv("LOCAL_LLM_MODEL", "local")


class _LocalBase:
    def __init__(self, client: Any | None = None, model: str | None = None):
        self._client = client
        self.model = model or _model()

    @property
    def client(self) -> Any:
        if self._client is None:
            self._client = _get_client()
        return self._client

    def _chat_json(self, system: str, user: str, temperature: float) -> dict[str, Any]:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_format={"type": "json_object"},
            temperature=temperature,
        )
        return _parse_json(response.choices[0].message.content or "")


def _constraints_text(constraints: list[Constraint]) -> str:
    if not constraints:
        return "(none)"
    return json.dumps([c.model_dump() for c in constraints], indent=1)


class LocalDesigner(_LocalBase):
    """Materialise entities from a brief, validating each against the schema (retry on failure)."""

    def design(
        self,
        brief: str,
        schema: EntitySchema,
        constraints: list[Constraint],
        n: int,
        stats: dict[str, int] | None = None,
    ) -> list[BaseModel]:
        """Design ``n`` entities. If ``stats`` is given, records raw ``emitted``/``valid`` counts."""
        constraints = constraints or []
        model_cls = schema.build_model()
        engine = ConstraintEngine()
        field_schema = schema.to_llm_schema()["input_schema"]
        system = (
            "You design entities for a game-balance simulator. Return ONLY a JSON object of the "
            'form {"entities": [ ... ]} where each entity matches the given field schema exactly. '
            "Respect every field's type and range. Do not add commentary."
        )
        collected: list[BaseModel] = []
        errors: list[str] = []

        for attempt in range(_MAX_RETRIES + 1):
            if len(collected) >= n:
                break
            user = (
                f"Brief: {brief}\n\nField schema (JSON Schema for one entity):\n"
                f"{json.dumps(field_schema, indent=1)}\n\n"
                f"Constraints:\n{_constraints_text(constraints)}\n\n"
                f"Produce {n - len(collected)} distinct valid entities."
            )
            if errors:
                user += "\n\nThe previous attempt was invalid. Fix these and do not repeat:\n" + "\n".join(
                    f"- {e}" for e in errors
                )
            errors = []
            try:
                payload = self._chat_json(system, user, temperature=0.7)
            except (json.JSONDecodeError, ValueError) as exc:
                errors.append(f"response was not valid JSON: {exc}")
                logger.info("designer attempt %d: bad JSON", attempt + 1)
                continue

            raw_entities = _extract_list(payload, "entities")
            if stats is not None:
                stats["emitted"] = stats.get("emitted", 0) + len(raw_entities)
            for raw in raw_entities:
                entity = self._validate(model_cls, engine, raw, constraints, errors)
                if entity is not None:
                    collected.append(entity)
                    if stats is not None:
                        stats["valid"] = stats.get("valid", 0) + 1

        if len(collected) < n:
            logger.warning("LocalDesigner returned %d of %d requested", len(collected), n)
        return collected[:n]

    @staticmethod
    def _validate(model_cls, engine, raw, constraints, errors) -> BaseModel | None:
        if not isinstance(raw, dict):
            errors.append(f"entity must be an object, got {type(raw).__name__}")
            return None
        try:
            entity = model_cls(**raw)
        except ValidationError as exc:
            errors.append(f"{raw} -> schema error: {exc.errors(include_url=False)}")
            return None
        result = engine.validate(entity, constraints)
        if not result.is_valid:
            errors.append(f"{raw} -> constraint violations: {result.violations}")
            logger.info("dropping constraint-violating entity: %s", result.violations)
            return None
        return entity


class LocalJudge(_LocalBase):
    """Score a set of entities against a subjective criterion (variety/cohesion/thematic)."""

    def judge(self, entities: list[BaseModel], criterion: str) -> JudgeResult:
        system = _load_judge_prompt(criterion)
        user = (
            "Entities:\n"
            + json.dumps([e.model_dump() for e in entities], indent=1)
            + '\n\nRespond ONLY as JSON: {"score": <0.0-1.0>, "rationale": "<one sentence>"}'
        )
        payload = self._chat_json(system, user, temperature=0.3)
        score = float(payload.get("score", 0.0))
        score = max(0.0, min(1.0, score))  # clamp defensively
        return JudgeResult(score=score, rationale=str(payload.get("rationale", "")))


class LocalIterator(_LocalBase):
    """Propose create/edit/delete modifications; never touch user-owned entities."""

    def propose_changes(
        self,
        entities: list[BaseModel],
        sim_metrics: dict[str, Any],
        judge_metrics: dict[str, Any],
        objectives: list[Objective],
        user_owned: set[str] | None = None,
    ) -> list[Modification]:
        user_owned = user_owned or set()
        system = (
            "You tune game entities toward the given objectives. Propose minimal changes. "
            'Return ONLY JSON: {"modifications": [{"kind": "create|edit|delete", "target": '
            '<entity id or null>, "payload": {<entity fields>}, "reasoning": "<why>"}]}. '
            "Never modify an entity listed as user-owned."
        )
        user = (
            "Current entities:\n"
            + json.dumps([e.model_dump() for e in entities], indent=1)
            + f"\n\nSimulation metrics:\n{json.dumps(sim_metrics, indent=1)}"
            + f"\n\nJudge metrics:\n{json.dumps(judge_metrics, indent=1)}"
            + f"\n\nObjectives:\n{json.dumps([o.model_dump() for o in objectives], indent=1)}"
            + f"\n\nUser-owned entities (do NOT modify): {sorted(user_owned)}"
        )
        payload = self._chat_json(system, user, temperature=0.4)

        mods: list[Modification] = []
        for raw in _extract_list(payload, "modifications"):
            if not isinstance(raw, dict):
                continue
            try:
                mod = Modification(**raw)
            except ValidationError as exc:
                logger.info("dropping malformed modification: %s", exc.errors(include_url=False))
                continue
            if mod.target is not None and mod.target in user_owned:
                logger.info("dropping modification on user-owned entity: %s", mod.target)
                continue
            mods.append(mod)
        return mods


def _parse_json(content: str) -> Any:
    """Parse model output into JSON, tolerating markdown fences and surrounding prose.

    Small models often wrap JSON in ```json fences or add commentary despite response_format.
    """
    text = content.strip()
    if not text:
        return {}
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"[\{\[].*[\}\]]", text, re.DOTALL)  # first JSON-looking block
        if match:
            return json.loads(match.group(0))
        raise


def _extract_list(payload: dict[str, Any], key: str) -> list[Any]:
    """Pull a list from ``payload[key]``; tolerate a bare list or a single object."""
    if isinstance(payload, list):
        return payload
    value = payload.get(key)
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    return []


def _load_judge_prompt(criterion: str) -> str:
    path = _PROMPTS_DIR / f"judge_{criterion}.txt"
    if path.exists():
        return path.read_text().strip()
    return (
        f"You are a game-design critic. Judge the '{criterion}' of the entity set on a 0.0-1.0 "
        "scale, where 1.0 is excellent. Be discriminating."
    )
