# Escrevendo um domain — Balance Studio

Como adicionar um novo tipo de balanceamento (domain) ao framework.

## Quickstart 10 minutos

Vamos criar um domain minimal: `hello_domain` que balanceia "greetings" (só pra demonstrar mecânica).

### 1. Criar pasta e arquivos

```bash
mkdir -p domains/hello_domain
touch domains/hello_domain/__init__.py
touch domains/hello_domain/schema.py
touch domains/hello_domain/simulator.py
touch domains/hello_domain/metrics.py
touch domains/hello_domain/seed_data.json
```

### 2. Schema (`domains/hello_domain/schema.py`)

```python
from core.entity_schema import EntitySchema, FieldSpec

def get_schema() -> EntitySchema:
    return EntitySchema(
        name="Greeting",
        fields=[
            FieldSpec(name="text", kind="cat", enum=["hi", "hello", "hey", "greetings"]),
            FieldSpec(name="warmth", kind="num", range=(0, 10)),
            FieldSpec(name="formality", kind="num", range=(0, 10)),
        ],
    )
```

### 3. Simulator (`domains/hello_domain/simulator.py`)

```python
from core.simulator_interface import SimulatorInterface, RunResult, Environment
from core.metrics.base import Metric
from core.metrics.rating import EloMmrRating
from pydantic import BaseModel
import random

class HelloEnv(Environment):
    social_context: str = "professional"

class HelloSimulator(SimulatorInterface):
    def entity_schema(self):
        from .schema import get_schema
        return get_schema()

    def environment_schema(self):
        return HelloEnv

    def run(self, entities: list[BaseModel], env: HelloEnv) -> RunResult:
        rng = random.Random(env.seed)
        # Simplistic: greeting with formality closer to context wins
        target = 8 if env.social_context == "professional" else 3
        distances = [(e, abs(e.formality - target)) for e in entities]
        winner = min(distances, key=lambda x: x[1])[0]
        return RunResult(
            entities_involved=[e.text for e in entities],
            outcome={"winner": winner.text, "context": env.social_context},
            duration_steps=1,
            seed=env.seed,
        )

    def default_metrics(self) -> list[Metric]:
        return [EloMmrRating()]

    def llm_generation_prompt(self, constraints):
        return "Generate friendly greetings with varied warmth and formality."
```

### 4. Entry point (`domains/hello_domain/__init__.py`)

```python
from .simulator import HelloSimulator

def get_simulator():
    return HelloSimulator()
```

### 5. Seed data (`domains/hello_domain/seed_data.json`)

```json
[
  {"text": "hi", "warmth": 8, "formality": 2},
  {"text": "hello", "warmth": 6, "formality": 6},
  {"text": "hey", "warmth": 9, "formality": 1},
  {"text": "greetings", "warmth": 4, "formality": 9}
]
```

### 6. Testar

```bash
poetry run python -c "
from api.registry import get_domain
sim = get_domain('hello_domain')
print(sim.entity_schema())
"
```

Deve listar o schema. Agora chama `POST /domains/hello_domain/simulate` da UI.

---

## Full walkthrough: `team_composition`

Este é o domain do Sprint 5. Segue exatamente o mesmo padrão do quickstart, mas com lógica realista.

### `domains/team_composition/schema.py`

```python
from core.entity_schema import EntitySchema, FieldSpec

def get_schema() -> EntitySchema:
    return EntitySchema(
        name="Person",
        fields=[
            FieldSpec(name="name", kind="cat"),
            FieldSpec(
                name="seniority",
                kind="cat",
                enum=["junior", "mid", "senior", "lead"],
            ),
            FieldSpec(
                name="skills",
                kind="tag_set",
                enum=[
                    "frontend", "backend", "mobile", "data", "devops",
                    "design", "product", "qa", "security",
                ],
            ),
            FieldSpec(
                name="preferred_task_types",
                kind="tag_set",
                enum=["feature", "bug", "infra", "research", "docs"],
            ),
        ],
    )
```

### `domains/team_composition/simulator.py`

Modelo probabilístico: dada uma lista de `Person` e um `Workload` (list de `Task`), simular quanto do workload é completado no deadline.

```python
class WorkloadEnv(Environment):
    tasks: list[Task]
    deadline_days: int

class TeamSimulator(SimulatorInterface):
    def run(self, entities: list[Person], env: WorkloadEnv) -> RunResult:
        rng = random.Random(env.seed)
        completed = 0
        blocked = 0
        for task in env.tasks:
            candidates = [p for p in entities if set(task.required_skills) & set(p.skills)]
            if not candidates:
                blocked += 1
                continue
            best = max(candidates, key=lambda p: skill_match_score(p, task))
            success_prob = compute_success_prob(best, task, rng)
            if rng.random() < success_prob:
                completed += 1
        return RunResult(
            entities_involved=[p.name for p in entities],
            outcome={
                "completed": completed,
                "blocked": blocked,
                "total": len(env.tasks),
            },
            duration_steps=env.deadline_days,
            seed=env.seed,
        )
    ...
```

### `domains/team_composition/metrics.py`

```python
class SkillCoverage(Metric):
    """Fraction of required skills present in the team across all runs."""
    ...

class Redundancy(Metric):
    """For each skill, how many team members have it. Higher = more resilience."""
    ...

class SinglePointOfFailure(Metric):
    """Skills held by exactly one member. Report count + names."""
    ...
```

---

## Checklist antes de considerar um domain "pronto"

- [ ] `get_simulator()` retorna instância funcional
- [ ] `entity_schema()` retorna `EntitySchema` válido
- [ ] `environment_schema()` retorna classe (não instância)
- [ ] `run()` é determinístico dado `env.seed` — testado com 5 execuções mesma seed
- [ ] `default_metrics()` retorna ao menos 1 métrica
- [ ] `llm_generation_prompt()` retorna string não-vazia com guidelines de design
- [ ] `seed_data.json` valida contra o schema
- [ ] Ao menos 5 testes em `tests/domains/test_<name>.py` cobrindo:
  - Load do schema
  - Load do seed
  - `run()` determinístico
  - Cada métrica retorna estrutura esperada
  - `llm_generation_prompt()` retorna string
- [ ] Domain não importa nada de outros domains
- [ ] Domain não modifica nada do core

## O que NÃO fazer

- ❌ Importar de outro domain (`from domains.card_game import ...`)
- ❌ Chamar LLM dentro de `run()` (simulador deve ser puro)
- ❌ Persistir estado global entre runs (usar apenas `env.seed`)
- ❌ Hardcodar constantes de balance (dificulta iteração; use env ou constraint)
- ❌ Assumir que a UI vai renderizar sua métrica de forma especial — se precisar de view custom, registre explicitamente

## Como aparecer na UI

Registry auto-descobre domains em `domains/*/__init__.py` no startup. Nenhuma configuração extra.

Se quiser view custom no frontend (opcional):

1. Adicionar componente em `ui/app/domains/<name>/CustomView.tsx`
2. Registrar em `ui/config/domain-views.ts`:
   ```typescript
   export const DOMAIN_VIEWS = {
     card_game: () => import("./card_game/CustomView"),
     // <name>: () => import("./<name>/CustomView"),
   };
   ```
3. Se não registrar, cai no dashboard genérico automaticamente
