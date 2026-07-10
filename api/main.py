"""FastAPI app exposing domain-agnostic balance endpoints.

Routing is by domain ``{name}``; the handlers never branch on which domain it is — they
call the plugin's :class:`~core.simulator_interface.SimulatorInterface`. Adding a domain
adds routes for free via the registry.
"""

from __future__ import annotations

import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ValidationError

from api.registry import registry
from core.branching import Branch, DiffReport
from core.constraint_engine import Constraint
from core.iteration_engine import IterationEngine, StepResult
from core.llm_fakes import FakeDesigner, FakeIterator, FakeJudge
from core.objectives import Objective
from core.report_engine import Report, build_report, hash_json
from core.scenario import Event, EventLog, Scenario
from core.snapshot import Replay, SnapshotStore

logger = logging.getLogger(__name__)


class _Services:
    """Shared, startup-initialised services (Fake LLMs — no API key touched)."""

    event_log: EventLog
    replay: Replay
    branch: Branch
    engine: IterationEngine


services = _Services()


@asynccontextmanager
async def lifespan(app: FastAPI):
    registry.load()
    base_dir = os.getenv("SCENARIOS_DIR", "scenarios")
    services.event_log = EventLog(base_dir=base_dir)
    services.replay = Replay(services.event_log, SnapshotStore(base_dir=base_dir))
    services.branch = Branch(services.event_log, services.replay)
    services.engine = IterationEngine(
        services.event_log,
        services.replay,
        registry.all(),
        FakeDesigner(),
        FakeJudge(),
        FakeIterator(),
    )
    logger.info("domains loaded: %s", registry.names())
    yield


app = FastAPI(title="Balance Studio", lifespan=lifespan)


class SimulateRequest(BaseModel):
    entities: list[Any]
    env: dict[str, Any]
    n_runs: int = Field(default=1, ge=1, le=100_000)
    metrics: list[str] | None = None


class GenerateRequest(BaseModel):
    n: int = Field(ge=1, le=100)
    constraints: list[dict[str, Any]] = Field(default_factory=list)
    user_intent: str = ""


def _require_domain(name: str):
    simulator = registry.get(name)
    if simulator is None:
        raise HTTPException(status_code=404, detail=f"domain '{name}' not found")
    return simulator


@app.get("/domains")
def list_domains() -> dict[str, list[str]]:
    return {"domains": registry.names()}


@app.get("/domains/{name}/schema")
def get_schema(name: str) -> dict[str, Any]:
    simulator = _require_domain(name)
    return simulator.entity_schema().model_dump()


@app.post("/domains/{name}/simulate", response_model=Report)
def simulate(name: str, request: SimulateRequest) -> Report:
    simulator = _require_domain(name)
    env_cls = simulator.environment_schema()

    try:
        base_env = env_cls(**request.env)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors(include_url=False)) from exc

    metrics = simulator.default_metrics()
    if request.metrics is not None:
        wanted = set(request.metrics)
        metrics = [m for m in metrics if m.name in wanted]

    runs = []
    env_fields = base_env.model_dump()
    for i in range(request.n_runs):
        # Vary the seed per run so a batch produces a distribution, not one repeated match.
        env_i = env_cls(**{**env_fields, "seed": base_env.seed + i})
        try:
            runs.append(simulator.run(request.entities, env_i))
        except (ValueError, TypeError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return build_report(
        domain=name,
        runs=runs,
        metrics=metrics,
        entity_set_hash=hash_json(request.entities),
        env_hash=hash_json(request.env),
    )


@app.post("/domains/{name}/generate")
def generate(name: str, request: GenerateRequest) -> dict[str, Any]:
    """Design candidate entities via the Designer hat.

    Uses the deterministic ``FakeDesigner`` in dev; Sprint 6 swaps in ``AnthropicDesigner``
    behind an ``LLM_BACKEND`` switch (no API key needed until then).
    """
    simulator = _require_domain(name)
    constraints = [Constraint(**c) for c in request.constraints]
    designer = FakeDesigner()
    entities = designer.design(
        brief=request.user_intent,
        schema=simulator.entity_schema(),
        constraints=constraints,
        n=request.n,
    )
    return {"entities": [e.model_dump() for e in entities], "requested": request.n}


# ---------------------------------------------------------------------------
# Scenario workflow (fluid human/LLM collaboration over the event log; Fakes only)
# ---------------------------------------------------------------------------


class CreateScenarioRequest(BaseModel):
    domain: str
    name: str = "Untitled scenario"
    brief: str = ""
    n_entities: int = Field(default=8, ge=1, le=200)


class IterateRequest(BaseModel):
    phase: Literal["design", "iterate", "simulate", "judge"]


class EntityRequest(BaseModel):
    entity: dict[str, Any]


class ObjectivesRequest(BaseModel):
    objectives: list[Objective]


class CreateBranchRequest(BaseModel):
    parent_seq: int = Field(ge=0)
    name: str


def _load_scenario(scenario_id: str) -> Scenario:
    try:
        return services.event_log.scenario(scenario_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"scenario '{scenario_id}' not found") from exc


def _validate_entity(domain: str, data: dict[str, Any]) -> dict[str, Any]:
    simulator = _require_domain(domain)
    model = simulator.entity_schema().build_model()
    try:
        return model(**data).model_dump()
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors(include_url=False)) from exc


