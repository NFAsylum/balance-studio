# Tasks — Balance Studio

Formato: `[ ]` pendente, `[x]` feita. Nunca marcar feita se DoD não é 100% verificável. Nunca continuar próximo sprint sem "verificação final" do anterior aprovada.

Total: 200 h realista. Ordem sequencial entre sprints; dentro do sprint, algumas tarefas podem paralelizar (indicado).

---

## Sprint 1 — Core do framework (20 h)

Sem domínios ainda. Só framework.

### [x] B1.1 — Setup do projeto (3 h) — spec revisada (SQLite + diskcache) aplicada
Poetry, FastAPI, dependencies, `.env.example`. **SQLite** pro dev + **`diskcache`** pra cache. Migração pra Postgres + Redis fica pro Sprint 7 (deploy).
**Retrabalho feito:**
- Removidos `psycopg2-binary` e `redis` do `pyproject.toml`
- Adicionado `diskcache = "^5.6.0"` ao `pyproject.toml`
- Deletado `docker-compose.yml`
- `.env.example` atualizado (SQLite + CACHE_DIR)
- `poetry lock && poetry sync` (lock regenerado, venv limpo)
**DoD:** (todos verificados programaticamente)
- `poetry install` sem erro ✅
- `poetry run pytest` executa (0 testes ainda, exit 5 é ok) ✅
- `.env.example` lista `ANTHROPIC_API_KEY`, `DATABASE_URL=sqlite:///./balance_studio.db`, `CACHE_DIR=./.diskcache` ✅
- Nenhum `docker-compose.yml` no repo (grep verifica) ✅
- `psycopg2-binary` e `redis` **não** aparecem no `pyproject.toml` ✅ (nem no `poetry.lock`)

### [x] B1.2 — `core/entity_schema.py` (5 h)
DSL declarativa: dict → Pydantic model dinâmico + JSON schema pra LLM tool_use.
**DoD:**
- `EntitySchema.from_dict({...}).build_model()` retorna classe Pydantic funcional
- `.to_llm_schema()` retorna dict válido no formato Anthropic tool_use
- Tipos suportados: `num` (com range), `cat` (com enum), `bool`, `tag_set`
- 5 testes cobrem cada tipo + campos inválidos + geração de tool_use schema
- `pytest tests/test_entity_schema.py` verde

### [x] B1.2.1 — Adicionar kind `str` ao FieldSpec (1 h, follow-up de B2.1 blocker)
Lacuna descoberta durante B2.1: campos free-form (Unit.name, Creature.name, Person.name) não têm kind válido. Solução: novo kind `str` com `min_len`/`max_len` opcionais. Ver `docs/architecture.md#core` para spec completa.
**DoD:**
- `FieldSpec.kind` inclui `"str"` no Literal
- `FieldSpec` ganha campos opcionais `min_len: int | None`, `max_len: int | None`
- `build_model()` gera Pydantic `str` field com `Field(min_length=..., max_length=...)`
- `to_llm_schema()` emite `{"type": "string", "minLength": ..., "maxLength": ...}` quando presentes
- 3 novos testes: str sem constraints, str com min/max, str inválido (violates min_len)
- `pytest tests/test_entity_schema.py` continua verde (5 originais + 3 novos = 8)
- **Não** aceitar `cat` sem enum como fallback — regressão silenciosa. Levantar erro claro se `cat` sem `enum`.

### [x] B1.3 — `core/constraint_engine.py` (4 h)
Valida entidades contra constraints declarativas.
**DoD:**
- 5 kinds implementados: `range`, `sum_of_fields`, `forbidden_combo`, `required_tag`, `unique_across_set`
- `ConstraintEngine.validate(entity, constraints)` retorna `ValidationResult` com `is_valid`, `violations: list[str]`
- 8 testes: cada kind com happy path + edge case
- `pytest tests/test_constraint_engine.py` verde

### [x] B1.4 — `core/simulator_interface.py` ABC (2 h)
ABC pura, sem implementação. Só define contrato.
**DoD:**
- `SimulatorInterface`, `RunResult`, `Environment` classes definidas
- Docstring completa em cada método abstrato
- `tests/test_simulator_interface.py` verifica que instanciação direta levanta `TypeError`

### [x] B1.5 — Métricas genéricas: rating + distribution + aggregators (6 h)
`core/metrics/base.py`, `rating.py` (Elo-MMR), `distribution.py`, `aggregators.py`.
**DoD:**
- `Metric` ABC + 3 implementações concretas
- `EloMmrRating.compute(runs)` retorna `dict[entity_id → rating_float]`; testado com 100 runs sintéticos
- `WinRateDistribution.compute(runs)` retorna `mean`, `std`, `outliers`
- Métricas são **domain-agnostic** — não podem importar de `domains/*`
- 6 testes; `pytest tests/test_metrics.py` verde

