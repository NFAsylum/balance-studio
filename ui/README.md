# Balance Studio — UI

Next.js 15 (App Router) + Tailwind v3 + shadcn-style components (Radix) + Tanstack Query +
Recharts. Tests: Vitest + Testing Library (jsdom).

## Rodar

```bash
cd ui
pnpm install
pnpm dev        # http://localhost:3000
pnpm build      # production build + type-check
pnpm test       # Vitest
```

O backend deve estar rodando (`poetry run uvicorn api.main:app --port 8000`). A UI lê a base
da API de `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).

## Notas de ambiente (dev container)

Sem `pnpm` global? Use corepack: `corepack pnpm ...` (ou um shim `pnpm -> corepack pnpm`).
Se `pnpm install`/`pnpm test` reclamarem de build scripts (`esbuild`/`sharp`), o
`pnpm-workspace.yaml` já traz `onlyBuiltDependencies` + `verifyDepsBeforeRun: false`. Aponte
os caches pra um dir gravável se `~/.npm`/`~/.local` não forem:
`NPM_CONFIG_CACHE`, `PNPM_HOME`, `COREPACK_HOME`.

## Estrutura

- `src/app/` — rotas (home, `scenarios/[id]`, `/history`, `/branches`)
- `src/components/ui/` — componentes shadcn-style (Button, Card, Input, Select, Tabs, Slider, Dialog)
- `src/lib/api.ts` — client da API
