# Arquitetura — Balance Studio

## Visão geral

Framework em três camadas:

1. **Core (genérico):** entity schema, constraint engine, LLM generator, simulator interface, metrics, report engine
2. **Domains (plugins):** cada domínio implementa `SimulatorInterface` + schema + metrics específicas
3. **API + UI (agnósticos):** rotas e componentes que operam sobre qualquer domínio via introspecção

Regra de ouro: **core não conhece domínios; domínios não modificam core**.

```
┌──────────────────────────────────────────────────────────┐
│                      Next.js UI                          │
│  - Domain list (fetched from API)                        │
│  - Generic entity editor (renders from schema)           │
│  - Generic results dashboard                             │
│  - Optional domain-specific views (pluginable)           │
└────────────────────────┬─────────────────────────────────┘
                         │ HTTP + JSON
                         ▼
┌──────────────────────────────────────────────────────────┐
│                      FastAPI                             │
│  POST /domains/{name}/generate  → LLM generates entities │
│  POST /domains/{name}/simulate  → run + return results   │
│  GET  /domains/{name}/schema    → entity schema (JSON)   │
│  GET  /domains/{name}/metrics   → available metrics      │
└────────────────────────┬─────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│                       CORE                               │
│  ┌────────────────┐  ┌────────────────┐                  │
│  │ entity_schema  │  │ llm_generator  │                  │
│  └────────────────┘  └────────────────┘                  │
│  ┌────────────────┐  ┌────────────────┐                  │
│  │  constraints   │  │    metrics     │                  │
│  └────────────────┘  └────────────────┘                  │
│  ┌───────────────────────────────────────┐               │
│  │        SimulatorInterface (ABC)       │◀── loaded    │
│  └───────────────────────────────────────┘   by name     │
└────────────────────────┬─────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│                    DOMAINS (plugins)                     │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────┐  │
│  │ card_game  │  │ creature_  │  │  team_composition  │  │
│  │            │  │   rpg      │  │                    │  │
│  └────────────┘  └────────────┘  └────────────────────┘  │
│  Each implements: schema, simulator, metrics             │
└──────────────────────────────────────────────────────────┘

     Postgres        ← stores experiment history, entity sets
     Redis           ← caches simulation results by hash
```

## Core

### `core/entity_schema.py`

DSL declarativa para definir entidades. Recebe dict, produz classe Pydantic dinâmica.

```python
class FieldSpec(BaseModel):
    name: str
    kind: Literal["num", "cat", "bool", "tag_set", "str"]
    range: tuple[float, float] | None = None      # for num
    enum: list[str] | None = None                 # for cat and tag_set (closed set)
    min_len: int | None = None                    # for str
    max_len: int | None = None                    # for str
    description: str = ""

class EntitySchema(BaseModel):
    name: str
    fields: list[FieldSpec]

    def build_model(self) -> type[BaseModel]:
        """Returns dynamically generated Pydantic model."""
        ...

    def to_llm_schema(self) -> dict:
        """Returns JSON schema for LLM tool_use."""
        ...
```

**Semantics of `kind`:**
- `num`: numeric (int or float). Bounded by `range`.
- `cat`: closed enum. Value must be in `enum`. Use for `ability_kind`, `seniority`, `type` etc.
- `bool`: true/false.
- `tag_set`: set of strings from a closed `enum` (multiple allowed). Use for `skills`, `resistances`, `preferred_task_types`.
- `str`: free-form string, invented by LLM or user. Optional `min_len`/`max_len`. Use for `name`, `description`. **Never use `cat` for open-ended text** — that's what `str` exists for.

### `core/constraint_engine.py`

Valida entidades contra regras declarativas.

```python
class Constraint(BaseModel):
    kind: Literal[
        "range",              # field between min and max
        "sum_of_fields",      # sum(a, b, c) between min and max
        "forbidden_combo",    # tag A + tag B on same entity
        "required_tag",       # entity must have at least one tag from set
        "unique_across_set",  # field value unique in set
    ]
    params: dict

class ConstraintEngine:
    def validate(self, entity: BaseModel, constraints: list[Constraint]) -> ValidationResult:
        ...
    def validate_set(self, entities: list[BaseModel], constraints: list[Constraint]) -> list[ValidationResult]:
        ...
```

### `core/llm_hats.py` — três protocols