### Verificação final Sprint 1
- [x] `pytest` inteiro verde (37 testes)
- [x] Nenhum import de `domains.*` em `core/`
- [x] `poetry run python -c "from core import entity_schema, constraint_engine, simulator_interface, metrics"` sucede

---

## Sprint 2 — Card game plugin + LLM generator (20 h) — CHECKPOINT 40h

### [x] B2.1 — `domains/card_game/schema.py` (3 h)
Define `Unit`, `Ability`, `Deck` via `EntitySchema`.
**DoD:**
- `get_schema()` retorna `EntitySchema` para `Unit`
- Campos: `name` (cat/free-string), `cost` (num 1-5), `hp` (num 1-20), `damage` (num 1-10), `ability_kind` (cat), `ability_value` (num)
- Load `domains/card_game/seed_data.json` com 10 unidades e validar todas — `pytest tests/test_card_schema.py` verde

### [x] B2.2 — `domains/card_game/simulator.py` (6 h)
Turn-based combat 1v1, seeded RNG, retorna `RunResult`.
**DoD:**
- `CardGameSimulator().run(entities=[deck_a, deck_b], env=MatchEnv(seed=42))` roda
- Mesma seed produz mesmo resultado (5 execuções, mesma seed, mesmo winner + mesmo turn count)
- Regras: mana cresce por turno, hand size 5, abilities executam em order de play, HP zero = remove
- 4 abilities: `deal_damage`, `heal`, `shield`, `draw`
- `pytest tests/test_card_simulator.py` cobre determinism, cada ability, edge case de empate

### [ ] B2.3 — `core/llm_generator.py` (6 h)
Gera candidatos via `tool_use` estruturado, retry com feedback em erro.
**DoD:**
- `LlmGenerator(client, schema).generate(n=3, constraints=[...])` retorna 3 entidades Pydantic válidas
- Retry: se LLM retorna dados que falham validação, próxima chamada inclui erro no prompt
- Max 3 retries por batch
- Constraint violations pós-geração são filtradas (retorna só válidas + logs os inválidos)
- Teste com Anthropic mockado: 1º call retorna dados inválidos, 2º retorna válidos, resultado tem 3 entidades

### [ ] B2.4 — Endpoint `POST /domains/{name}/simulate` (5 h)
Rota agnóstica. Registry carrega `domains/card_game` no startup.
**DoD:**
- `POST /domains/card_game/simulate` com body `{entities: [...], env: {...}, n_runs: 10}` retorna `Report`
- Registry auto-descobre domínios em `domains/` (import de `__init__.py`)
- Erro 404 pra domain não registrado
- Erro 422 pra body inválido
- `pytest tests/test_api_simulate.py` cobre happy path + erros

### Verificação final Sprint 2 (CHECKPOINT 40 h)
- [ ] Rodar end-to-end via curl:
  ```bash
  curl -X POST http://localhost:8000/domains/card_game/generate \
    -H "Content-Type: application/json" \
    -d '{"n": 5, "constraints": [], "user_intent": "aggro deck with low-cost units"}'
  ```
- [ ] Rodar simulate com output do generate; recebe Report com métricas
- [ ] **CRÍTICO:** se aqui falha, **para e escala pro humano**. Cenário pessimista ativado. Decisão: cortar escopo (só card game, sem creature RPG) ou aceitar prazo maior.

---

## Sprint 3 — Creature RPG plugin (escala) (20 h)

### [ ] B3.1 — `domains/creature_rpg/schema.py` (4 h)
`Creature` (name, type, hp, atk, def_, skills[], resistances{}), `Skill`, `Type` enum.
**DoD:**
- 200 creatures seed em `domains/creature_rpg/seed_data.json`, distribuídas em 8 tipos
- Cada creature tem 2-4 skills
- Load em <2s: `pytest tests/test_creature_load.py -k test_load_perf`
- Todas validam via schema

### [ ] B3.2 — `domains/creature_rpg/simulator.py` (8 h)
Gauntlet mode + tournament mode.
**DoD:**
- Gauntlet: `Creature` vs random N adversários, retorna estatísticas
- Tournament: round-robin em subset de creatures, retorna resultados
- Type matchup table (fogo > gelo > planta > água > fogo etc.), pluginável via JSON
- Ability queue com priority + cooldown
- Determinismo com seed
- 6 testes cobrem cada modo + edge cases

