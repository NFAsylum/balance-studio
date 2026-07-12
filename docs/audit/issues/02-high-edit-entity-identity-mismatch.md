# `edit_entity` grava entidade com `name` diferente da chave da URL

**Severity:** High
**Priority:** P0
**Category:** Logic
**Source:** `api/main.py:273-289`, `core/snapshot.py:92-97`

## Descrição

O endpoint `PATCH /scenarios/{scenario_id}/entities/{entity_id}` usa o `entity_id` da URL
como `Event.target`, mas grava o payload do cliente como `Event.after` sem verificar se
`payload["name"] == entity_id`:

```python
# api/main.py:273-289
@app.patch("/scenarios/{scenario_id}/entities/{entity_id}")
def edit_entity(scenario_id: str, entity_id: str, request: EntityRequest) -> dict[str, Any]:
    ...
    data = _validate_entity(scenario.domain, request.entity)   # valida schema, não identidade
    event = Event(
        branch_id=branch,
        actor="user",
        kind="edit_entity",
        target=entity_id,        # chave = URL
        before=state.entities[entity_id],
        after=data,              # pode ter name != entity_id
    )
    return services.event_log.append(scenario_id, event).model_dump(mode="json")
```

E o replay grava crua:

```python
# core/snapshot.py:92-97
def _apply_event(entities: dict[str, dict[str, Any]], event: Event) -> None:
    if event.kind == "create_entity" or event.kind == "edit_entity":
        entities[event.target] = event.after or {}      # chave = target, valor = after
```

Cenário concreto:

1. Usuário cria unidade `"Ace"` (chave `"Ace"`, `entity.name == "Ace"`).
2. Usuário faz `PATCH /scenarios/s1/entities/Ace` com body `{"entity": {"name": "Bob", "cost": 2, ...}}`.
3. State fica: `entities["Ace"] = {"name": "Bob", "cost": 2, ...}`.

## Risco

Múltiplos módulos assumem `entities[key]["name"] == key`:

- `IterationEngine._iterate` faz `target = mod.target or str(mod.payload.get("name", ...))`
  — se o Iterator LLM propõe editar `"Bob"` (o nome real), o motor procura `entities["Bob"]`,
  não encontra e (dependendo do fluxo) trata como create; ou o filtro authorship
  `last_actor.get(mod.target)` erra o alvo.
- `sim_cache.IncrementalSimRunner._names` extrai `m.model_dump().get("name", str(i))` — a
  chave usada como identidade da entidade nas métricas diverge da chave usada no state.
- `WinRateDistribution` conta por `entities_involved` — que vêm de `simulator.run_batch`
  onde a chave é o `deck.id` (=  o "name" do payload em `card_game.run_batch`). Isso batê-lo
  com a chave do state fica ambíguo.
- `Branch.diff` compara `state.entities` por chave; renomear via edit produz "unchanged"
  no diff mesmo tendo mudado.

Pior: eventualmente o próprio replay pode ficar quebrado se um edit posterior usar o novo
`name` como target — vira uma segunda entrada e a antiga fica órfã sem delete.

## Fix sugerido

Rejeitar o rename via edit (o design não deixa claro se rename é intended):

```python
# api/main.py, dentro de edit_entity, depois de _validate_entity:
if data.get("name") and data["name"] != entity_id:
    raise HTTPException(
        status_code=422,
        detail=f"entity name '{data['name']}' does not match path '{entity_id}'; "
               f"rename via delete+create instead"
    )
```

Ou, se rename é feature desejada, adicionar `kind="rename_entity"` explícito com
`target=old_id, after={"new_id": ...}` e tratar em `_apply_event`. Recomendo a primeira
opção — matches o comportamento atual do `add_entity` que usa `data["name"]` como target.

## Referências

- Analogamente para `create_entity` já existe consistência: `api/main.py:262`
  `target = str(data["name"])`. Basta reforçar a invariante em edits.
