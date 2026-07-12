# Balance Studio — Auditoria de Código

**Data:** 2026-07-11 (contexto: 2026-07-06)
**Auditor:** Claude (Opus 4.7, 1M ctx)
**Escopo:** `core/`, `domains/`, `api/`, `scripts/`, `ui/`, `Dockerfile`, `fly.toml`, `.env*`
**Método:** leitura profunda + Grep por padrões suspeitos + análise de fluxo de dados

## Resumo executivo

Codebase está em bom estado geral. As regras de arquitetura mais importantes do CLAUDE.md
estão respeitadas: **core não importa nada de `domains/*`** (`grep "from domains" core/` vazio)
e domínios só importam de `core.entity_schema`, `core.metrics.base`, `core.simulator_interface`
(nunca invertem a direção). A determinismo dos simuladores está bem defendido — todo uso de
`random` passa por `random.Random(env.seed)`, sem RNG global. Não há `eval`, `exec`,
`pickle.load`, `os.system`, `shell=True`, `yaml.load()` inseguro em lugar nenhum. Não há
segredos (sk-…, ghp_…, tokens) hardcoded no repo, e o `.gitignore` cobre `.env`.

Os problemas encontrados concentram-se em três frentes:

1. **Segurança de deploy do FastAPI:** endpoints não sanitizam `scenario_id` na URL —
   `EventLog._dir()` monta `Path(base_dir) / scenario_id` sem checar `..`. Combinado com
   `allow_origins=["*"]` sem autenticação, um cenário chamado `../../../etc` cria/lê
   arquivos fora de `SCENARIOS_DIR`. Em produção (Fly.io no volume `/data`) isso permite
   escrita arbitrária sob o volume montado.
2. **Bug de identidade de entidade em edições:** `PATCH /scenarios/{sid}/entities/{entity_id}`
   usa a URL como chave (`target=entity_id`) mas o payload da entidade pode conter um `name`
   diferente. O replay grava `entities[entity_id] = payload_com_name_diferente`, criando
   estado inconsistente onde a chave do dict não bate com o campo `name` do valor.
3. **Gap entre discurso e implementação de LLM:** o CLAUDE.md e a documentação prometem
   `AnthropicDesigner/Judge/Iterator` como caminho de produção, mas `llm_factory.py`
   levanta `NotImplementedError` para `LLM_BACKEND=anthropic`. O `anthropic` está no
   `pyproject.toml` mas nunca é usado.

Além disso há performance quadrática em várias chamadas de `EventLog.read()` (nenhum
cache/index — cada operação relê `events.jsonl` inteiro), e alguns detalhes de code style
e UX menores.

## Breakdown por severidade

| Severidade | Total |
|---|---|
| Critical | 1 |
| High | 4 |
| Medium | 6 |
| Low | 3 |
| **Total** | **14** |

## Breakdown por categoria

| Categoria | Total |
|---|---|
| Security | 3 |
| Logic | 3 |
| Performance | 3 |
| Design | 2 |
| Testing | 1 |
| Code-guidelines | 1 |
| UX | 1 |

## Top 5 riscos mais preocupantes

1. **Path traversal em `scenario_id` da URL** (Critical, Security) — permite escrita/leitura
   de arquivos arbitrários no host, especialmente crítico com `allow_origins=["*"]` e sem
   auth. Ver `01-critical-path-traversal-scenario-id.md`.
2. **Inconsistência de identidade em `edit_entity`** (High, Logic) — o replay pode gravar
   `entities["Ace"] = {"name": "Bob", ...}`. Todo código downstream (LLM iterator, métricas,
   diff branches) assume que `entities[key]["name"] == key`. Ver
   `02-high-edit-entity-identity-mismatch.md`.
3. **CORS `allow_origins=["*"]` em prod sem auth** (High, Security) — combinado com escrita
   por POST/PATCH/DELETE, qualquer site na web pode CRUD cenários alheios. Ver
   `03-high-cors-wildcard-no-auth.md`.