### [ ] B3.3 — Métricas RPG (4 h)
`TierEmergence`, `DominanceIndex`, `UsageCoverage`.
**DoD:**
- `TierEmergence`: agrupa creatures por rating em tiers S/A/B/C/D, retorna dict
- `DominanceIndex`: fração de matches em que a top-5% ganha
- `UsageCoverage`: quantas creatures aparecem em pelo menos M matches
- Métricas usam base `Metric` do core, não hardcodam nada de creature
- `pytest tests/test_creature_metrics.py` verde

### [ ] B3.4 — Otimização de performance (4 h)
Paralelizar simulações via `concurrent.futures.ThreadPoolExecutor`. Cache via **`diskcache`** (dev; Redis na prod, mesma interface).
**DoD:**
- Criar abstração `core/cache_backend.py` com `CacheBackend` protocol e impl `DiskCacheBackend`
- 200 creatures × 1000 gauntlet matches em <60s (medido)
- Cache: chave = `sha256(entities_json + env_json + seed)`, TTL 24h
- Cache hit em request repetido: <100ms (medido)
- `pytest tests/test_performance.py` bench
- `pytest tests/test_cache_backend.py` valida contract do protocol (mesmo teste rodará depois com Redis)

### Verificação final Sprint 3
- [ ] Rodar `POST /domains/creature_rpg/simulate` com 200 creatures, 1000 matches
- [ ] Report retorna com tier list + rating + dominance
- [ ] Segunda chamada idêntica em <200ms (cache hit)

---

## Sprint 4 — UI genérica (20 h)

### [ ] B4.1 — Setup Next.js 15 + shadcn/ui + estrutura (4 h)
**DoD:**
- `pnpm dev` roda em http://localhost:3000
- shadcn/ui instalado + `<Button>`, `<Card>`, `<Input>`, `<Select>`, `<Tabs>` funcionais
- Estrutura de rotas conforme `docs/architecture.md`
- Domain picker (home) lista domains fetchados de `GET /domains`

### [ ] B4.2 — `<EntityEditor>` genérico (8 h)
Renderiza form a partir de `EntitySchema`.
**DoD:**
- Recebe `schema: EntitySchema` (JSON) e `value` inicial; emit `onChange`
- Renderiza: input pra num (com slider se tem range), select pra cat, checkbox pra bool, tag input pra tag_set
- Ambos domains (card + creature) usam o **mesmo componente** — testado manualmente com 2 schemas
- Validação inline: mostra erro quando valor sai do range
- Vitest: 5 testes

### [ ] B4.3 — Dashboard de resultados genérico (6 h)
Métricas → cards. Distributions → histograms. Ratings → bar chart / tier list.
**DoD:**
- `<MetricCard>` renderiza qualquer `MetricResult` baseado em `.kind`
- `<DistributionChart>` (Recharts) plota histograma
- `<RatingBarChart>` mostra ratings ordenados
- Card game e creature RPG renderizam **sem componente específico** por default

### [ ] B4.4 — View domain-specific opcional (heatmap card game) (2 h)
**DoD:**
- `domains/<name>/ui/` (frontend side) pode registrar componente custom
- Card game registra `<MatchupHeatmap>` — mostrado quando disponível, senão fallback pro genérico
- Creature RPG **não** registra, usa view padrão

### Verificação final Sprint 4
- [ ] Navegar UI: home → card game editor → simulate → results
- [ ] Repetir pra creature RPG
- [ ] Screenshot dos dois dashboards no `README.md`

---

## Sprint 5 — Team composition + polish + docs (20 h)

### [ ] B5.1 — `domains/team_composition/schema.py` (3 h)
`Person(name, seniority, skills[], preferred_task_types[])`, `TaskType`.
**DoD:**
- Seed com 50 pessoas, 20 task types
- Schema valida seed

### [ ] B5.2 — `domains/team_composition/simulator.py` (8 h)
Modelo probabilístico de completion.
**DoD:**
- `WorkloadEnv(tasks, deadline_days, seed)` define workload
- Simulator retorna: task completion rate, average time, blocked tasks
- Seeded determinism
- 5 testes de comportamento (todos experts fazem tudo, todos juniors fazem pouco, mismatched skills falha, etc.)

### [ ] B5.3 — Métricas team (3 h)
`SkillCoverage`, `Redundancy`, `SinglePointOfFailure`.
**DoD:**
- Métricas usam base `Metric` do core
- Dashboard renderiza team results **sem código extra na UI** (usa componentes genéricos)

### [ ] B5.4 — `docs/writing-a-domain.md` — tutorial (6 h)
Passo a passo pra criar novo domain.
**DoD:**
- Seção "10 minute quickstart" com exemplo minimal
- Seção "full example" walking pelo team_composition
- Seção "checklist" antes de PR
- Leitor externo consegue esboçar um domain trivial em <2h seguindo o doc (validar informalmente)

### Verificação final Sprint 5
- [ ] 3 domains listados na home, todos rodam
- [ ] Tutorial pronto e revisado

