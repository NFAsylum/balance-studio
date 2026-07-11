# Deploy — Balance Studio

Backend (FastAPI) → **Fly.io**; frontend (Next.js) → **Vercel**. Arquivos prontos:
`Dockerfile` + `.dockerignore` + `fly.toml` (raiz), `ui/vercel.json`, e este guia.

> **Não testado com build local** — o sandbox de dev não tem Docker. Os arquivos seguem os
> padrões do Fly/Vercel; valide o `docker build` na primeira execução.

## 0. Decisões antes de subir

- **LLM em prod (`LLM_BACKEND`):**
  - `fake` — funciona sem infra (Designer/Judge/Iterator determinísticos). Bom pra demo da
    UI/fluxo, sem qualidade de LLM real.
  - `local` — precisa que o `llama-server` (`LOCAL_LLM_URL`) seja **alcançável da nuvem**. O
    servidor atual está numa rede privada (`192.168.3.92`). Opções: expor via túnel
    (cloudflared/ngrok) ou VPS com GPU; então `fly secrets set LOCAL_LLM_URL=https://...`.
- **Cache (`CACHE_BACKEND`):** `redis` (recomendado em prod) ou `disk` (usa o volume Fly).

## 1. Backend no Fly.io

```bash
# a partir da raiz do repo (onde estão Dockerfile e fly.toml)
fly auth login
fly launch --no-deploy --copy-config --name balance-studio-api   # revisa/gera o app
fly volumes create balance_data --size 1 --region gru             # event log + snapshots

# Redis gerenciado (Upstash via Fly) — anota a URL que ele imprime:
fly redis create                                                  # -> redis://...
fly secrets set REDIS_URL="redis://default:...@...upstash.io:6379"

# (opcional) LLM local acessível publicamente:
# fly secrets set LLM_BACKEND=local LOCAL_LLM_URL="https://seu-endpoint/v1"

fly deploy
fly open        # abre a URL pública -> anota pro NEXT_PUBLIC_API_URL
```

Smoke pós-deploy:
```bash
curl https://balance-studio-api.fly.dev/domains
curl -X POST https://balance-studio-api.fly.dev/scenarios \
  -H 'Content-Type: application/json' \
  -d '{"domain":"card_game","name":"prod smoke","brief":"aggro","n_entities":5}'
```

## 2. Frontend no Vercel

O projeto Next fica em `ui/`. No dashboard da Vercel (ou `vercel` CLI):

- **Root Directory:** `ui`
- **Framework:** Next.js (auto-detectado; `ui/vercel.json` reforça `pnpm`)
- **Environment Variable:** `NEXT_PUBLIC_API_URL = https://balance-studio-api.fly.dev`

```bash
cd ui
vercel                       # primeira vez: linka o projeto (Root Directory = ui)
vercel env add NEXT_PUBLIC_API_URL production   # cola a URL do Fly
vercel --prod
```

## 3. CORS

A API já libera CORS pra todas as origens (`api/main.py`). Pra prod mais restrito, troque
`allow_origins=["*"]` pela URL do Vercel.

## 4. Local production-like (opcional, precisa de Docker)

```bash
docker compose -f deploy/docker-compose.yml up --build   # backend + redis em :8000
# UI apontando pra ele:
cd ui && NEXT_PUBLIC_API_URL=http://localhost:8000 pnpm dev
```

## Notas

- **Sem camada SQL.** A persistência é file-based (event log + snapshots no volume `/data`).
  `DATABASE_URL` e os deps `sqlalchemy`/`alembic` são vestigiais do plano pré-pivot — não há
  migração Postgres a rodar. Remover os deps é uma limpeza opcional.
- **Volume = estado.** Os cenários vivem no volume `balance_data`. Backup: `fly ssh console`
  + `tar` de `/data/scenarios`, ou snapshots de volume do Fly.
