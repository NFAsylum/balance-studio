# CORS `allow_origins=["*"]` + endpoints de escrita sem autenticação

**Severity:** High
**Priority:** P1
**Category:** Security
**Source:** `api/main.py:68-74`, `deploy/README.md:62-64`

## Descrição

```python
# api/main.py:68-74
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

O deploy README reconhece: "A API já libera CORS pra todas as origens. Pra prod mais
restrito, troque `allow_origins=["*"]` pela URL do Vercel." — mas até então o `fly.toml`
sobe com esse valor.

Não há **nenhuma** camada de autenticação (nenhum `Depends(oauth2_scheme)`, nenhum header
API-key checado, nenhum middleware de auth). Todos os endpoints — incluindo POST/PATCH/DELETE
que alteram estado — são anônimos.

Combinado com o path traversal do finding #01, qualquer site na web pode:

1. Chamar `POST /scenarios` (cria arquivo em disk).
2. Chamar `POST /scenarios/{sid}/iterate` (dispara Iterator LLM — custa dinheiro se rodar
   backend `local` via API paga ou disparar `NotImplementedError` no `anthropic`).
3. Chamar `DELETE /scenarios/{sid}/entities/{eid}` (destrói dados).
4. Ler event log completo via `GET /scenarios/{sid}/history` sem restrição.

## Risco

- **DoS trivial** disparando `iterate` em loop (o Iterator local + IncrementalSimRunner
  executam simulação pesada; sem rate limit).
- **CSRF-like** — um site malicioso visitado por um usuário logado (nem tem login, mas
  qualquer cookie de sessão futuro) faz cross-origin write com `fetch(..., {mode: 'cors'})`.
- **Corrupção de dados de outros usuários** — o design é single-tenant, mas se dois humanos
  compartilham o Fly.io deploy eles pisam nos cenários um do outro. Path traversal (#01)
  ainda vaza entre "tenants" mesmo com sanitização de ID, porque não há segregação real.

## Fix sugerido

Curto prazo (P1, antes de deploy):

```python
# api/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("CORS_ORIGIN", "http://localhost:3000")],  # comma-split se >1
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
    allow_credentials=True,
)
```

E adicionar um `x-api-key` mínimo:

```python
_API_KEY = os.getenv("BALANCE_STUDIO_API_KEY")

def require_api_key(x_api_key: str = Header(...)) -> None:
    if _API_KEY and x_api_key != _API_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")

app = FastAPI(..., dependencies=[Depends(require_api_key)] if _API_KEY else [])
```

Médio prazo: multi-tenant real (namespace por user_id no path/token, `SCENARIOS_DIR/<user>/<sid>/`)
se o design comercial exigir.

## Referências

- FastAPI CORS docs: https://fastapi.tiangolo.com/tutorial/cors/
- OWASP: https://owasp.org/www-community/attacks/CORS_OriginHeaderScrutiny
