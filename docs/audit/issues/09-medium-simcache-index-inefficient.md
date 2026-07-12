# `SimCache._index_add` recarrega e re-serializa JSON a cada `put`

**Severity:** Medium
**Priority:** P2
**Category:** Performance
**Source:** `core/sim_cache.py:82-90`

## Descrição

```python
# core/sim_cache.py:82-90
def _index_get(self, entity_id: str) -> list[str]:
    raw = self.backend.get(self._idx_key(entity_id))
    return json.loads(raw) if raw is not None else []

def _index_add(self, entity_id: str, config_hash: str) -> None:
    current = self._index_get(entity_id)
    if config_hash not in current:
        current.append(config_hash)
        self.backend.set(self._idx_key(entity_id), json.dumps(current).encode())
```

E `put`:

```python
def put(self, entry: SimCacheEntry) -> None:
    self.backend.set(self._sim_key(entry.config_hash), entry.model_dump_json().encode())
    for entity_id in entry.entities_involved:
        self._index_add(entity_id, entry.config_hash)
```

Cada `put` de uma matchup em uma dupla `[A, B]`:
- 1 get de `idx:A` (JSON parse)
- 1 set de `idx:A` (JSON serialize)
- 1 get de `idx:B` (JSON parse)
- 1 set de `idx:B` (JSON serialize)

Para uma round-robin de 20 entities (190 pares), cada `put` toca 2 idx keys, cada key é
lida N vezes (para cada matchup em que aparece — 19 matchups por entity). No total:
190 × 2 = 380 get + 380 set, mas o índice de A cresce até 19 hashes; ele é serializado
inteiro em cada set, então JSON round-trip cresce O(N).

Para Redis prod isso é 4 RTTs por put × 190 matchups × N iteradas.

## Risco

- Perf real: numa auto_loop com 20 entities e 10 iterações, isso é ~7600 Redis RTTs só
  para índice. Latência típica Fly.io → Upstash Redis ≈ 1-2 ms → 8-16 segundos gastos só
  em I/O de cache index (que deveria ser near-free).
- Ridicoulous when cached miss happens: a matchup nem foi rodada e ainda paga 4 RTTs.

Não é dramático porque o dev backend é `diskcache` local (nsyscalls, não RTT), mas o
plano em `deploy/README.md` é Upstash Redis em prod.

## Fix sugerido

Trocar list-JSON por set nativo Redis (SADD/SMEMBERS):

```python
# core/cache_backend.py — adicionar métodos set-like ao Protocol (backward compat via default impl)
class CacheBackend(Protocol):
    ...
    def sadd(self, key: str, member: str) -> None: ...
    def smembers(self, key: str) -> list[str]: ...

class InMemoryCacheBackend:
    ...
    def sadd(self, key, member):
        self._sets.setdefault(key, set()).add(member)
    def smembers(self, key):
        return list(self._sets.get(key, set()))

class RedisCacheBackend:
    def sadd(self, key, member): self._r.sadd(key, member)
    def smembers(self, key): return [m.decode() for m in self._r.smembers(key)]

class DiskCacheBackend:
    # diskcache não tem set; manter fallback JSON mas otimizado (dedup by set)
    ...
```

E:

```python
def _index_add(self, entity_id: str, config_hash: str) -> None:
    self.backend.sadd(self._idx_key(entity_id), config_hash)
```

Alternativa mais simples se não quiser mudar Protocol: batch os índices na `_put` e escreve
tudo de uma vez ao fim de uma round de matchups (pega a diff, faz 1 set por entity_id).

## Referências

- Redis SADD: https://redis.io/commands/sadd/