---

## Sprint 6 — Iteração LLM + performance (20 h)

### [ ] B6.1 — Bateria de teste real: 10 balanceamentos por domain (4 h)
Rodar 10 fluxos "usuário define constraint → LLM gera → simula → interpreta".
**DoD:**
- 10 sessions salvas em Postgres (`experiments` tabela)
- Log estruturado de falhas: prompt inputs, LLM output, erro
- Documentar padrões em `docs/experiments.md`

### [ ] B6.2 — Prompt tuning por domain (6 h)
Adicionar few-shot examples de sucesso no prompt de cada domain.
**DoD:**
- Sucesso rate (fração de generates que produzem constraint-satisfying entities) >80% no card game
- >70% no creature RPG (constraints maiores)
- Tabela de resultados em `docs/experiments.md`

### [ ] B6.3 — Cache agressivo no LLM generator (4 h)
**DoD:**
- Cache também no LLM generator (`sha256(prompt + constraints + intent) → entities`)
- Reusa `CacheBackend` do B3.4 (mesma abstração)
- Hit rate >50% durante uso normal (medido em 10 sessions repetidas com pequenas variações)

### [ ] B6.4 — Progress streaming na UI (4 h)
**DoD:**
- `POST /simulate` retorna Server-Sent Events com progress
- UI mostra progress bar em tempo real (`400 of 1000 runs`)
- Cancelamento funcional

### [ ] B6.5 — Custo visível (2 h)
**DoD:**
- Chip "$0.XX gasto nesta sessão" no header da UI, atualiza após cada LLM call
- Custo persistido em Postgres por experiment

### Verificação final Sprint 6
- [ ] 10 balanceamentos rodam end-to-end sem falha grave
- [ ] Métricas de sucesso do LLM registradas
- [ ] Cache hit rate documentado

---

## Sprint 7 — Deploy + writeup (20 h)

### [ ] B7.1 — Deploy Fly.io + Vercel + migração de infra (6 h, era 4)
Momento planejado de trocar SQLite → Postgres e `diskcache` → Redis.
**DoD:**
- Provisionar Fly Postgres + Fly Redis (upstash) via `flyctl`
- Implementar `RedisCacheBackend` (subclasse do `CacheBackend` protocol) — passa o mesmo `test_cache_backend.py`
- `DATABASE_URL` em prod aponta pra Postgres; local segue SQLite via `.env`
- Rodar `alembic upgrade head` contra Postgres remoto — schema portável desde B2.1
- Smoke test: gerar 3 cartas via LLM, simular, cache hit numa segunda chamada
- API + Postgres + Redis no Fly.io
- Frontend no Vercel
- Secrets via `fly secrets` e Vercel env vars
- URL público funcional

### [ ] B7.2 — Seed data polida (3 h)
Card (10 unidades diversas), creature (200 balanceadas em tiers), team (50 diversos).
**DoD:**
- Cada domain tem seed que dá pra demonstrar imediatamente
- Documentado no `docs/writing-a-domain.md`

### [ ] B7.3 — README (5 h)
**DoD:**
- Problema geral (balance é problema comum)
- Arquitetura de plugin (diagrama)
- 3 casos de uso com screenshot
- Tutorial de extensão (link)
- Como rodar local + deployado
- Números de performance
- Reader externo entende em 5 min de leitura

### [ ] B7.4 — Demo video 4 min (4 h)
Roteiro: card game (simulate + heatmap) → troca pra creature RPG (mesma UI, dados diferentes) → mostra tier list → abre `docs/writing-a-domain.md` e mostra que team_composition virou 3º domain com 200 linhas.

### [ ] B7.5 — Post técnico (4 h)
Medium/dev.to. "Framework de balance com LLM: 3 domínios, 1 core". 500-800 palavras.
**DoD:**
- Rascunho revisado
- Publicado, link no README

---

## Estimativas resumidas

| Sprint | Total | Cumulativo | Nota |
|---|---:|---:|---|
| 1 | 20 h | 20 h | Core sem domínios |
| 2 | 20 h | 40 h | CHECKPOINT — end-to-end card game |
| 3 | 20 h | 60 h | Creature RPG (prova de escala) |
| 4 | 20 h | 80 h | UI genérica |
| 5 | 20 h | 100 h | Team + tutorial de extensão |
| 6 | 20 h | 120 h | Iteração LLM + performance |
| 7 | 20 h | 140 h | Deploy + demo + post |

**Total realista: ~140 h** (revisão pra baixo vs 200 h anterior — o plano mais estruturado corta buffer).

Se apertado no calendário, cortar Sprint 5 (team composition + tutorial doc) — pode virar issue follow-up, deixando 120h.
