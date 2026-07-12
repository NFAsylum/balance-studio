# INBOX — 2026-07-12 (Balance Studio)

Após executar, mova pra `docs/inbox-archive/2026-07-12-*.md` ou apague.

## Task 1: split de `api/main.py` (~1h)

Arquivo atualmente com 398 LOC concentrando todos os endpoints. Refactor em routers por domínio:

```
api/
├── main.py                    # app + middleware + include_router — <50 LOC
├── routers/
│   ├── __init__.py
│   ├── domains.py             # /domains/{name}/schema, /metrics, /generate, /simulate
│   ├── scenarios.py           # /scenarios (CRUD + iterate)
│   ├── branches.py            # /scenarios/{id}/branches (create, diff)
│   ├── entities.py            # /scenarios/{id}/entities (CRUD)
│   └── health.py              # /health
└── dependencies.py            # shared deps (get_registry, api_key auth, rate limiter)
```

**Regras:**
- `main.py` fica só com criação da app + `add_middleware` (CORS, auth, rate limit) + `include_router` das 5 subrotas
- Cada router usa `APIRouter(prefix=..., tags=[...])`
- Deps compartilhadas (`Depends(get_registry)`, auth middleware) ficam em `api/dependencies.py`
- Nenhum path muda — clientes externos não veem diferença
- Backward compat total: mesmos endpoints, mesmos schemas, mesmos status codes

**DoD:**
- `main.py` <50 LOC
- Cada router <150 LOC
- `pytest tests/test_api_scenarios.py tests/test_api_simulate.py` verde sem edição
- Ruff limpo
- `curl http://localhost:8000/health` retorna 200
- Commit único: `refactor: split api/main.py into routers by domain`

## Task 2: cleanup de fixes Low do audit (~30min)

Três fixes Low do `docs/audit/README.md` ainda pendentes. Endereçar tudo num commit só.

**F1.a — dead deps** (audit #13):
Remover de `pyproject.toml`:
- `sqlalchemy` — projeto não usa SQL
- `alembic` — sem migrations
- `tiktoken` — não usado no código

Depois `poetry lock && poetry install`. `pytest` deve continuar verde.

**F1.b — paths `/tmp` hardcoded** (audit #12):
Substituir em `scripts/experiment_balance.py` e `scripts/experiment_b6.py`:
```python
# de:
tmp_dir = "/tmp/experiment"

# pra:
import tempfile
tmp_dir = os.path.join(tempfile.gettempdir(), "experiment")
```
Ou usar `Path(tempfile.gettempdir()) / "experiment"`.

**F1.c — mistura pt/en na UI** (audit #14):
Padronizar TODAS as strings visíveis da UI em **inglês**. Comentários no código podem ficar em português. Log messages backend padronizar em inglês também. Escopo:
- `ui/src/**/*.tsx` — todo texto visível
- `api/` — mensagens de erro visíveis (raise, HTTPException detail)
- `core/` — logs de info/warn/error

Se houver arquivo de i18n (`src/lib/i18n.ts` ou similar), aproveitar. Se não, hardcode em inglês por agora — i18n vira issue futuro.

**DoD:**
- `pyproject.toml` não menciona sqlalchemy/alembic/tiktoken
- `poetry install` limpa; `pytest` verde
- `grep -rE "/tmp/" scripts/` retorna vazio
- `pnpm build` na UI passa; texto visível é inglês
- Commit: `chore: audit cleanup — dead deps, /tmp paths, UI language`

## Task 3: resolver `docs/inbox.md` (~5min)

Mesma coisa do Storyteller: mover pra `docs/inbox-archive/2026-07-12-splits-and-cleanup.md`, adicionar `/docs/inbox.md` ao `.gitignore`.

**DoD:**
- Arquivo movido pra archive
- `.gitignore` inclui a linha
- `git status` limpo

## Ordem

1 → 2 → 3. Após tudo, avisa no próximo prompt que está pronto pra push.
