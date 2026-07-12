# INBOX — 2026-07-11 (Balance Studio)

Após executar, mova esta task pra `docs/inbox-archive/YYYY-MM-DD-hhmm.md` ou apague.

## Contexto

Sprint 8 prep está feito (Redis backend, deploy files, README, seed polish). O que falta é trabalho humano de deploy real (contas Fly/Vercel + secrets) + demo video.

**Antes de deployar**, uma auditoria completa foi feita e revelou **14 findings** (1 Critical, 4 High, 6 Medium, 3 Low). Detalhes em `docs/audit/README.md`. Alguns são **bloqueadores absolutos pra qualquer deploy público** — atacante pega o servidor em minutos se subir do jeito atual.

Essa task é: **corrigir os bloqueadores de deploy** antes do humano tocar em `fly deploy`.

## Ordem de execução

**FASE 1 (obrigatória, ~5-7h)** — Fixes que bloqueiam deploy público. Rodar todas antes de qualquer `fly deploy`.

**FASE 2 (~2-3h, opcional se quiser fechar polish)** — Fixes que não bloqueiam deploy mas devem ser resolvidos antes de mostrar publicamente.

Fixes Low ficam pra backlog pós-deploy.

---

## FASE 1 — Fixes bloqueadores de deploy

### F1.1 — Path traversal em EventLog / SnapshotStore (audit #01, ~1-2h) ⚠ CRITICAL

Ver `docs/audit/issues/01-critical-path-traversal-scenario-id.md`.

**Problema:** `EventLog._dir(scenario_id)` monta `Path(base_dir) / scenario_id` sem sanitizar. Cliente manda `scenario_id="../../etc"` → escreve arquivo fora do volume. Mesmo problema em `branch_id` e `entity_id` quando compõem paths.

**Ação:**
- Criar validador `core/paths.py::validate_id(value: str, kind: str) -> str`:
  - Regex whitelist: `^[a-zA-Z0-9_-]{1,64}$`
  - Levanta `ValueError("invalid <kind> id: <value>")` se falhar
- Aplicar em **todos** os pontos de entrada:
  - `EventLog.append/read/head/init_scenario` — validar `scenario_id`, `branch_id`
  - `SnapshotStore.save/load/list` — mesmo
  - `SimCache` — mesmo se usa scenario_id em path
  - Handlers de API (`api/main.py` ou rotas) — validar path params antes de passar pro core
