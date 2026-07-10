"""Declarative entity schema DSL.

A domain describes its entities as a dict of field specs. The core turns that
into (a) a dynamic Pydantic model for validation and (b) an Anthropic ``tool_use``
input schema so the LLM can emit entities the model will accept. The core never
hardcodes any domain's fields — everything flows from the declared ``EntitySchema``.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, create_model, model_validator

FieldKind = Literal["num", "cat", "bool", "tag_set"]


class FieldSpec(BaseModel):
    """One field of an entity.

    ``num`` uses ``range`` (inclusive min/max); ``cat`` uses ``enum``; ``bool`` and
    ``tag_set`` use neither. ``tag_set`` is an unordered list of free-form string tags.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    kind: FieldKind
    range: tuple[float, float] | None = None  # num only
    enum: list[str] | None = None  # cat only
    description: str = ""

    @model_validator(mode="after")
    def _validate_kind_params(self) -> FieldSpec:
        if self.kind == "num":
            if self.enum is not None:
                raise ValueError(f"field '{self.name}': 'enum' is only valid for kind 'cat'")
            if self.range is not None:
                lo, hi = self.range
                if lo > hi:
                    raise ValueError(
                        f"field '{self.name}': range min {lo} is greater than max {hi}"
                    )
        elif self.kind == "cat":
            if self.range is not None:
                raise ValueError(f"field '{self.name}': 'range' is only valid for kind 'num'")
            if not self.enum:
                raise ValueError(f"field '{self.name}': kind 'cat' requires a non-empty 'enum'")
            if len(set(self.enum)) != len(self.enum):
                raise ValueError(f"field '{self.name}': 'enum' has duplicate values")
        else:  # bool, tag_set
            if self.range is not None:
                raise ValueError(f"field '{self.name}': 'range' is only valid for kind 'num'")
            if self.enum is not None:
                raise ValueError(f"field '{self.name}': 'enum' is only valid for kind 'cat'")
        return self


class EntitySchema(BaseModel):
    """A named collection of :class:`FieldSpec`, buildable into a Pydantic model."""

    model_config = ConfigDict(extra="forbid")

    name: str
    fields: list[FieldSpec]

    @model_validator(mode="after")
    def _validate_unique_names(self) -> EntitySchema:
        names = [f.name for f in self.fields]
        if len(set(names)) != len(names):
            raise ValueError("field names must be unique within an EntitySchema")
        if not names:
            raise ValueError("EntitySchema must declare at least one field")
        return self

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EntitySchema:
        """Parse a plain dict (e.g. loaded from JSON) into an EntitySchema."""
        return cls.model_validate(data)

    def build_model(self) -> type[BaseModel]:
        """Return a dynamically generated Pydantic model that validates entities.

        Extra fields are forbidden so LLM hallucinations surface as validation errors.
        """
        field_defs: dict[str, Any] = {}
        for spec in self.fields:
            annotation, field_info = self._field_definition(spec)
            field_defs[spec.name] = (annotation, field_info)
        return create_model(
            self.name,
            __config__=ConfigDict(extra="forbid"),
            **field_defs,
        )

    def to_llm_schema(self) -> dict[str, Any]:
        """Return an Anthropic ``tool_use`` tool definition emitting one entity.

        Shape: ``{"name", "description", "input_schema"}`` where ``input_schema`` is a
        JSON Schema object. Callers pass this in the ``tools`` array of a Messages call.
        """
        properties: dict[str, Any] = {}
        for spec in self.fields:
            properties[spec.name] = self._json_schema_property(spec)
        return {
            "name": f"emit_{self.name.lower()}",
            "description": f"Return a single valid {self.name} entity.",
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": [f.name for f in self.fields],
                "additionalProperties": False,
            },
        }

    # -- internals ---------------------------------------------------------

    @staticmethod
    def _field_definition(spec: FieldSpec) -> tuple[Any, Any]:
        """Map a FieldSpec to a (type annotation, FieldInfo) pair for create_model."""
        if spec.kind == "num":
            if spec.range is not None:
                lo, hi = spec.range
                return float, Field(ge=lo, le=hi, description=spec.description)
            return float, Field(description=spec.description)
        if spec.kind == "cat":
            assert spec.enum is not None  # guaranteed by FieldSpec validation
            return Literal[tuple(spec.enum)], Field(description=spec.description)  # type: ignore[valid-type]
        if spec.kind == "bool":
            return bool, Field(description=spec.description)
        # tag_set — required list (may be empty); kept in sync with to_llm_schema 'required'
        return list[str], Field(description=spec.description)

    @staticmethod
    def _json_schema_property(spec: FieldSpec) -> dict[str, Any]:
        base: dict[str, Any] = {}
        if spec.description:
            base["description"] = spec.description
        if spec.kind == "num":
            base["type"] = "number"
            if spec.range is not None:
                base["minimum"], base["maximum"] = spec.range
        elif spec.kind == "cat":
            base["type"] = "string"
            base["enum"] = spec.enum
        elif spec.kind == "bool":
            base["type"] = "boolean"
        else:  # tag_set
            base["type"] = "array"
            base["items"] = {"type": "string"}
        return base