O LLM entra em três papéis distintos. Cada um é um `Protocol` isolado. Cada um tem impl `Fake*` (dev) e `Anthropic*` (Sprint 6).

```python
class DesignerLlm(Protocol):
    """Materializa entidades a partir de brief em linguagem natural."""
    def design(
        self,
        brief: str,
        schema: EntitySchema,
        constraints: list[Constraint],
        n: int,
    ) -> list[BaseModel]: ...

class SubjectiveJudgeLlm(Protocol):
    """Avalia qualitativamente (variedade, coesão, temática)."""
    def judge(
        self,
        entities: list[BaseModel],
        criterion: str,  # "variety" | "cohesion" | "thematic_consistency"
    ) -> JudgeResult:  # {score: 0-1, rationale: str}
        ...

class IteratorLlm(Protocol):
    """Propõe mudanças dado estado + métricas + objetivos."""
    def propose_changes(
        self,
        entities: list[BaseModel],
        sim_metrics: dict,
        judge_metrics: dict,
        objectives: list[Objective],
    ) -> list[Modification]: ...

class Modification(BaseModel):
    kind: Literal["create", "edit", "delete"]
    target: str | None       # entity_id (None for create)
    payload: dict            # new entity (create/edit) or {} (delete)
    reasoning: str
```

**Guardrail:** `IteratorLlm` nunca propõe mudança em entidade cuja última edição foi por `actor="user"`. Respeita autoria — quando o usuário editou algo, foi decisão dele. Iterator só toca em entidades que ele mesmo ou os outros hats de LLM criaram/editaram por último.

### `core/scenario.py` — Scenario + Event log

Estado do trabalho vive como sequência de eventos append-only, não como estado mutável.

```python
class Event(BaseModel):
    seq: int                     # monotonic dentro do branch
    parent_seq: int | None       # None só no primeiro evento do branch principal
    branch_id: str               # "main" default, uuid pra branches
    timestamp: datetime
    actor: Literal["user", "llm-designer", "llm-judge", "llm-iterator"]
    kind: Literal[
        "create_entity", "edit_entity", "delete_entity",
        "simulate", "evaluate_subjective", "set_objective", "note"
    ]
    target: str                  # entity_id ou "scenario"
    before: dict | None
    after: dict | None
    metadata: dict               # user_note, llm_reasoning, sim_config_hash

class Scenario(BaseModel):
    id: str
    domain: str
    name: str
    objectives: list[Objective]
    head_event_seq: int
    current_branch: str          # branch ativo default pra novos eventos

class EventLog:
    def append(self, scenario_id: str, event: Event) -> None: ...
    def read(
        self,
        scenario_id: str,
        branch_id: str | None = None,
        up_to_seq: int | None = None,
    ) -> list[Event]: ...
    def head(self, scenario_id: str, branch_id: str) -> int: ...
```

Storage: `scenarios/<id>/events.jsonl` — uma linha por evento, JSON parse-safe. Append é o(1). Read é streaming.

### `core/snapshot.py` — snapshots + replay

Snapshot é state materializado num ponto. Auto-snapshot a cada 50 eventos. Comprimido zstd.

```python
class Snapshot(BaseModel):
    scenario_id: str
    at_seq: int
    branch_id: str
    entities: dict[str, dict]
    env: dict
    sim_results_index: dict  # config_hash -> file ref

class SnapshotStore:
    def save(self, snapshot: Snapshot) -> None:
        """Escreve scenarios/<id>/snapshots/seq-<N>.json.zst"""
        ...
    def load(self, scenario_id: str, at_seq: int) -> Snapshot: ...
    def list(self, scenario_id: str, branch_id: str) -> list[SnapshotInfo]: ...

class Replay:
    @staticmethod
    def rebuild_state(scenario_id: str, target_seq: int) -> State:
        """
        1. SnapshotStore.list — acha snapshot mais próximo <= target_seq
        2. EventLog.read entre snapshot.at_seq e target_seq
        3. Aplica eventos em ordem
        4. Retorna State
        """
        ...
```

Portabilidade: pasta `scenarios/<id>/` inteira é o cenário. `tar czf backup.tar.gz scenarios/<id>` e leva.

### `core/iteration_engine.py` — motor de iteração event-based

Sem state machine rígida. Loop reativo. Usuário pode inserir evento entre qualquer chamada.