4. **`sim_cache.IncrementalSimRunner` grava evento com `actor="user"` mesmo quando disparado
   pela iteração LLM** (High, Logic) — quebra a authorship guardrail que decide quais
   entidades o Iterator pode tocar. Ver `04-high-sim-cache-wrong-actor.md`.
5. **Anthropic backend prometido mas não implementado** (High, Design) — divergência entre
   docs/CLAUDE.md e código; `llm_factory.py` só suporta `fake` e `local`. Ver
   `05-high-anthropic-backend-not-implemented.md`.

## Índice de findings (ordem: severidade decrescente, depois prioridade)

| # | Sev | Prio | Categoria | Título |
|---|---|---|---|---|
| 01 | Critical | P0 | Security | Path traversal em `scenario_id`, `branch_id`, `entity_id` (não sanitizados) |
| 02 | High | P0 | Logic | `edit_entity` grava entidade com `name` diferente da chave (inconsistência de estado) |
| 03 | High | P1 | Security | CORS `allow_origins=["*"]` + endpoints de escrita sem auth |
| 04 | High | P0 | Logic | `IncrementalSimRunner` sempre grava `actor="user"` — falseia a authorship guardrail |
| 05 | High | P1 | Design | Backend `anthropic` documentado mas não implementado (`NotImplementedError`) |
| 06 | Medium | P1 | Performance | `EventLog.read()` é O(N) e não cacheia — várias chamadas por request |
| 07 | Medium | P1 | Performance | `EventLog.head()` faz `read()` completo + `max()` só pra achar o último seq |
| 08 | Medium | P1 | Logic | `Modification.payload` do LocalIterator pode ser parcial mas `_valid_payload` exige entidade inteira |
| 09 | Medium | P2 | Performance | `sim_cache._index_get` recarrega e re-serializa JSON a cada `put` |
| 10 | Medium | P2 | Security | LLM prompt injection possível via `brief` sem sanitização |
| 11 | Medium | P2 | Design | `experiment_balance.py` importa `_valid_payload` (símbolo privado) de `core.iteration_engine` |
| 12 | Low | P2 | Testing | `experiment_balance.py`/`experiment_b6.py` hardcoded a caminhos `/tmp/…` (quebra no Windows) |
| 13 | Low | P3 | Code-guidelines | `sqlalchemy`/`alembic` no `pyproject.toml` mas nunca usados (dep bloat) |
| 14 | Low | P3 | UX | Mistura pt/en na UI e em log messages; termos vagos ocasionais |

## Auditorias sem findings

- **Determinismo:** todo `random.Random(seed)` — nenhum RNG global. `datetime.now()` aparece
  só como `default_factory` em `Event`/`Report` (timestamps de metadados, aceitável).
- **Injeção de código Python (`eval`/`exec`/`pickle.loads`/`os.system`/`shell=True`):**
  nenhuma ocorrência.
- **Secrets vazados:** nenhum `sk-`, `ghp_`, ou token literal em código versionado. `.env`
  está no `.gitignore`.
- **Camada de layering:** `grep "from domains" core/` retorna vazio; regra de ouro respeitada.
- **`try: except: pass` / silent failure em código de produção:** todo `except` no `core/`
  captura tipos específicos e loga via `logger.info`. Apenas `experiment_balance.py` tem
  `except Exception` mas está fora do `core/` (script experimental) e com noqa comentada.
- **YAML unsafe:** nenhum `yaml.load()` sem `Loader=SafeLoader` — o projeto não usa PyYAML.
- **SQL injection:** o projeto não usa SQL (SQLAlchemy é dep morta — ver finding #13).
- **Testes:** 183 testes passando conforme README/CLAUDE.md. Cobertura verificada por
  amostragem parece robusta (test_iteration_engine.py cobre injeção, authorship, atomicidade,
  rejeição de payload inválido — não é só wiring).
