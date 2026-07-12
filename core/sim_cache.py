"""Incremental simulation cache + runner.

Simulation is the expensive, LLM-free part; caching it per matchup means an edit to one
entity only re-runs the matchups that entity is in. Each cache entry records the seq it was
computed at, so the UI can flag freshness (fresh / stale) against the scenario head.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from core.cache_backend import CacheBackend
from core.metrics.aggregators import aggregate_metrics
from core.report_engine import hash_json
from core.scenario import Event, EventLog
from core.simulator_interface import Environment, RunResult, SimulatorInterface

Kind = Literal["quick", "full"]
_SIM_PREFIX = "sim:"
_IDX_PREFIX = "idx:"


class SimCacheEntry(BaseModel):
    config_hash: str
    entities_involved: list[str]
    kind: Kind
    computed_at_seq: int
    runs: list[RunResult]  # all matches for this matchup (plural — a matchup yields many)


class SimCache:
    """Stores per-matchup results and a reverse index for entity-level invalidation.

    ``key_prefix`` namespaces keys so a *shared* backend (Redis in prod) isolates scenarios;
    with a per-scenario disk dir it's simply harmless.
    """

    def __init__(self, backend: CacheBackend, key_prefix: str = ""):
        self.backend = backend
        self._prefix = f"{key_prefix}:" if key_prefix else ""

    def _sim_key(self, config_hash: str) -> str:
        return f"{self._prefix}{_SIM_PREFIX}{config_hash}"

    def _idx_key(self, entity_id: str) -> str:
        return f"{self._prefix}{_IDX_PREFIX}{entity_id}"

    def get(self, config_hash: str) -> SimCacheEntry | None:
        raw = self.backend.get(self._sim_key(config_hash))
        return SimCacheEntry.model_validate_json(raw) if raw is not None else None

    def put(self, entry: SimCacheEntry) -> None:
        self.backend.set(self._sim_key(entry.config_hash), entry.model_dump_json().encode())
        for entity_id in entry.entities_involved:
            self._index_add(entity_id, entry.config_hash)

    def invalidate_touching(self, entity_ids: set[str]) -> int:
        """Delete every cache entry involving any of ``entity_ids``. Returns count removed."""
        removed = 0
        for entity_id in entity_ids:
            for config_hash in self._index_get(entity_id):
                self.backend.delete(self._sim_key(config_hash))
                removed += 1
            self.backend.delete(self._idx_key(entity_id))
        return removed

    @staticmethod
    def is_stale(entry: SimCacheEntry, head_seq: int) -> bool:
        return head_seq > entry.computed_at_seq

    @staticmethod
    def freshness(entry: SimCacheEntry, head_seq: int) -> str:
        if head_seq > entry.computed_at_seq:
            return "stale"
        return "full" if entry.kind == "full" else "quick"

    # -- index -------------------------------------------------------------

    def _index_get(self, entity_id: str) -> list[str]:
        raw = self.backend.get(self._idx_key(entity_id))
        return json.loads(raw) if raw is not None else []

    def _index_add(self, entity_id: str, config_hash: str) -> None:
        current = self._index_get(entity_id)
        if config_hash not in current:
            current.append(config_hash)
            self.backend.set(self._idx_key(entity_id), json.dumps(current).encode())


class SimRunReport(BaseModel):
    n_runs: int
    matchups_reused: int
    matchups_computed: int
    metrics: dict[str, Any] = Field(default_factory=dict)


class IncrementalSimRunner:
    """Runs a batch simulation, reusing cached matchups and computing only the misses."""

    def __init__(self, simulator: SimulatorInterface, cache: SimCache, event_log: EventLog):
        self.simulator = simulator
        self.cache = cache
        self.events = event_log

    def run(
        self,
        scenario_id: str,
        entities: list[BaseModel],
        env: Environment,
        n_runs: int,
        kind: Kind = "full",
        branch: str = "main",
    ) -> SimRunReport:
        # Freshness tracks entity changes only — simulate/judge/note events don't stale a cache.
        content_seq = self._content_seq(scenario_id, branch)
        matchups = self.simulator.matchups(entities)
        per = max(1, round(n_runs / len(matchups))) if matchups else 0

        all_runs: list[RunResult] = []
        reused = computed = 0
        for matchup in matchups:
            config_hash = self._config_hash(matchup, env, per, kind)
            entry = self.cache.get(config_hash)
            if entry is not None and not SimCache.is_stale(entry, content_seq):
                all_runs.extend(entry.runs)
                reused += 1
            else:
                runs = self.simulator.run_batch(matchup, env, per)
                self.cache.put(
                    SimCacheEntry(
                        config_hash=config_hash,
                        entities_involved=self._names(matchup),
                        kind=kind,
                        computed_at_seq=content_seq,
                        runs=runs,
                    )
                )
                all_runs.extend(runs)
                computed += 1

        metrics = {
            k: v.model_dump()
            for k, v in aggregate_metrics(self.simulator.default_metrics(), all_runs).items()
        }
        self.events.append_many(
            scenario_id,
            [
                Event(
                    branch_id=branch,
                    actor="user",
                    kind="simulate",
                    target="scenario",
                    after={"n_runs": len(all_runs), "kind": kind, "metrics": metrics},
                    metadata={"matchups_reused": reused, "matchups_computed": computed},
                )
            ],
        )
        return SimRunReport(
            n_runs=len(all_runs),
            matchups_reused=reused,
            matchups_computed=computed,
            metrics=metrics,
        )

    def _content_seq(self, scenario_id: str, branch: str) -> int:
        """Highest seq among entity-changing events (create/edit/delete) — the freshness clock."""
        entity_kinds = {"create_entity", "edit_entity", "delete_entity"}
        seqs = [
            e.seq for e in self.events.read(scenario_id, branch_id=branch) if e.kind in entity_kinds
        ]
        return max(seqs, default=0)

    @staticmethod
    def _names(matchup: list[BaseModel]) -> list[str]:
        return [m.model_dump().get("name", str(i)) for i, m in enumerate(matchup)]

    @staticmethod
    def _config_hash(matchup: list[BaseModel], env: Environment, per: int, kind: str) -> str:
        return hash_json(
            {
                "entities": sorted(json.dumps(m.model_dump(), sort_keys=True) for m in matchup),
                "env": env.model_dump(),
                "per": per,
                "kind": kind,
            }
        )