```python
class IterationEngine:
    def step(
        self,
        scenario_id: str,
        phase: Literal["design", "iterate", "simulate", "judge"],
    ) -> StepResult:
        """
        Executa uma fase, grava eventos correspondentes.
        Atomic — falha no meio não commita eventos parciais.
        """
        ...

    def auto_loop(
        self,
        scenario_id: str,
        max_steps: int = 10,
        stop_on_convergence: bool = True,
    ) -> LoopResult:
        """
        Roda phases em ordem: design (se scenario vazio) -> simulate -> judge -> iterate -> loop.
        Antes de cada step: verifica EventLog.head() vs seq no início do último step.
        Se cresceu (usuário injetou evento), incorpora antes de continuar.
        """
        ...
```

### `core/objectives.py` — multi-objetivo

```python
class Objective(BaseModel):
    metric_name: str
    direction: Literal["minimize", "maximize", "target"]
    target_value: float | None = None
    weight: float = 1.0

class ObjectiveAggregator:
    @staticmethod
    def score(objectives: list[Objective], metric_results: dict) -> float: ...

    @staticmethod
    def pareto_check(
        objectives: list[Objective],
        candidates: list[Candidate],
    ) -> list[Candidate]:
        """Retorna só os pontos da frente de Pareto."""
        ...
```

### `core/sim_cache.py` — cache incremental de simulação

Freshness por config: `computed_at_seq` = `EventLog.head()` no momento em que cachou. Se `head_seq > computed_at_seq`, marca stale na UI.

```python
class SimCacheEntry(BaseModel):
    config_hash: str
    entities_involved: set[str]  # pra invalidação por entity_id
    kind: Literal["quick", "full"]
    computed_at_seq: int
    run_result: RunResult

class SimCache:
    def get(self, config_hash: str) -> SimCacheEntry | None: ...
    def put(self, entry: SimCacheEntry) -> None: ...
    def invalidate_touching(self, entity_ids: set[str]) -> None: ...

class IncrementalSimRunner:
    def run(
        self,
        entities: list[Entity],
        env: Environment,
        n_runs: int,
        kind: Literal["quick", "full"],
    ) -> RunResult:
        """
        Full run se kind=full. Quick = N reduzido (100 vs 1000) pra UI live.
        Verifica cache. Miss parcial: roda só as duplas que faltam.
        """
        ...
```

**Freshness na UI (ver Sprint 5):**
- 🟢 full: cache hit com kind=full e computed_at_seq == head_seq
- 🟡 quick: cache hit com kind=quick, ou parcial
- 🔴 stale: computed_at_seq < head_seq (algo mudou)
- ⏳ computing: run em andamento (SSE progress)

### `core/simulator_interface.py`

ABC que domínios implementam.

```python
class RunResult(BaseModel):
    entities_involved: list[str]  # ids
    outcome: dict                 # domain-specific but structured
    duration_steps: int
    seed: int

class Environment(BaseModel):
    """Base env; each domain subclasses."""
    seed: int

class SimulatorInterface(ABC):
    @abstractmethod
    def entity_schema(self) -> EntitySchema: ...

    @abstractmethod
    def environment_schema(self) -> type[Environment]: ...

    @abstractmethod
    def run(
        self,
        entities: list[BaseModel],
        env: Environment,
    ) -> RunResult: ...

    @abstractmethod
    def default_metrics(self) -> list[Metric]: ...

    @abstractmethod
    def llm_generation_prompt(self, constraints: list[Constraint]) -> str:
        """Domain-specific prompt fragment appended to base generator prompt."""
        ...
```

### `core/metrics/`

Interface + implementações genéricas.

```python
# base.py
class Metric(ABC):
    name: str
    description: str

    @abstractmethod
    def compute(self, runs: list[RunResult]) -> MetricResult: ...

# rating.py
class EloMmrRating(Metric):
    """Elo-MMR rating per entity based on head-to-head runs."""
    name = "elo_mmr"
    def compute(self, runs: list[RunResult]) -> dict[str, float]:
        ...

# distribution.py
class WinRateDistribution(Metric):
    """Win rate per entity, dispersion, outliers."""
    name = "winrate_distribution"

# aggregators.py — combine multiple metrics into a report
```

### `core/report_engine.py`

Consolida runs + métricas em JSON estruturado consumido pela UI.

```python
class Report(BaseModel):
    domain: str
    n_runs: int
    entity_set_hash: str
    env_hash: str
    metric_results: dict[str, Any]
    generated_at: datetime

def build_report(runs: list[RunResult], metrics: list[Metric]) -> Report:
    ...
```

