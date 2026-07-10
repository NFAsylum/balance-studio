# Balance Studio — Framework Genérico de Balanceamento com LLM

## Missão

Construir um **framework** (não um app) que resolve balance de qualquer domínio via plugins. Core cuida de schema de entidades, geração LLM, constraint validation, simulação, métricas, UI. Cada domínio pluga simulador + schema em ~200-500 linhas.

MVP entrega 2 domínios funcionais (card game + creature RPG) e 1 demo de extensibilidade (team composition). Projeto tocado como portfólio de TCC. Prazo ~7 semanas @ 20h/sem. Você (Claude) executa; o dev humano (marco) intervém em decisões de escopo e prompt tuning.

## Diferencial vs "balanceador de card game"

Um "balanceador de cartas" é software vertical. **Este é framework**. O contraste no portfólio é decisivo:
- Card game com 10 unidades? OK, resolve.
- RPG com 200 monstros? Mesma UI, muda o plugin.
- Distribuir produtos em corredores de supermercado? Novo plugin, mesmo core.
- Distribuir funcionários por times? Novo plugin, mesmo core.

Cada domínio novo custa horas de plugin, não semanas de reescrever tudo.

## Stack fixado

- Python 3.11 + Poetry + FastAPI + Pydantic v2 (schema-driven)
- **SQLite** (experimentos, dev) + **`diskcache`** (cache de simulação, dev)
- Anthropic SDK, modelo `claude-sonnet-4-6`, `tool_use` obrigatório
- Frontend: Next.js 15 + shadcn/ui + Recharts + Tanstack Query
- Deploy: Vercel (front) + Fly.io (back + Postgres + Redis)
- Testes: pytest (Python) + Vitest (frontend)

**Migração futura (Sprint 7, antes do polish final):** SQLite → Postgres, `diskcache` → Redis. Design assume `CacheBackend` como abstração desde o início — swap de impl é trivial. O motivo de SQLite+diskcache no dev é evitar overhead de infra pro Claude no container (sem docker-in-docker) e simplificar o setup do humano.

Não trocar sem justificativa forte + confirmação do humano.

## Layout do repo

```
balance-studio/
├── CLAUDE.md                       # este arquivo
├── docs/
│   ├── architecture.md             # core + plugin system
│   ├── tasks.md                    # sprints com definition of done
│   ├── prompts.md                  # templates LLM iteráveis
│   ├── writing-a-domain.md         # tutorial de plugin (deliverable)
│   └── experiments.md              # log de tuning, criado no Sprint 6
├── bootstrap.sh
├── pyproject.toml
├── docker-compose.yml              # Postgres + Redis
├── core/
│   ├── entity_schema.py
│   ├── constraint_engine.py
│   ├── llm_generator.py
│   ├── simulator_interface.py
│   ├── report_engine.py
│   └── metrics/
│       ├── base.py
│       ├── rating.py               # Elo-MMR
│       ├── distribution.py
│       └── aggregators.py
├── domains/                        # cada plugin autocontido
│   ├── card_game/
│   │   ├── schema.py
│   │   ├── simulator.py
│   │   ├── metrics.py
│   │   └── seed_data.json
│   ├── creature_rpg/
│   │   ├── schema.py
│   │   ├── simulator.py
│   │   ├── metrics.py
│   │   └── seed_data.json
│   └── team_composition/           # demo de extensibilidade
│       ├── schema.py
│       ├── simulator.py
│       ├── metrics.py
│       └── seed_data.json
├── api/                            # FastAPI
├── ui/                             # Next.js 15
├── tests/
└── deploy/
```

## Fluxo de trabalho por task

1. Ler `docs/tasks.md`, pegar próxima task pendente (checkbox `[ ]`)
2. Criar branch: `git checkout -b dev-marco-<sprint>-<task-id>` (ex: `dev-marco-b1-1.3`)
3. Implementar
4. Rodar: `pytest tests/` (Python) e/ou `npm test` (frontend) — todos verdes antes de continuar
5. Verificar Definition of Done da task; **cada critério tem que ser verificável programaticamente**
6. Commit: `git commit -m "B1.3: entity_schema DSL v1"` (sem menção a AI, sem emoji)
7. Marcar task como feita em `docs/tasks.md` (`[x]`)
8. Se DoD não é 100% verificável ou algo ficou pela metade: **NÃO marcar feita, escalar pro humano**

## Guardrails (rígidos)

- Nunca commit em `main` — sempre branch `dev-marco-*`
- Nunca `--no-verify` em hooks
- Nunca `git rebase` — use merge
- Nunca skip de teste sem justificativa em comentário
- Se estourar 30% da estimativa de uma task, **para e pergunta ao humano**
- Se DoD é vaga demais pra ser auto-verificável, **para e pergunta**
- Configurar git author antes do primeiro commit:
  ```bash
  git config user.name "NFAsylum"
  git config user.email "marcooinotna13@outlook.com"
  ```
- Nunca postar review/comentário no GitHub sem confirmação humana
- **Nunca hardcodar lógica de domínio no core**. Se algo é específico de card game, vai em `domains/card_game/`, ponto.

## Regras de arquitetura invioláveis

1. **Core não conhece domínios.** Se `core/*.py` importa qualquer coisa de `domains/*`, é bug. Core recebe interfaces (`SimulatorInterface`, `Metric`), não implementações concretas.
2. **Domain nunca modifica core.** Se um plugin novo precisa mudar core, é porque a interface está errada — para e pergunta em vez de contornar.
3. **Simulator é puro.** `Simulator.run(entities, env, seed)` é determinístico dado seed. Sem I/O, sem chamadas LLM dentro do runner.
4. **LLM é opcional.** O framework roda sem LLM — o usuário pode fornecer entities manualmente. LLM é gerador de candidatos, não parte crítica do loop.
5. **Cache é do core, não do domain.** Redis cache trata `(entity_set_hash, env_hash, seed)` de forma genérica.

## Quando escalar pro humano

- Decisão de escopo (adicionar/cortar feature)
- Prompt LLM não converge após 3 iterações
- Interface de plugin parece limitante — investigar se é redesign de interface
- Estimativa estourada em >30%
- API key faltando ou expirada
- Bug em dependência externa

## Sprint priority se token acabar

Se você (Claude) tem contexto limitado ou budget de token apertado:
1. **Sprints 1-2 são inegociáveis** — sem framework core e sem card game plugin end-to-end, não há nada demonstrável
2. **Sprint 3 (creature RPG) é o que vende escala** — priorizar sobre UI se precisar cortar
3. **Sprint 4-5 (UI + team domain)** é polish. Se cortar, cortar aqui, não em Sprint 3.

## Convenções

- Português em docs, comentários pro humano
- Inglês em código, docstrings, prompts LLM
- Não usar termos vagos ("objetos", "processa dados") — nomear tipos/classes específicos
- Reports usam formato "N of M"

## Referências rápidas

- `docs/architecture.md` — plugin system + interfaces
- `docs/tasks.md` — o que fazer agora
- `docs/prompts.md` — templates iniciais LLM
- `docs/writing-a-domain.md` — tutorial de plugin (também deliverable)
- Elo-MMR paper: https://cs.stanford.edu/people/paulliu/files/www-2021-elor.pdf
- RuleSmith (referência): https://arxiv.org/abs/2602.06232
- Anthropic tool_use: https://docs.claude.com/en/docs/tool-use
