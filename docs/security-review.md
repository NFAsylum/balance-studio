# Security Review — resposta à auditoria (2026-07-12)

Anexo do PR de deploy. Endereça os bloqueadores da auditoria (`docs/audit/`) antes de
qualquer `fly deploy` público. Branch: `dev-marco-security-fase1`.

## O que foi corrigido

### FASE 1 — bloqueadores de deploy

| # | Finding | Severidade | Fix |
|---|---|---|---|
| 01 | Path traversal em `scenario_id`/`branch_id` | **Critical** | `core/paths.py::validate_id` (whitelist `^[A-Za-z0-9_-]{1,64}$`, sem `.` → `..` rejeitado) + `safe_under` (resolve + `is_relative_to`). Aplicado em `EventLog`, `SnapshotStore`, `SimCache` e no path do disk cache. API mapeia `InvalidId → 422` antes de tocar disco. |
| 03 | CORS `*` + zero auth | High | CORS restrito por `ALLOWED_ORIGINS` (default localhost). Middleware exige `X-API-Key` == `BALANCE_API_KEY` em `POST/PATCH/DELETE`; sem key setada → warning + modo dev. Rate limit in-memory por IP (`WRITE_RATE_LIMIT_PER_MIN`, default 60) — sem dependência nova. |
| 05 | Backend `anthropic` prometido mas não implementado | High | **Implementado** via abstração de transporte (`core/llm_client.py`: `JsonChat` + `OpenAIJsonChat` + `AnthropicJsonChat`). Os hats não foram duplicados — `core/llm_anthropic.py` só injeta o transporte Anthropic (tool_use forçado, `claude-sonnet-4-6`). ~50 linhas, não 4-6h. |
| 02 | `edit_entity` permite rename silencioso (chave ≠ `name`) | High | `PATCH /entities/{id}` rejeita com 422 se `payload.name != id` (rename = delete + create). |
| 04 | `IncrementalSimRunner` grava `actor="user"` sempre | High | `run(actor=...)` (default `"user"`); atribuição correta propagável. |

### FASE 2 — robustez / performance

| # | Finding | Fix |
|---|---|---|
| 06/07 | `EventLog.read`/`head` re-parseiam o log inteiro (O(N²)) | Cache de parse por `scenario_id` invalidado por tamanho de arquivo (append-only ⇒ correto). Uma parse por escrita, não por leitura. |
| 08 | Payload parcial do Iterator rejeitado | `_iterate` faz merge do delta sobre a entidade atual antes de validar; `after` guarda o payload completo mesclado. |
| 10 | Prompt injection via `brief`/`name` | `brief` capado (`max_length=500`); input do usuário embrulhado em `<user_brief>` + instrução "data, not instructions" nos prompts do Designer e Iterator. |
| 11 | Símbolo privado `_valid_payload` importado | Renomeado para `is_valid_payload` (público); callers atualizados. |

## Configuração de deploy (env vars)

```bash
BALANCE_API_KEY=<token forte>              # exige X-API-Key nas escritas
ALLOWED_ORIGINS=https://<app>.vercel.app   # CORS allow-list (vírgula separa múltiplas)
WRITE_RATE_LIMIT_PER_MIN=60                # rate limit por IP nas escritas
LLM_BACKEND=anthropic                      # produção (LLM local não é acessível de nuvem)
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-6
```

Sem `BALANCE_API_KEY` o servidor sobe em **modo dev** (escritas abertas) e loga
`⚠ running without API key auth (dev mode)`. **Nunca deployar público sem setar a key.**

## O que fica pendente (não bloqueia deploy)

- **Multi-tenancy real:** o design é single-tenant. Dois humanos no mesmo deploy compartilham
  namespace de cenários. Segregação por `user_id` no path/token é trabalho futuro (audit #03,
  médio prazo).
- **Actor "engine" dedicado:** a fase `simulate` disparada pelo auto-loop ainda é atribuída a
  `user` por default (o enum de actor não tem valor "engine"/"system"). O parâmetro existe;
  só falta um tipo de actor. Não afeta a guardrail de authorship.
- **Índice em disco pro event log:** o cache de parse resolve o O(N²) dentro de um processo;
  para históricos muito grandes (>10k eventos) um índice `events.idx` seria o próximo passo.
- **Fixes Low (backlog):** paths `/tmp` hardcoded (audit #12), dependências mortas
  `sqlalchemy/alembic/tiktoken` (audit #13).

## Verificação

- `pytest` inteiro **verde** (216 testes; +25 novos: paths, auth, identity, actor, payload
  parcial, transporte Anthropic).
- `ruff check` limpo.
- Custo: **$0** — nenhum fix precisou de LLM real.
