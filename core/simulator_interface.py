"""The contract every domain simulator implements.

The core loads a simulator *by name* and drives it through this ABC — it never imports
a concrete domain. A simulator is pure: :meth:`SimulatorInterface.run` must be
deterministic given the environment seed, with no I/O and no LLM calls inside the runner.

To avoid a runtime import cycle (metrics reference :class:`RunResult`; a simulator
references ``Metric``), the cross-module names are imported only under ``TYPE_CHECKING``
and resolved lazily via string annotations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

from core.entity_schema import EntitySchema

if TYPE_CHECKING:
    from core.metrics.base import Metric


class Environment(BaseModel):
    """Base simulation environment. Each domain subclasses this to add its own knobs.

    The only guaranteed field is ``seed`` — the core relies on it for reproducibility
    and cache keying. Subclasses add domain-specific parameters (e.g. ``turn_limit``).
    """

    model_config = ConfigDict(extra="forbid")

    seed: int


class RunResult(BaseModel):
    """Structured outcome of one simulation run.

    ``outcome`` is domain-specific but must be JSON-serialisable so metrics, the report
    engine, and the cache can treat it generically. ``entities_involved`` holds the ids
    of participating entities so ratings/metrics can attribute results without knowing
    the domain.
    """

    model_config = ConfigDict(extra="forbid")

    entities_involved: list[str]
    outcome: dict[str, Any]
    duration_steps: int
    seed: int


class SimulatorInterface(ABC):
    """Contract implemented by every domain plugin's simulator.

    Concrete implementations live in ``domains/<name>/simulator.py`` and are the only
    place domain rules exist. The core consumes this interface, never the concrete type.
    """

    @abstractmethod
    def entity_schema(self) -> EntitySchema:
        """Return the :class:`~core.entity_schema.EntitySchema` describing this domain's
        entity (e.g. a card ``Unit`` or an RPG ``Creature``).

        Used by the API to expose the schema, by the UI to render an editor, and by the
        LLM generator to build the ``tool_use`` input schema.
        """

    @abstractmethod
    def environment_schema(self) -> type[Environment]:
        """Return the concrete :class:`Environment` subclass this simulator accepts.

        The API validates incoming ``env`` payloads against this type before calling
        :meth:`run`. Returning the class (not an instance) lets the core introspect and
        construct environments generically.
        """

    @abstractmethod
    def run(self, entities: list[BaseModel], env: Environment) -> RunResult:
        """Execute one deterministic simulation run and return its :class:`RunResult`.

        Must be pure and reproducible: identical ``entities`` and ``env`` (same seed)
        must yield an identical result. No I/O, no network, no LLM calls — the core
        parallelises and caches runs on the assumption of purity.
        """

    def run_batch(
        self, entities: list[BaseModel], env: Environment, n_runs: int
    ) -> list[RunResult]:
        """Run ``n_runs`` matches over an entity *set* and return every RunResult.

        This is the seam the iteration engine and sim cache use: given a pool of entities,
        the domain decides matchmaking (card game: round-robin of solo decks; creature RPG:
        gauntlet). The default treats the whole list as one matchup repeated with varied
        seeds — domains with set-level structure override it.
        """
        return [
            self.run(entities, env.model_copy(update={"seed": env.seed + i}))
            for i in range(n_runs)
        ]

    @abstractmethod
    def default_metrics(self) -> list[Metric]:
        """Return the metrics this domain computes by default over a batch of runs.

        These are domain-agnostic :class:`~core.metrics.base.Metric` instances (possibly
        including domain-specific ones); the report engine calls ``compute`` on each.
        """

    @abstractmethod
    def llm_generation_prompt(self, constraints: list[Any]) -> str:
        """Return a domain-specific prompt fragment appended to the base generator prompt.

        Describes what a good entity looks like in this domain and how to honour the given
        constraints, guiding the LLM before it calls the ``tool_use`` emit tool.
        """