@app.post("/scenarios")
def create_scenario(request: CreateScenarioRequest) -> Scenario:
    _require_domain(request.domain)  # 404 if the domain isn't registered
    scenario = Scenario(
        id=uuid.uuid4().hex[:12],
        domain=request.domain,
        name=request.name,
        brief=request.brief,
        n_entities=request.n_entities,
    )
    services.event_log.init_scenario(scenario)
    return scenario


@app.get("/scenarios/{scenario_id}")
def get_scenario(scenario_id: str) -> dict[str, Any]:
    scenario = _load_scenario(scenario_id)
    branch = scenario.current_branch
    head = services.event_log.head(scenario_id, branch)
    state = services.replay.rebuild_state(scenario_id, head, branch)
    return {"scenario": scenario.model_dump(), "entities": state.entities, "head_seq": head}


@app.post("/scenarios/{scenario_id}/iterate", response_model=StepResult)
def iterate(scenario_id: str, request: IterateRequest) -> StepResult:
    _load_scenario(scenario_id)
    return services.engine.step(scenario_id, request.phase)


@app.post("/scenarios/{scenario_id}/entities")
def add_entity(scenario_id: str, request: EntityRequest) -> dict[str, Any]:
    scenario = _load_scenario(scenario_id)
    data = _validate_entity(scenario.domain, request.entity)
    target = str(data["name"])
    event = Event(
        branch_id=scenario.current_branch,
        actor="user",
        kind="create_entity",
        target=target,
        after=data,
    )
    return services.event_log.append(scenario_id, event).model_dump(mode="json")


@app.patch("/scenarios/{scenario_id}/entities/{entity_id}")
def edit_entity(scenario_id: str, entity_id: str, request: EntityRequest) -> dict[str, Any]:
    scenario = _load_scenario(scenario_id)
    branch = scenario.current_branch
    state = services.replay.rebuild_state(scenario_id, services.event_log.head(scenario_id, branch), branch)
    if entity_id not in state.entities:
        raise HTTPException(status_code=404, detail=f"entity '{entity_id}' not found")
    data = _validate_entity(scenario.domain, request.entity)
    event = Event(
        branch_id=branch,
        actor="user",
        kind="edit_entity",
        target=entity_id,
        before=state.entities[entity_id],
        after=data,
    )
    return services.event_log.append(scenario_id, event).model_dump(mode="json")


@app.delete("/scenarios/{scenario_id}/entities/{entity_id}")
def delete_entity(scenario_id: str, entity_id: str) -> dict[str, Any]:
    scenario = _load_scenario(scenario_id)
    branch = scenario.current_branch
    state = services.replay.rebuild_state(scenario_id, services.event_log.head(scenario_id, branch), branch)
    if entity_id not in state.entities:
        raise HTTPException(status_code=404, detail=f"entity '{entity_id}' not found")
    event = Event(
        branch_id=branch,
        actor="user",
        kind="delete_entity",
        target=entity_id,
        before=state.entities[entity_id],
    )
    return services.event_log.append(scenario_id, event).model_dump(mode="json")


@app.post("/scenarios/{scenario_id}/objectives")
def set_objectives(scenario_id: str, request: ObjectivesRequest) -> dict[str, Any]:
    _load_scenario(scenario_id)
    Objective.set_via_event(services.event_log, scenario_id, request.objectives)
    return {"objectives": [o.model_dump() for o in request.objectives]}


@app.get("/scenarios/{scenario_id}/history")
def get_history(scenario_id: str) -> dict[str, Any]:
    scenario = _load_scenario(scenario_id)
    events = services.event_log.read(scenario_id, branch_id=scenario.current_branch)
    return {"events": [e.model_dump(mode="json") for e in events]}


@app.post("/scenarios/{scenario_id}/branches")
def create_branch(scenario_id: str, request: CreateBranchRequest) -> dict[str, Any]:
    _load_scenario(scenario_id)
    try:
        branch_id = services.branch.create(scenario_id, request.parent_seq, request.name)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"branch_id": branch_id}


@app.get("/scenarios/{scenario_id}/branches/{branch_a}/diff/{branch_b}", response_model=DiffReport)
def diff_branches(scenario_id: str, branch_a: str, branch_b: str) -> DiffReport:
    _load_scenario(scenario_id)
    known = services.event_log.branch_ids(scenario_id)
    for branch in (branch_a, branch_b):
        if branch not in known:
            raise HTTPException(status_code=404, detail=f"branch '{branch}' not found")
    return services.branch.diff(scenario_id, branch_a, branch_b)
