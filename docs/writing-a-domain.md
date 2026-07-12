# Escrevendo um domain — Balance Studio

Como adicionar um novo tipo de balanceamento (domain) ao framework. O core não muda — você
pluga um schema + um simulador + métricas, e o mesmo event log, engine de iteração, LLM hats
(Designer/Judge/Iterator), cache e UI passam a operar sobre o seu domínio.

> **A promessa:** card game (10 unidades), creature RPG (100 creatures) e team composition
> (50 pessoas) rodam pela **mesma** infraestrutura. Um domínio novo custa horas de plugin,
> não semanas de reescrita.

## Anatomia de um domain

```
domains/<name>/
├── __init__.py        # export get_simulator() -> SimulatorInterface
├── schema.py          # define a EntitySchema do domínio (+ seed generator)
├── simulator.py       # implementa SimulatorInterface
├── metrics.py         # métricas específicas (opcional; core já tem genéricas)
└── seed_data.json     # exemplos pra bootstrap
```

O registry (`api/registry.py`) descobre automaticamente qualquer subpacote de `domains/` que
exponha `get_simulator()`. Não precisa registrar em lugar nenhum.

## O contrato: `SimulatorInterface`

```python
class SimulatorInterface(ABC):
    def entity_schema(self) -> EntitySchema: ...        # a EntitySchema da entidade
    def environment_schema(self) -> type[Environment]: ...  # subclasse de Environment
    def run(self, entities, env) -> RunResult: ...       # UMA simulação determinística
    def default_metrics(self) -> list[Metric]: ...       # métricas computadas por padrão
    def llm_generation_prompt(self, constraints) -> str: ...  # dica pro Designer LLM

    # opcionais (têm default no core):
    def run_batch(self, entities, env, n_runs) -> list[RunResult]: ...
    def matchups(self, entities) -> list[list[Entity]]: ...
```

Regras invioláveis:
- **`run` é puro e determinístico** dado `env.seed`. Sem I/O, sem LLM dentro do runner.
- **Nada de domínio no core.** Se você sente que precisa mudar `core/*`, a interface está
  errada — pare e discuta (é redesign de interface, não workaround).

### `matchups` e `run_batch`

A engine simula um *conjunto* de entidades. Como formar as partidas é específico do domínio:
- **Competitivo (card/creature):** `matchups()` retorna todos os pares; a engine roda cada
  par e o cache incremental invalida só os pares afetados quando você edita uma entidade.
- **Estrutural (team):** o default (`matchups = [entities]`, `run_batch` repete com seeds
  variados) já serve — uma "partida" é o time inteiro trabalhando a workload.

## Quickstart (10 minutos): `hello_domain`

Um domínio minimal que "balanceia" saudações pela sua cordialidade (`warmth`).

### 1. Schema — `domains/hello_domain/schema.py`

```python
import json
from pathlib import Path
from pydantic import BaseModel
from core.entity_schema import EntitySchema

_SEED = Path(__file__).with_name("seed_data.json")

def get_schema() -> EntitySchema:
    return EntitySchema.from_dict({
        "name": "Greeting",
        "fields": [
            {"name": "name", "kind": "str", "min_len": 1, "max_len": 40},
            {"name": "warmth", "kind": "num", "range": [0, 10]},
        ],
    })

def load_seed() -> list[BaseModel]:
    model = get_schema().build_model()
    return [model(**e) for e in json.loads(_SEED.read_text())]
```

### 2. Simulador — `domains/hello_domain/simulator.py`

```python
from typing import Any
from core.entity_schema import EntitySchema
from core.metrics.base import Metric, MetricResult
from core.simulator_interface import Environment, RunResult, SimulatorInterface
from domains.hello_domain.schema import get_schema

class GreetEnv(Environment):
    pass  # só o seed herdado da base

class AvgWarmth(Metric):
    name, kind, description = "avg_warmth", "distribution", "Mean warmth of the set."
    def compute(self, runs: list[RunResult]) -> MetricResult:
        vals = [r.outcome["avg_warmth"] for r in runs]
        return MetricResult(kind=self.kind, name=self.name,
                            data={"mean": sum(vals) / len(vals) if vals else 0.0})

class HelloSimulator(SimulatorInterface):
    def entity_schema(self) -> EntitySchema: return get_schema()
    def environment_schema(self) -> type[Environment]: return GreetEnv
    def default_metrics(self) -> list[Metric]: return [AvgWarmth()]
    def llm_generation_prompt(self, constraints) -> str:
        return "Design warm, varied greetings (warmth 0-10)."
    def run(self, entities: list[Any], env: Environment) -> RunResult:
        data = [e.model_dump() if hasattr(e, "model_dump") else e for e in entities]
        avg = sum(d["warmth"] for d in data) / len(data) if data else 0.0
        return RunResult(entities_involved=[d["name"] for d in data],
                         outcome={"avg_warmth": avg}, duration_steps=1, seed=env.seed)
```

