# `EventLog.head()` faz `read()` completo + `max()` só pra achar o último seq

**Severity:** Medium
**Priority:** P1
**Category:** Performance
**Source:** `core/scenario.py:247-250`

## Descrição

```python
# core/scenario.py:247-250
def head(self, scenario_id: str, branch_id: str) -> int:
    """Return the highest seq in ``branch_id`` (0 if the branch has no events yet)."""
    seqs = [e.seq for e in self.read(scenario_id, branch_id=branch_id)]
    return max(seqs, default=0)
```

Isso lê `events.jsonl` inteiro, parseia todo evento como Pydantic model, extrai seq, e
pega o max. Para saber o **último** número de sequência.

Todo `append()` já faz `head()` antes de gravar (`scenario.py:172`). Toda escrita então é
O(N) — completamente desnecessário: o próprio `append()` já sabe qual é o novo head
(head + 1 do stored event).

## Risco

Combinado com finding #06, esse é o pior loop. `append()` faz `read()` + `max()` a cada
chamada. Um scenario com 5k events e 100 appends numa sessão = 500k linhas parseadas.

Além disso, `Scenario.head_event_seq` é gravado no manifesto (`_write_manifest` em cada
`append`) — o valor **já existe** persistido. `head()` poderia ler o manifesto em vez
do event log inteiro.

## Fix sugerido

Manter head em memória + persistir por branch no manifesto:

```python
# manifest.json shape:
{
  "scenario": {...},
  "branches": {
    "main":  {"name": "main",  "parent_branch": null, "fork_seq": 0, "head_seq": 42},
    "alt":   {"name": "alt",   "parent_branch": "main", "fork_seq": 10, "head_seq": 15}
  }
}
```

E:

```python
def head(self, scenario_id: str, branch_id: str) -> int:
    return self._read_manifest(scenario_id)[1][branch_id].get("head_seq", 0)

def append(self, scenario_id, event) -> Event:
    scenario, branches = self._read_manifest(scenario_id)
    ...
    head = branches[event.branch_id].get("head_seq", 0)
    stored = event.model_copy(update={"seq": head + 1, ...})
    ...
    branches[event.branch_id]["head_seq"] = stored.seq
    self._write_manifest(scenario, branches)
    return stored
```

Trocar `read` full por lookup O(1) no manifesto. `list_branches` (`branching.py:61-74`)
também para de recomputar `head_seq` via `max(e.seq for e in events)` — vira lookup.

**Cuidado:** o manifesto vira source-of-truth para head — se uma escrita cai no meio (só
appendou no jsonl mas não atualizou manifesto), pode divergir. Adicionar recovery: no
startup, se `head_seq_manifest < head_seq_jsonl`, alinhar (o jsonl é o real source).

## Referências

- Finding #06 (`EventLog.read()` O(N)) — parcialmente sobreposto; esse aqui é o caso
  específico mais quente.