- Não usar `os.path.normpath` como defesa — atacante pode contornar
- Testes: 6 casos maliciosos (`..`, `/etc`, `\..\..\`, `%2e%2e`, `~`, unicode confusables)

**DoD:**
- 6 testes novos em `tests/test_paths.py` cobrindo cada ataque
- Refactor de `EventLog/SnapshotStore/SimCache` chama validador
- API rejeita path param inválido com 422 antes de chegar no core
- `pytest` inteiro continua verde (183+ testes)

### F1.2 — Auth mínimo + CORS restrito (audit #03, ~2h) ⚠ HIGH

Ver `docs/audit/issues/03-high-cors-wildcard-no-auth.md`.

**Problema:** `allow_origins=["*"]` + zero auth. Qualquer site na internet pode fazer POST/DELETE anônimo.

**Ação:**
- Adicionar auth por **API key simples** (headers `X-API-Key: <token>`):
  - Env var `BALANCE_API_KEY` — se setada, endpoints de escrita exigem match
  - Se não setada em dev: warning no startup + comportamento atual (dev-only)
  - Middleware FastAPI que valida antes de qualquer rota `POST/PATCH/DELETE`
- Restringir CORS:
  - Env var `ALLOWED_ORIGINS="https://balance-studio.vercel.app,http://localhost:3000"`
  - Sem env var: só localhost (dev)
- Bônus (30min): rate limit simples usando `slowapi` — 60 req/min por IP nos endpoints de escrita

**DoD:**
- `BALANCE_API_KEY=changeme poetry run uvicorn ...` — sem header X-API-Key retorna 401 em POST/PATCH/DELETE
- Sem env var: warning "⚠ running without API key auth (dev mode)" no log
- CORS só aceita origem da env var
- Testes: 4 cenários (com key, sem key, key errada, CORS de origem não permitida)
- Docs atualizadas em `docs/architecture.md` explicando como setar

### F1.3 — Anthropic backend: implementar ou remover promessa (audit #05, ~30min-1h)

Ver `docs/audit/issues/05-high-anthropic-backend-not-implemented.md`.

**Problema:** Docs mencionam `LLM_BACKEND=anthropic` mas código levanta `NotImplementedError`. Deploy em nuvem provavelmente vai precisar disso (LLM local não é acessível de servidor remoto).

**Ação — decisão do humano:**
- **Opção A (recomendada):** Implementar `AnthropicDesigner/Judge/Iterator` chamando SDK Anthropic. ~4-6h de trabalho — cai pra FASE 2 desse inbox se quiser.
- **Opção B (rápida):** Remover promessa dos docs. Trocar `NotImplementedError` por `ValueError` claro: "Anthropic backend not implemented — use LLM_BACKEND=local or fake". Atualizar `docs/architecture.md`, `README.md`, `.env.example`. Bloquear escolha na factory.

**Sugestão:** por ora Opção B (30min). Se decidir deployar em nuvem depois, implementar Opção A (não é urgente enquanto for local).

**DoD (Opção B):**
- Factory levanta `ValueError` com mensagem clara em `LLM_BACKEND=anthropic`
- `.env.example` comenta que anthropic backend não está implementado
- Docs atualizadas

### F1.4 — Identity mismatch em `edit_entity` (audit #02, ~30min)

Ver `docs/audit/issues/02-high-edit-entity-identity-mismatch.md`.

**Problema:** `PATCH /entities/{entity_id}` com body `{"name": "Bob"}` quando URL tem `Ace` → estado fica `entities["Ace"] = {"name": "Bob"}`. Chave da URL diverge do payload.

**Ação:**
- No handler do endpoint `PATCH`, validar: se `payload["name"]` diferir de `entity_id` path param, rejeitar com 422 ("name in payload must match URL path")
- Ou: renomear silenciosamente (payload wins) mas exigir `PUT` semântico — mudar handler pra rejeitar edits que mudam identidade e forçar create+delete
- Recomendo primeira opção (rejeitar) — semanticamente mais claro

**DoD:**
- Teste: `PATCH /entities/Ace` com body `{"name": "Bob"}` retorna 422 com mensagem clara
- Update válido (`PATCH /entities/Ace` com body `{"name": "Ace", "hp": 5}`) funciona
- `pytest tests/test_api_scenarios.py` verde

### F1.5 — `IncrementalSimRunner` grava actor correto (audit #04, ~15min)

Ver `docs/audit/issues/04-high-sim-cache-wrong-actor.md`.

**Problema:** sempre grava `actor="user"` mesmo quando o evento vem do LLM. Timeline UI vai mostrar "user fez simulate" quando foi o Iterator LLM.

**Ação:**
- `IncrementalSimRunner.run()` aceita param `actor: str` (default `"user"`)
- Callers (iteration_engine) passam o actor correto: `"llm-iterator"` quando dispara via IteratorLlm, etc.

**DoD:**
- Timeline UI mostra atribuição correta
- Teste: chamar `IncrementalSimRunner.run(actor="llm-iterator")` grava evento com `actor="llm-iterator"`

---

Depois da FASE 1 completa:
- `pytest` inteiro verde
- 4 testes novos passando (paths, auth, identity, actor)
- Docs atualizadas
- Documento `docs/security.md` breve explicando: auth via API key, CORS via env, path validation, LLM backend selection

Só então **é seguro pro humano deployar** em Vercel + Fly.io.

---

## FASE 2 — Polish antes de demo (opcional)

### F2.1 — Performance de EventLog.read O(N²) (audit #06, ~1h)

Ver issue #06. Rescan do log completo a cada `read()` com filtros. Fix: index em disco `events.idx` mantido em paralelo ao `events.jsonl`, mapeia `(branch_id, seq) → byte_offset`. Ou aceita e documenta como limite conhecido pra scenarios <1000 eventos.

### F2.2 — `EventLog.head()` faz full read (audit #07, ~30min)

Cache do último seq em memória por `(scenario_id, branch_id)`. Invalida em `append`.

### F2.3 — Payload parcial no Iterator (audit #08, ~30min)

Iterator LLM às vezes retorna edit com apenas alguns campos. Merge com estado atual antes de validar.

### F2.4 — Prompt injection do Iterator (audit #10, ~1h)

Sanitizar `user_note` e `reasoning` antes de injetar em prompt do próximo turno do Iterator.

### F2.5 — Símbolo privado `_valid_payload` importado (audit #11, ~15min)

Renomear pra `is_valid_payload` (público) ou refatorar caller.

---

## Fixes Low (backlog pós-deploy)

- Paths `/tmp` hardcoded quebram no Windows (audit #12) — usar `tempfile.gettempdir()`
- Dependências mortas (audit #13) — `sqlalchemy/alembic/tiktoken` não usadas, remover do pyproject
- UI mistura pt/en (audit #14) — padronizar em uma língua (recomendo inglês pra UI e docs internas continua PT)

---

## Notas

- **Reprodução dos números do B6.6:** experimento de balance-quality foi rodado com Fake/Local — não impactado pelos fixes acima. Mantém integridade da manchete "Iterator reduziu dispersão em 2/3 domínios".
- **Bug em produção sim, mas em MVP local ainda ok:** os Critical/High acima são "bloqueadores pra deploy público", não "produto quebrado". Localmente tudo funciona.
- **Custo:** $0 — nenhum fix precisa de LLM real, tudo é código.
- **Tempo total FASE 1:** 5-7h. FASE 2: 2-3h. Backlog Low: 1-2h.

Ao terminar FASE 1, escreva `docs/security-review.md` com resumo do que foi endereçado + o que fica pendente. Isso vira anexo do PR de deploy.
