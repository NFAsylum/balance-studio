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
    kind: Literal["num", "cat", "bool", "tag_set"]
    range: tuple[float, float] | None = None      # for num
    enum: list[str] | None = None                 # for cat
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

### `core/llm_generator.py`

Gera candidatos via `tool_use`.

```python
class LlmGenerator:
    def __init__(self, llm_client: LlmClient, schema: EntitySchema):
        ...

    def generate(
        self,
        n: int,
        constraints: list[Constraint],
        seed_examples: list[BaseModel] | None = None,
        user_intent: str = "",
    ) -> list[BaseModel]:
        """
        Prompts LLM with tool_use schema. Retries with error feedback if invalid.
        Max 3 retries per batch. Filters out constraint violations post-generation.
        """
        ...
```

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

## Cache (Redis)

Chave: `sim:{domain}:{sha256(entities_json + env_json + n_runs)}`
Valor: JSON do Report
TTL: 24h por default, config por domain

`SimulationService.simulate()` verifica cache antes de rodar. Miss ratio logado em métrica.

## Persistência (Postgres)

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
