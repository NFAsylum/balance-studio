# `IncrementalSimRunner` sempre grava `actor="user"` — falseia authorship

**Severity:** High
**Priority:** P0
**Category:** Logic
**Source:** `core/sim_cache.py:148-160`

## Descrição

Quando o `IncrementalSimRunner.run()` termina, ele appenda um evento `simulate` ao log:

```python
# core/sim_cache.py:148-160
self.events.append_many(
    scenario_id,
    [
        Event(
            branch_id=branch,
            actor="user",           # <-- SEMPRE "user", mesmo quando chamado pelo Iterator
            kind="simulate",
            target="scenario",
            after={"n_runs": len(all_runs), "kind": kind, "metrics": metrics},
            metadata={"matchups_reused": reused, "matchups_computed": computed},
        )
    ],
)
```

Mas o `IterationEngine._simulate` (`core/iteration_engine.py:128-148`) chama esse runner
como parte da fase `simulate` do auto-loop, disparada pelo LLM Iterator. O evento
`simulate` fica então marcado como `actor="user"`, quando na verdade é `llm-iterator` (ou,
mais precisamente, "engine" — não há tipo pra isso).

## Risco

Efeito colateral direto na authorship guardrail (`iteration_engine.py:219-224`):

```python
def _last_actor_by_target(self, scenario_id, branch) -> dict[str, str]:
    actors: dict[str, str] = {}
    for event in self.events.read(scenario_id, branch_id=branch):
        if event.kind in _ENTITY_KINDS:
            actors[event.target] = event.actor
    return actors
```

Nesse caso específico, o filtro é sobre `_ENTITY_KINDS = {"create_entity", "edit_entity",
"delete_entity"}`, então o evento `simulate` não entra — o guardrail em si não quebra.
**Mas** os endpoints `list_scenarios`/`get_history` retornam o event log cru pra UI, que
mostra "user rodou simulate" quando na verdade foi o motor. Isso engana o usuário sobre
authorship — uma feature de venda do produto ("colaboração fluida humano/LLM") assenta
justamente em quem fez o quê.

Além disso, o `metadata={"matchups_reused": reused, "matchups_computed": computed}` mistura
métricas de perf do runner com metadata semântica — dois níveis de abstração no mesmo campo.

Um segundo problema no mesmo evento: quando o `simulate` roda via `/domains/{name}/simulate`
(fora de um scenario), o `IncrementalSimRunner` **não** é usado (chama `simulator.run`
direto em `api/main.py:139`) — então esse `actor="user"` fixo só afeta o caminho
event-based via `IterationEngine`. Ainda assim é bug real.

## Fix sugerido

Deixar o caller informar o actor:

```python
# core/sim_cache.py
def run(
    self,
    scenario_id: str,
    entities: list[BaseModel],
    env: Environment,
    n_runs: int,
    kind: Kind = "full",
    branch: str = "main",
    actor: str = "user",   # NEW
) -> SimRunReport:
    ...
    Event(branch_id=branch, actor=actor, kind="simulate", ...)
```

E em `core/iteration_engine.py:137`:

```python
report = runner.run(scenario_id, instances, env, self.n_runs, kind="full", branch=branch,
                    actor="llm-iterator")
```

Ou, mais limpo, extrair a gravação do evento do runner e deixar o caller montar
(runner só computa e retorna, engine grava). Isso alinha com o princípio de
"cache é do core, não do domain" — o cache não deveria estar gravando eventos de scenario.

## Referências

- Guardrail definido em `CLAUDE.md:23`: "Nunca sobrescreve edição do usuário".
- Actor enum em `core/scenario.py:22`.