## Domains (padrão de plugin)

Cada domínio é um módulo autocontido com 3 arquivos + seed data:

```
domains/<name>/
├── __init__.py           # export get_simulator() -> SimulatorInterface
├── schema.py             # define EntitySchema para o domínio
├── simulator.py          # implementa SimulatorInterface
├── metrics.py            # métricas específicas do domínio
└── seed_data.json        # exemplos pra bootstrap
```

### `domains/card_game/`

- Entity: `Unit(name, cost, hp, damage, ability_kind, ability_value)`
- Env: `MatchEnv(hand_size, mana_curve, turn_limit, seed)`
- Simulator: turn-based 1v1 combat, seeded RNG, retorna `RunResult` com `winner`, `turns`, `damage_dealt`
- Metrics: `WinRateMatrix`, `EloMmrRating`, `TtkStats`
- Seed: 10 unidades base cobrindo aggro/control/combo

### `domains/creature_rpg/`

- Entity: `Creature(name, type, hp, atk, def_, skills[], resistances{})`
- Env: `GauntletEnv(mode: "gauntlet"|"tournament", n_battles, seed)` — gauntlet = 1 vs random N; tournament = round-robin subset
- Simulator: turn-based com type-matchup table, ability queue
- Metrics: `EloMmrRating`, `TierEmergence`, `DominanceIndex`, `UsageCoverage`
- Seed: 200 creatures cobrindo 8 tipos

### `domains/team_composition/` (demo de extensibilidade)

- Entity: `Person(name, seniority, skills[], preferred_task_types[])`
- Env: `WorkloadEnv(tasks: list[TaskType], deadline_days, seed)`
- Simulator: simulação probabilística de completion (cada task tem `required_skills` + `estimated_hours`, cada pessoa contribui baseado em skill match + carga)
- Metrics: `SkillCoverage`, `Redundancy`, `SinglePointOfFailure`, `CompletionRate`
- Seed: 50 pessoas, 20 task types

## API (FastAPI)

Rotas agnósticas ao domínio; roteamento por `{name}`.

```
GET  /domains                                    → list registered domains
GET  /domains/{name}/schema                      → EntitySchema (JSON)
GET  /domains/{name}/environment-schema          → Environment schema
GET  /domains/{name}/metrics                     → list of Metric.name + description
GET  /domains/{name}/seed                        → seed entities

POST /domains/{name}/generate
     Body: {n, constraints, user_intent}
     Returns: list of validated entities

POST /domains/{name}/simulate
     Body: {entities, env, n_runs, metrics}
     Returns: Report

GET  /experiments                                → list saved experiments (Postgres)
POST /experiments                                → save current run for later
GET  /experiments/{id}                           → fetch
```

Domain registry em `api/registry.py`: import dinâmico de `domains/*/__init__.py` na inicialização.

## Frontend (Next.js 15)

Estrutura de rotas:

```
app/
├── page.tsx                                    → domain picker
├── domains/[name]/
│   ├── editor/page.tsx                         → entity editor
│   ├── generate/page.tsx                       → LLM generator UI
│   ├── simulate/page.tsx                       → run + progress
│   └── results/[experimentId]/page.tsx         → dashboard
└── experiments/page.tsx                        → history
```

Componentes genéricos:
- `<EntityEditor schema={...} value={...} onChange={...} />` — renderiza form a partir de EntitySchema
- `<MetricCard result={...} />` — renderiza métrica agnóstica ao tipo
- `<DistributionChart data={...} />`, `<RatingBarChart data={...} />` (Recharts)

Componentes domain-specific (opcionais, registrados por domain):
- Card game: `<MatchupHeatmap />`
- Creature RPG: `<TierList />`
- Team: `<SkillCoverageGrid />`

## Cache (`diskcache` no dev, Redis no prod)

Abstração `core/cache_backend.py`:
```python
class CacheBackend(Protocol):
    def get(self, key: str) -> bytes | None: ...
    def set(self, key: str, value: bytes, ttl_seconds: int) -> None: ...

class DiskCacheBackend:   # dev — SQLite-based, arquivo em CACHE_DIR
    ...

class RedisCacheBackend:  # prod — Sprint 7
    ...
```

Chave: `sim:{domain}:{sha256(entities_json + env_json + n_runs)}`
Valor: JSON do Report
TTL: 24h por default, config por domain