### 3. Export — `domains/hello_domain/__init__.py`

```python
from domains.hello_domain.simulator import HelloSimulator
def get_simulator() -> HelloSimulator:
    return HelloSimulator()
```

### 4. Seed — `domains/hello_domain/seed_data.json`

```json
[{"name": "Hi", "warmth": 3}, {"name": "Warm welcome", "warmth": 9}]
```

### 5. Pronto

```python
from api.registry import discover_domains
print(sorted(discover_domains()))   # -> [..., 'hello_domain']
```

O domínio já aparece na home da UI, aceita entidades manuais ou geradas por LLM, simula, e
mostra a métrica `avg_warmth`. Zero mudança no core.

## Kinds de campo (`FieldSpec.kind`)

| kind | tipo Python | extras | uso |
|---|---|---|---|
| `num` | float | `range: [min, max]` | stats numéricos |
| `cat` | Literal(enum) | `enum: [...]` (obrigatório) | tipo, seniority, ability_kind |
| `bool` | bool | — | flags |
| `str` | str | `min_len`/`max_len` | nomes, descrições (texto livre) |
| `tag_set` | list[str] | — | skills, tags |
| `map` | dict[str, float] | `enum` = chaves permitidas | resistances, pesos |

Qualquer campo pode ser opcional com `"required": false` (vira `T | None = None`).

## Walkthrough completo: `team_composition`

Domínio não-competitivo real (staffing). Veja `domains/team_composition/` inteiro.

- **schema.py** — `Person(name str, seniority cat, skills tag_set, preferred_task_types
  tag_set)`. Além da entidade, define um *registry* de `TaskType` (nome + `required_skills` +
  `estimated_hours`) que a workload consome. `generate_seed()` cria 50 pessoas determinísticas.
- **simulator.py** — `WorkloadEnv(tasks, deadline_days, hours_per_day, seed)`. `run()` faz
  atribuição gulosa: cada task vai pra uma pessoa capaz (tem todos os `required_skills`) com
  capacidade sobrando, preferindo quem gosta do tipo; esforço escala por seniority. O
  `outcome` carrega `completion_rate`, `avg_completion_hours`, `blocked_tasks` **e** a análise
  estrutural do time (`coverage`, `redundancy`, `spof_skills`). Determinístico (o seed só
  embaralha a ordem de chegada das tasks). Usa os defaults de `matchups`/`run_batch`.
- **metrics.py** — `CompletionRate`, `SkillCoverage`, `Redundancy`,
  `SinglePointOfFailure`. Leem os campos do `outcome` (o simulador embute a análise estrutural
  ali, então as métricas ficam na interface `compute(runs)` do core sem hardcodar nada além
  das chaves do próprio outcome).

Padrão-chave: **métricas estruturais** (que dependem da composição, não de vencedor) são
computadas pelo simulador e embutidas no `outcome`; as classes `Metric` só as leem.

## Como o LLM usa seu domain (de graça)

Você **não** escreve código de LLM. Os três hats já funcionam com qualquer schema:
- **Designer** deriva o JSON Schema de `EntitySchema.to_llm_schema()` e valida a saída contra
  o seu `build_model()`. Seu `llm_generation_prompt()` só dá o *flavor*.
- **Judge** avalia variety/cohesion/thematic sobre as entidades (agnóstico).
- **Iterator** propõe modificações; a engine valida o payload contra o seu schema e respeita
  autoria (nunca sobrescreve entidade editada pelo usuário).

Backend do LLM é `fake` (dev) ou `local`/… via `LLM_BACKEND` — o domínio não sabe qual.

## Checklist antes do PR

- [ ] `get_schema()` retorna uma `EntitySchema` válida; `seed_data.json` valida contra ela
- [ ] `run(entities, env)` é **determinístico** dado `env.seed` (rode 5x, mesmo resultado)
- [ ] `environment_schema()` é uma subclasse de `Environment` (tem `seed`)
- [ ] `default_metrics()` retorna métricas que leem só `RunResult` (nada de I/O)
- [ ] `__init__.py` exporta `get_simulator()`
- [ ] Domínio competitivo? Override `matchups()` (pares) pro cache incremental funcionar
- [ ] Testes: schema+seed, determinismo, cada comportamento-chave, cada métrica
- [ ] `grep -rn "from domains" core/` continua vazio (core não conhece domínios)
- [ ] `pytest` inteiro verde; `ruff check` limpo

## Rodando

```bash
poetry run uvicorn api.main:app --port 8000     # backend (registry descobre seu domínio)
cd ui && pnpm dev                                # UI em :3000 (seu domínio na home)
```
