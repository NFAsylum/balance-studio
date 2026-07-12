# `EventLog.read()` é O(N) e não cacheia — várias chamadas por request

**Severity:** Medium
**Priority:** P1
**Category:** Performance
**Source:** `core/scenario.py:221-250`, todos os callers em `core/`

## Descrição

`EventLog.read()` abre `events.jsonl`, parseia todas as linhas via `Event.model_validate_json`,
filtra em memória:

```python
# core/scenario.py:221-245
def read(self, scenario_id, branch_id=None, up_to_seq=None) -> list[Event]:
    events: list[Event] = []
    path = self._events_path(scenario_id)
    if not path.exists():
        return events
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            ...
            event = Event.model_validate_json(line)
            if branch_id is not None and event.branch_id != branch_id:
                continue
            if up_to_seq is not None and event.seq > up_to_seq:
                continue
            events.append(event)
    ...
```

Nenhum cache. Múltiplos callers chamam `read()` várias vezes por request:

1. `IterationEngine.step("iterate")` — chama:
   - `_last_actor_by_target` → 1 `read()` full
   - `_latest_winrate` → 1 `read()` full (reverse scan)
   - `_latest_judge` → 1 `read()` full (reverse scan)
   - `Replay.rebuild_state` → 1 `read(up_to_seq=head)`
2. `IterationEngine.step("simulate")` — chama:
   - `Replay.rebuild_state` → 1 `read()`
   - `IncrementalSimRunner._content_seq` → 1 `read()`
3. `EventLog.head()` internamente faz outro `read()` full.

`api/main.py:277` faz `services.event_log.head(scenario_id, branch)` (= 1 read) **e**
`services.replay.rebuild_state(scenario_id, head, branch)` (= mais 1 read) só pra montar
o `edit_entity`. Idem em `delete_entity`, `get_scenario`, etc.

Cada request para `iterate` (auto_loop com 10 steps) processa `events.jsonl` inteiro
mínimo 30-40 vezes. Para um cenário com 500 events (fácil de atingir em uma sessão),
isso é O(N × K × requests) — cresce quadraticamente com o histórico.

## Risco

- **UX degrada em cenários maduros.** Um cenário com 5k events (esperado depois de várias
  auto-loops) tem cada request lento (~100ms → 1s+ conforme cresce).
- **Cost inflation em prod.** Fly.io cobra por CPU-second; Redis cache miss + re-parse
  de milhares de eventos é overhead pura.
- **Snapshot infra existe justamente pra evitar isso mas não é usada em `read()`** —
  `Replay.rebuild_state` usa snapshot (bom), mas os métodos de query direto (`head`,
  `_last_actor_by_target`) ignoram o snapshot e vão no JSONL.

## Fix sugerido

Duas melhorias, incremental:

1. **Índice em memória de `head` por (scenario_id, branch):** `EventLog` mantém
   `self._head_cache: dict[tuple[str, str], int]`, atualizado em cada `append()`. `head()`
   consulta o dict (O(1)) e cai no `read()` só quando o cache está vazio (primeira leitura).
   Elimina 30-50% dos re-reads sem mudar semântica.

2. **Cache de `list[Event]` por (scenario_id, branch) invalidado em append:** o `read()`
   sem filtro popula um cache; `read(branch_id=...)` filtra do cache; `read(up_to_seq=...)`
   idem. Invalidação simples: em `append`/`append_many`, drop do cache. Streaming não fica
   pior pois já é in-memory.

Longer-term (fora do escopo desta auditoria): SQLite índice sobre events.jsonl, ou migração
para tabela SQLAlchemy (as libs já estão instaladas — ver finding #13).

## Referências

- Snapshot infra em `core/snapshot.py` já resolve pra state materialização, mas queries
  ad-hoc (winrate, judge, actor por target) ainda scan-all.
