# INBOX — 2026-07-14 (Balance Studio — /health + model status display)

Após executar, mova pra `docs/inbox-archive/2026-07-14-status-display.md`.

## Status

- 🆕 **T-STATUS.1** — endpoint `/health` + chip visual de backend/modelo

## Contexto

Marco quer signal de "product-grade" nos dois projetos portfolio. Balance atualmente **não tem `/health` endpoint** — `curl /health` retorna 404. Storyteller tem `/health` estruturado com `backend_llm` field.

**Decisão de 2026-07-14**: implementar **Option A do comparativo** (status display only, sem UI de troca). Padroniza com Storyteller. Zero UX de switching agora — só transparência de "estou usando modelo X via backend Y". Complexidade baixa, signal alto.

## Red lines

- ❌ **`git rebase` proibido.** Use merge.
- ❌ **Sem force push, sem history rewrite.**
- ❌ **Não postar review/comentário/PR no GitHub sem confirmação humana.**
- ❌ **Não mexer em `docker/.env`.**

## T-STATUS.1 [4-5h] — `/health` + backend/modelo display

### Contexto técnico específico

**Como Balance escolhe modelo hoje** (verificado em `core/llm_client.py:45`):
```python
self._transport: JsonChat = transport or OpenAIJsonChat(client=client, model=model)
```

Model vem via constructor arg, ou vazio se não passado. Backend selection via env `LLM_BACKEND=fake|anthropic|local` no `.env`.

**MAS**: llama.cpp/llama-server é permissivo — se você pedir modelo X mas ele só tem Y carregado, ele serve Y sem erro. Env config é *hint*, não verdade. Pra status **real**, precisa consultar `GET http://192.168.3.92:8080/v1/models` e mostrar o que llama-server tem ativo.

### Escopo

**Backend**:

1. **Novo endpoint `/health`** em `api/routers/health.py` (o arquivo existe mas retorna trivial `{"status":"ok"}` — expandir):
   ```json
   {
     "status": "ok",
     "backend_llm": "local",
     "llm_model": "qwen2.5-coder-7b",
     "domains_loaded": ["card_game", "creature_rpg", "team_composition"],
     "event_log_ready": true
   }
   ```
   - `backend_llm`: valor do env `LLM_BACKEND` (default `"fake"`)
   - `llm_model`: modelo real detectado (ver detecção abaixo) ou `"fake"` se backend é fake
   - `domains_loaded`: from `services.registry.names()`
   - `event_log_ready`: verifica se `services.event_log` foi inicializado

2. Função `_detect_local_model()` em `core/llm_local.py` (ou lugar equivalente):
   - Faz `GET {LOCAL_LLM_URL}/v1/models` com timeout 2s
   - Retorna primeiro model id da lista (ou None se falha)
   - Cachear resultado por 30s (evita chamada por request)

3. `/health` chama detecção conforme backend:
   - Backend `fake` → `llm_model: "fake"`
   - Backend `local` → chama `_detect_local_model()`; se falhar, `"local-unreachable"`
   - Backend `anthropic` → `llm_model` = env `ANTHROPIC_MODEL` ou `"claude-sonnet-4-6"`

**Frontend**:

4. Component novo `<ModelStatusChip />` (em `ui/src/components/model-status-chip.tsx`):
   - Query `/health` via react-query (cache 30s, staleTime alto)
   - Renderiza chip pequeno: `[backend · model]` — ex: `[local · qwen2.5-coder-7b]`
   - Cor por backend: local = amber, anthropic = green, fake = gray
   - Tooltip on hover: "Backend LLM: local · Model: qwen2.5-coder-7b · Para trocar: edite `.env` e reinicie"
   - Loading state: `[carregando…]`
   - Error state (backend não responde): `[backend offline]`

5. Wire no header da app (`ui/src/app/layout.tsx` ou `ui/src/components/AppHeader.tsx` — investigue o padrão real do repo). Lado direito do header, visível em todas as páginas.

### DoD

- `curl http://localhost:8000/health` retorna 200 com JSON do formato acima
- `llm_model` detectado corretamente (local com llama-server ativo → nome real; fake → "fake"; local com llama offline → "local-unreachable")
- Cache 30s implementado (chama llama-server no máximo 1x por 30s)
- Timeout de 2s previne backend hang
- Chip aparece no header em qualquer página
- `pytest tests/` inteiro verde
- Teste novo `tests/test_api_health.py` cobrindo: retorno com backend fake, retorno com backend local ativo (mock llama-server), retorno com backend local unreachable
- Vitest test do `ModelStatusChip` cobrindo: loading, success, error

### Verificação manual

- Backend em `LLM_BACKEND=local` + llama-server ativo → chip mostra `[local · qwen2.5-coder-7b]`
- Backend em `LLM_BACKEND=local` + llama-server offline → chip mostra `[local · local-unreachable]` (amber)
- Backend em `LLM_BACKEND=fake` → chip mostra `[fake · fake]` (gray)
- Chip persiste ao navegar entre scenarios/history/branches

### Se travar

- Se o roteador health atual tem estrutura de dependency injection não trivial: siga o padrão do `scenarios.py` (usa `services` global via `dependencies.py`)
- Se a detecção assíncrona conflita com response sync: use `httpx.Client` sync em thread; não precisa async por causa disso
- Se cache dá race condition: `functools.lru_cache` com `maxsize=1` + timer manual. Não overengineer.

## Diretiva sobre escopo

Executar T-STATUS.1 sozinho. Não mexer em:
- Model switching UI (Option B — fora de escopo)
- Scenario-level LLM config
- Env config UX

Se qualquer coisa parecer que precisa expandir escopo: **escale**.

## Depois de tudo verde

1. `git push` da branch `dev-marco-status-display`
2. Abrir PR: `feat: /health endpoint + model status chip (T-STATUS.1)`
3. Body: menciona Option A do comparativo backend/model, escreve trade-off "hint vs verdade" (env vs llama-server actual), inclui screenshot do chip em cada estado, screenshot do `/health` JSON
4. **Aguardar autorização humana** pra merge

Reporte no próximo prompt:
- SHA do commit
- Screenshot do chip em cada estado
- Confirmação de DoD verde
