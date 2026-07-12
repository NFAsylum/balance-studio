# `_valid_payload` exige entidade inteira, mas `LocalIterator` propõe payloads parciais

**Severity:** Medium
**Priority:** P1
**Category:** Logic
**Source:** `core/iteration_engine.py:180-197, 240-246`, `core/llm_local.py:181-197`

## Descrição

`LocalIterator` explicitamente pede ao modelo:

```python
# core/llm_local.py:181-197
system = (
    ...
    'Return ONLY JSON: {"modifications": [{"kind": "edit", "target": "<entity name>", '
    '"payload": {<only the changed fields>}, "reasoning": "<why>"}]}. '
    ...
)
```

Nota: `"only the changed fields"` — o modelo retorna um payload delta (ex.: `{"damage": 4}`
para nerf leve). Isso está OK e é bom design (menos tokens, menos chance de invalidar
outros campos).

Mas o `IterationEngine._iterate` (`core/iteration_engine.py:180-197`) rejeita esse delta:

```python
# Reject create/edit whose payload doesn't validate — never commit invalid state.
if mod.kind != "delete" and not _valid_payload(model_cls, mod.payload):
    rejected += 1
    continue

# ...
events.append(
    Event(
        ...
        after=None if mod.kind == "delete" else mod.payload,   # after = payload cru
    )
)
```

E `_valid_payload`:

```python
def _valid_payload(model_cls, payload) -> bool:
    try:
        model_cls(**payload)
        return True
    except (ValidationError, TypeError):
        return False
```

`model_cls(**{"damage": 4})` levanta ValidationError porque faltam `name`, `cost`, `hp`,
`ability_kind`, `ability_value`. **Todo edit parcial do LocalIterator é rejeitado.**

Note que o `scripts/experiment_balance.py:91-111` **contorna** isso manualmente:

```python
def _apply(entities, mods, model_cls) -> int:
    ...
    base = dict(entities.get(mod.target, {})) if mod.target else {}
    merged = {**base, **(mod.payload or {})}
    if not _valid_payload(model_cls, merged):
        continue
    ...
```

Ou seja: o autor **já sabe** do problema, mas a correção existe só no script de experimento,
não no core.

## Risco

- **Iterator LLM efetivamente broken em `iterate` phase.** Se o modelo cumpre a instrução
  "only the changed fields", 100% das modificações são rejeitadas silenciosamente (contadas
  em `rejected_invalid` mas não relatadas ao usuário).
- **Ou o modelo ignora a instrução** e retorna a entidade inteira, gastando 2-3× mais
  tokens e podendo introduzir mudanças não-intencionadas em campos que não deveria tocar.
- **Divergência entre `experiment_balance.py` e produção** — os números do
  README ("−10.6% em creature_rpg") vieram do script que faz merge, não do fluxo
  API/UI. O usuário rodando pela UI vê "0 modifications applied" onde o experimento
  mostrou balanço.

## Fix sugerido

Aplicar a mesma lógica de merge no core:

```python
# core/iteration_engine.py
def _iterate(self, scenario_id, branch, scenario, entities_data, instances) -> StepResult:
    ...
    for mod in mods:
        if mod.target and last_actor.get(mod.target) == "user":
            skipped.append(mod.target)
            continue

        if mod.kind == "delete":
            after = None
        else:
            base = entities_data.get(mod.target, {}) if mod.target else {}
            after = {**base, **(mod.payload or {})}
            if not _valid_payload(model_cls, after):
                rejected += 1
                continue

        target = mod.target or str(after.get("name", "new_entity"))
        events.append(Event(..., after=after, ...))
```

Alternativa: deixar o payload ser sempre completo mas garantir isso do lado do prompt
(mudar `"only the changed fields"` para `"the full updated entity"`). Piora token cost mas
mantém `after` como snapshot completo, o que casa melhor com o modelo de replay.

Recomendo o merge — matches a intenção do prompt atual e reduz custo de tokens.

## Referências

- Correção já existe em `scripts/experiment_balance.py:91-111`, comentada com
  "Edits MERGE the (often partial) payload".