`SimulationService.simulate()` verifica cache antes de rodar. Miss ratio logado em métrica. Contract testado com `tests/test_cache_backend.py` — mesmo teste roda contra Disk e Redis.

## Persistência (SQLite no dev, Postgres no prod)

SQLAlchemy 2.0 + Alembic. **Tipos portáveis desde o início:** sem JSONB/ARRAY do Postgres — use `JSON` genérico. Migração SQLite → Postgres no Sprint 7 é troca de `DATABASE_URL`; migrations reaplicam sem edição.

Tabelas:
- `experiments(id, domain, entity_set_json, env_json, report_json, created_at, user_id)`
- `entity_sets(id, domain, name, entities_json, created_at)` — sets nomeados reutilizáveis

## Convenções de código

- Python 3.11, type hints obrigatórios
- Pydantic v2 para todos os models
- SQLAlchemy 2.0
- Sem async no MVP a menos que benchmark mostre benefício
- Docstrings em inglês, uma linha, WHY quando não óbvio
- Frontend: TypeScript strict, Zod pra runtime validation dos payloads

## Segurança & seleção de backend (deploy)

Ver `docs/security-review.md` para o detalhe. Resumo operacional:

- **Auth de escrita:** `BALANCE_API_KEY` — se setada, `POST/PATCH/DELETE` exigem header
  `X-API-Key`. Sem ela, o servidor sobe em modo dev (escritas abertas) e loga um warning.
- **CORS:** `ALLOWED_ORIGINS` (vírgula separa múltiplas origens); default `http://localhost:3000`.
- **Rate limit:** `WRITE_RATE_LIMIT_PER_MIN` (default 60) por IP nas escritas.
- **Path validation:** `scenario_id`/`branch_id` passam por `core.paths.validate_id`
  (whitelist) — ids inseguros retornam 422 antes de tocar o disco.
- **Backend LLM:** `LLM_BACKEND=fake|local|anthropic`. `local` e `anthropic` compartilham os
  mesmos hats (`core/llm_local.py`), trocando só o transporte (`core/llm_client.py`).
  Produção usa `anthropic` (o llama-server local não é acessível de um servidor remoto).

## Presets & custom schemas (Scenario Editor backend)

A scenario is no longer locked to its plugin's schema. The plugin provides a **base schema +
simulator**; the scenario layers **user overrides** on top:

- `EntitySchema.with_overrides({"fields": [...]})` — edit/add/remove fields by name; touched
  fields are tagged `origin="user"`. Feeds `build_model()` and `to_llm_schema()` unchanged.
- `Scenario.schema_overrides` (persisted in the manifest) + `Scenario.effective_schema(registry)`
  = the plugin schema with overrides applied — what the scenario actually validates against.
- **Presets** (`presets/<domain>/<id>.json`, served by `GET /presets?domain=` and
  `GET /presets/{id}`) bundle `schema_overrides` + `default_constraints` + `default_objectives`
  + `default_visual_variant`. `POST /scenarios` accepts `preset_id`, extra `schema_overrides`
  (merged on top, user wins), and `visual_variant`. `GET /scenarios/{id}` returns the effective
  `schema`.

### Declarative enums per preset (FASE 1.5)

Presets rescale numeric ranges freely, and — since FASE 1.5 — they can also **replace the
categorical enums** the simulators used to hardcode, *without breaking determinism*. The
enum→behaviour mapping moved from Python into env data, carried by `Scenario.sim_config`
(populated from `Preset.sim_config`) and passed into the domain `Environment`:

- **card_game** — `MatchEnv.ability_map` maps a schema `ability_kind` value onto an engine
  primitive (`deal_damage`/`heal`/`shield`/`draw`). A preset renames/curates (MTG: `burn →
  deal_damage`, `counter → shield`, …). New *effects* still require engine primitives.
- **creature_rpg** — `GauntletEnv.type_matchup` supplies a full type-effectiveness matrix, so a
  preset can ship its own type roster (e.g. an 18-type elemental chart, common in
  creature-collector RPGs).
- **team_composition** — `WorkloadEnv.seniority_speed` declares an arbitrary seniority ladder →
  speed multiplier (intern..principal).

Empty config = the plugin default, so existing scenarios and every determinism test are
unchanged. The simulators stay pure (`run(entities, env)`), reading the mapping from `env`.
