# `experiment_balance.py` importa `_valid_payload` (símbolo privado) de `core.iteration_engine`

**Severity:** Medium
**Priority:** P2
**Category:** Design
**Source:** `scripts/experiment_balance.py:21`, `core/iteration_engine.py:240-246`

## Descrição

```python
# scripts/experiment_balance.py:21
from core.iteration_engine import _valid_payload
```

`_valid_payload` é module-private (prefixo `_`) e vive dentro de `iteration_engine.py`:

```python
# core/iteration_engine.py:240-246
def _valid_payload(model_cls: type[BaseModel], payload: dict[str, Any]) -> bool:
    """True if an iterator's modification payload validates against the entity schema."""
    try:
        model_cls(**payload)
        return True
    except (ValidationError, TypeError):
        return False
```

O `_` no nome comunica "não faz parte da API pública". O uso em `experiment_balance.py`
força o autor a manter esse símbolo privado estável, ou o experimento quebra.

Além disso o próprio script duplica a lógica de "apply modifications" (`_apply` em
`experiment_balance.py:91-111`) que deveria viver no core — hoje ela é dividida entre
`IterationEngine._iterate` (rejeita partial payload) e o script (merge + apply).

## Risco

- **Refactor breaks silently.** Se alguém renomeia `_valid_payload` para
  `_validate_iteration_payload` (razoável), o experimento para de rodar. Não há teste
  cobrindo o experiment script.
- **Duplicação de lógica** — o merge partial payload existe só no script (ver finding #08).
  Fica difícil manter as duas implementações em sincronia.
- **Cheirinho de bad layering:** scripts/ é meta-código, não deve importar private de core.

## Fix sugerido

Promover `_valid_payload` para API pública OU extrair para módulo utilitário:

```python
# core/iteration_engine.py
def validate_payload_against_schema(model_cls, payload) -> bool:
    """True if ``payload`` validates against ``model_cls``. Used by scripts + engine."""
    try:
        model_cls(**payload)
        return True
    except (ValidationError, TypeError):
        return False

_valid_payload = validate_payload_against_schema  # backward compat interno
```

E extrair o merge helper para `core/iteration_engine.py`:

```python
def merge_partial_edit(base: dict, delta: dict) -> dict:
    """Merge an iterator's delta payload onto the current entity dict."""
    return {**base, **(delta or {})}
```

Aí `experiment_balance.py:91-111` fica muito mais fino, e a lógica de merge é reutilizada
no `_iterate` phase (resolvendo o finding #08).

## Referências

- Finding #08 (partial payload rejected) — mesmo underlying issue.
- PEP 8 sobre `_prefix` como convention.
