# Tasks — Balance Studio

Formato: `[ ]` pendente, `[x]` feita. Nunca marcar feita se DoD não é 100% verificável. Nunca continuar próximo sprint sem "verificação final" do anterior aprovada.

**Total revisado: ~180 h.** Sprint 1 concluído. Sprints 2-8 reestruturados com base no modelo real do produto (colaboração fluida humano/LLM, event log, 3 hats de LLM, multi-objetivo, freshness em UI).

**Papel do LLM:** três protocols distintos, todos plugáveis com Fake (dev) e Anthropic (Sprint 6):
- `DesignerLlm` — brief em linguagem natural → entidades
- `SubjectiveJudgeLlm` — avaliação qualitativa (variedade, coesão, temática)
- `IteratorLlm` — dado estado + métricas + objetivos → propõe mudanças

**Modo de operação:** usuário e LLMs modificam o mesmo estado a qualquer momento. Sem fronteira modal. Cada mudança é evento append-only no `events.jsonl` do cenário. Snapshot a cada 50 eventos, comprimido zstd.

---

## Sprint 1 — Core do framework (20 h) — CONCLUÍDO

Sem domínios. Só framework.

### [x] B1.1 — Setup do projeto (3 h) — spec revisada (SQLite + diskcache) aplicada
Poetry, FastAPI, dependencies, `.env.example`. **SQLite** pro dev + **`diskcache`** pra cache. Migração pra Postgres + Redis fica pro Sprint 8 (deploy).
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

### [x] B1.2.1 — kind `str` no FieldSpec (1 h, follow-up)

### [x] B1.3 — `core/constraint_engine.py` (4 h)

### [x] B1.4 — `core/simulator_interface.py` ABC (2 h)

### [x] B1.5 — Métricas genéricas: rating + distribution + aggregators (6 h)

### Verificação final Sprint 1
- [x] `pytest` inteiro verde (37 testes)
- [x] Nenhum import de `domains.*` em `core/`
- [x] Import direto do core funciona

---

## Sprint 2 — Card game plugin + Scenario infra + LLM protocols (25 h)

Novo escopo — inclui infra de persistência de cenários (event log + snapshots) e protocols de LLM (mas só Fakes).

### [x] B2.1 — `domains/card_game/schema.py` (3 h)
Define `Unit`, `Ability`, `Deck` via `EntitySchema`.
**DoD:**
- `get_schema()` retorna `EntitySchema` para `Unit`
- Campos: `name` (kind `str`, max_len 40), `cost` (num 1-5), `hp` (num 1-20), `damage` (num 1-10), `ability_kind` (cat com enum fechado: `deal_damage|heal|shield|draw`), `ability_value` (num), `description` (str, max_len 200, opcional)
- Load `domains/card_game/seed_data.json` com 10 unidades e validar todas
- `pytest tests/test_card_schema.py` verde

### [x] B2.2 — `domains/card_game/simulator.py` (6 h)
Turn-based combat 1v1, seeded RNG, retorna `RunResult`. **Puro determinístico.**
**DoD:**
- `CardGameSimulator().run(entities=[deck_a, deck_b], env=MatchEnv(seed=42))` roda
- Mesma seed produz mesmo resultado (5 execuções — mesmo winner, mesmo turn count, mesmo damage_dealt)
- Regras: mana cresce por turno, hand size 5, abilities executam em order de play, HP zero remove
- 4 abilities: `deal_damage`, `heal`, `shield`, `draw`
- `pytest tests/test_card_simulator.py` cobre determinism, cada ability, edge case de empate

### [x] B2.3 — `core/scenario.py`: Scenario model + Event log (5 h)
Event log append-only em JSON-Lines. Cada evento é imutável.
**DoD:**
- `Event` Pydantic model com campos: `seq`, `parent_seq`, `branch_id`, `timestamp`, `actor` (str), `kind` (Literal enum), `target`, `before`, `after`, `metadata`
- `actor` aceita: `"user"`, `"llm-designer"`, `"llm-judge"`, `"llm-iterator"`
- `kind` aceita: `"create_entity"`, `"edit_entity"`, `"delete_entity"`, `"simulate"`, `"evaluate_subjective"`, `"set_objective"`, `"note"`
- `Scenario` model: `id`, `domain`, `name`, `objectives`, `head_event_seq`, `current_branch`
- `EventLog.append(event)` grava linha em `scenarios/<id>/events.jsonl`
- `EventLog.read(scenario_id, branch_id=None, up_to_seq=None)` retorna eventos ordenados
- `EventLog.head(scenario_id, branch_id)` retorna último seq
- 6 testes: append, read, sequencing correto, branch isolation, up_to_seq slice, evento em branch inexistente falha

### [x] B2.4 — Snapshot infra + replay + zstd (5 h)
Snapshot é dump completo do state num ponto do event log. Fica em `scenarios/<id>/snapshots/`, comprimido zstd (adicionar `zstandard` ao pyproject).
**DoD:**
- `Snapshot(scenario_id, at_seq, entities, env, sim_results_index)` model
- `SnapshotStore.save(snapshot)` — comprime com zstd, escreve `seq-<N>.json.zst`
- `SnapshotStore.load(scenario_id, at_seq)` — descomprime e retorna Snapshot
- `SnapshotStore.list(scenario_id, branch_id)` — lista snapshots disponíveis
- `Replay.rebuild_state(scenario_id, target_seq)` — pega snapshot mais próximo ≤ target_seq + aplica eventos entre eles + retorna state
- Auto-snapshot a cada 50 eventos (configurável)
- 5 testes: save/load round-trip, replay determinístico, snapshot mais próximo, ausência de snapshot cai pra replay do zero, compressão reduz tamanho

### [x] B2.5 — LLM protocols (3 hats) + Fakes (6 h)
Três `Protocol`s em `core/llm_hats.py`. Impl `Fake*` deterministicas em `core/llm_fakes.py`.
**DoD:**
- `DesignerLlm` protocol: `design(brief: str, schema: EntitySchema, constraints, n: int) -> list[Entity]`
- `SubjectiveJudgeLlm` protocol: `judge(entities: list[Entity], criterion: str) -> JudgeResult` (score 0-1 + rationale)
- `IteratorLlm` protocol: `propose_changes(entities, sim_metrics, judge_metrics, objectives) -> list[Modification]`
- `Modification` model: `kind` (create/edit/delete), `target` (entity_id or None), `payload`, `reasoning`
- `FakeDesigner` retorna entidades templadas do seed + variações determinísticas
- `FakeJudge` retorna score baseado em hash dos inputs (determinístico)
- `FakeIterator` propõe mudanças mecânicas (ex: se winrate > 60% de uma entity, propõe reduzir stat)
- 8 testes cobrem cada protocol + cada Fake

### Verificação final Sprint 2
- [x] `pytest` inteiro verde (90 testes)
- [x] Rodar end-to-end **com Fakes**:
  ```bash
  poetry run python -m scripts.demo_sprint2 \
    --brief "aggro deck with cheap units" \
    --n 5 --domain card_game
  ```
- [x] Script cria Scenario, FakeDesigner gera 5 unidades, CardGameSimulator roda 100 matches (round-robin de decks-solo → winrate por unidade), FakeJudge avalia, FakeIterator propõe modificações, tudo persistido em `scenarios/<id>/events.jsonl` + `manifest.json` + snapshot zstd (verificado + portátil via tar)
- [x] Rodar de novo com mesmo brief + seed produz output idêntico (guardado por `tests/test_demo_sprint2.py`)

---

## Sprint 3 — Motor de iteração + branching + multi-objetivo + cache incremental (25 h)

### [x] B3.1 — Motor de iteração event-based (7 h)
Sem state machine rígida. Loop reativo: `iterate(scenario)` puxa estado atual, chama Designer/Iterator conforme fase, aplica mudanças propostas (se autorizadas), roda simulate/judge, grava eventos. Usuário pode inserir evento manual entre qualquer chamada.
**DoD:**
- `IterationEngine.step(scenario_id, phase: Literal["design","iterate","simulate","judge"])` — executa uma fase, grava eventos
- Cada step é atomic — se falha no meio, eventos parciais **não** são commitados
- `IterationEngine.auto_loop(scenario_id, max_steps=10, stop_on_convergence=True)` — roda phases em ordem até convergir ou max_steps
- Detectar "user injection": se `EventLog.head()` cresceu entre início e fim do step, engine incorpora o novo estado antes de próximo step
- 6 testes: single step, full auto loop, user injection mid-loop respeitada, atomic rollback em erro

### [x] B3.2 — Branching + diff (5 h)
Branch = novo `branch_id`, primeiro evento aponta pra `parent_seq` do fork point.
**DoD:**
- `Branch.create(scenario_id, parent_seq, name) -> branch_id`
- `Branch.list(scenario_id) -> list[BranchInfo]` com nome, head_seq, event_count
- `Branch.diff(scenario_id, branch_a, branch_b) -> DiffReport` — mostra eventos exclusivos de cada, entidades divergentes, métricas divergentes
- Branches são independentes — evento em branch A não afeta branch B
- 5 testes: create, list, diff simétrico, dois branches não interferem

### [x] B3.3 — Multi-objetivo (4 h)
Usuário compõe N objetivos com pesos, engine agrega score.
**DoD:**
- `Objective` model: `metric_name` (str), `direction` (minimize|maximize|target), `target_value` (opt), `weight` (float)
- `ObjectiveAggregator.score(objectives, metric_results) -> float` — score único ponderado
- `ObjectiveAggregator.pareto_check(objectives, candidates) -> list[Candidate]` — frente de Pareto quando 2+ objetivos conflitam
- `Objective.set_via_event(scenario, objectives)` — grava como evento `set_objective`
- 4 testes: single objective, dois conflitantes (Pareto), peso zero ignorado, target_value

### [x] B3.4 — Cache incremental (5 h)
Cache sim invalida só entradas que envolvem entidades editadas.
**DoD:**
- `SimCache` (impl de `CacheBackend`, `diskcache` no dev) armazena `{config_hash → RunResult}` com metadata `{entities_involved, kind: quick|full, computed_at_seq}`
- `SimCache.invalidate_touching(entity_ids)` remove entradas que envolvem entidades listadas
- `IncrementalSimRunner.run(entities, env, n_runs, kind)`:
  - Verifica cache — se hit, retorna direto
  - Se miss parcial (algumas duplas cached, outras não), roda só as faltantes
  - Registra evento `simulate` no log
- Freshness tag por config: `computed_at_seq` = seq do último evento antes do cache. Se `head_seq > computed_at_seq`, marca stale
- 5 testes: hit, miss full, miss parcial + reuso, invalidação por entity_id, freshness stale

### [x] B3.5 — Endpoints (4 h)
Rotas FastAPI expondo o fluxo end-to-end com Fake LLMs.
**DoD:**
- `POST /scenarios` — cria scenario com domain + brief opcional
- `GET /scenarios/{id}` — retorna current state (rebuild via replay)
- `POST /scenarios/{id}/iterate` — dispara `IterationEngine.step` com phase no body
- `POST /scenarios/{id}/entities` — usuário insere entidade manual (grava evento)
- `PATCH /scenarios/{id}/entities/{entity_id}` — edita
- `DELETE /scenarios/{id}/entities/{entity_id}` — remove
- `POST /scenarios/{id}/objectives` — define objetivos multi-critério
- `GET /scenarios/{id}/history` — retorna events do branch atual
- `POST /scenarios/{id}/branches` — cria branch
- `GET /scenarios/{id}/branches/{a}/diff/{b}` — retorna DiffReport
- Todos usam Fakes; nenhum toca API real
- `pytest tests/test_api_scenarios.py` cobre happy path + 404 + 422

### Verificação final Sprint 3
- [x] Rodar sequência end-to-end via curl (`scripts/demo_sprint3.sh`) — todos os 9 passos rodam ao vivo (uvicorn). Destaque: no passo 7 o FakeIterator propôs 4 mudanças, aplicou 3 e **pulou a entidade editada pelo usuário** (`skipped_user_owned: ["cyberpunk-0"]`) — authorship guardrail comprovado end-to-end.
- [x] Cenário exportável: pasta `scenarios/<id>/` tem `manifest.json`, `events.jsonl`, `sim_cache/` populado. *`snapshots/` só aparece no intervalo de 50 eventos (mecanismo já verificado no Sprint 2 e ligado no `auto_loop`); o demo tem 24 eventos.*
- [x] `tar czf backup.tar.gz scenarios/<id>` e extrair em outra pasta — carrega intacto (24 eventos, branches `main`+`alt`)

---

## Sprint 4 — Creature RPG plugin (escala + perf) (20 h)

### [x] B4.1 — `domains/creature_rpg/schema.py` (4 h)
`Creature` (name kind `str`, type cat, hp/atk/def num, skills tag_set, resistances dict), `Skill`, `Type` enum.
**DoD:**
- 100 creatures seed em `domains/creature_rpg/seed_data.json`, distribuídas em 8 tipos (12-13 por tipo)
- Cada creature tem 2-4 skills
- Load em <1s (design pra escalar até 200 sem colapsar)
- Todas validam via schema

### [x] B4.2 — `domains/creature_rpg/simulator.py` (8 h)
Gauntlet mode + tournament mode.
**DoD:**
- Gauntlet: `Creature` vs random N adversários, retorna estatísticas
- Tournament: round-robin em subset de creatures
- Type matchup table pluginável via JSON (`domains/creature_rpg/matchups.json`)
- Ability queue com priority + cooldown
- Determinismo com seed (5 execuções mesmo output)
- 6 testes cobrem cada modo + edge cases

### [x] B4.3 — Métricas RPG (4 h)
`TierEmergence`, `DominanceIndex`, `UsageCoverage`.
**DoD:**
- `TierEmergence`: agrupa creatures por rating em tiers S/A/B/C/D
- `DominanceIndex`: fração de matches em que top-5% ganha
- `UsageCoverage`: quantas creatures aparecem em pelo menos M matches
- Métricas usam base `Metric` do core
- `pytest tests/test_creature_metrics.py` verde

### [x] B4.4 — Performance profiling + tuning (4 h)
Design assume 1000 entidades máximas com folga sobre escala real (100/500).
**DoD:**
- `ThreadPoolExecutor` paraleliza simulate calls
- 100 creatures × 1000 gauntlet matches em <30s (quick estimate <2s)
- 500 cartas × 1000 matches em <60s (quick <3s)
- Cache hit em request repetido: <100ms
- Benchmarks em `tests/test_performance.py` — falha se regressão >20%

### Verificação final Sprint 4
- [x] 100 creatures rodando gauntlet completo produz tier list emergente (S/A/B/C/D 20 cada, 1000 battles em 0,030s)
- [x] Cache hit second-run <200ms (medido <5ms com InMemory; guardado por `test_performance.py`)
- [x] Benchmarks documentados em `docs/performance.md`

---

## Sprint 5 — UI (30 h)

### [x] B5.1 — Setup Next.js 15 + shadcn/ui + rotas (4 h)
**DoD:**
- `pnpm dev` roda em http://localhost:3000
- shadcn/ui: `<Button>`, `<Card>`, `<Input>`, `<Select>`, `<Tabs>`, `<Slider>`, `<Dialog>`
- Rotas: `/`, `/scenarios/[id]`, `/scenarios/[id]/history`, `/scenarios/[id]/branches`
- Home lista scenarios locais (fetch `GET /scenarios`)

### [ ] B5.2 — `<EntityEditor>` genérico (6 h)
Renderiza form a partir de `EntitySchema`.
**DoD:**
- Recebe `schema` + `value`, emit `onChange`
- Renderiza: input num (com slider quando tem range), select cat, checkbox bool, tag input tag_set, textarea str (com min/max caracteres)
- Ambos domains (card + creature) usam **o mesmo componente**
- Validação inline mostra erro quando fora do range/enum
- Vitest: 5 testes

### [ ] B5.3 — Timeline scrubber + history (6 h)
Usuário navega no histórico do cenário.
**DoD:**
- Timeline horizontal mostra eventos ordenados por seq
- Ícone/cor por `actor` (user, designer, judge, iterator)
- Hover em evento mostra `metadata` (motivo do LLM, nota do user)
- Click restaura view read-only pra aquele ponto (usa `Replay.rebuild_state`)
- Filtro por actor, por kind
- Vitest: 3 testes

### [ ] B5.4 — Real-time metrics panel + freshness indicators (6 h)
Painel lateral com métricas + indicador de estado da simulação.
**DoD:**
- Cada card de métrica tem:
  - Valor
  - Ícone de freshness: 🟢 full (N alto), 🟡 quick (N pequeno), 🔴 stale, ⏳ computing
- Debounce: 2s de idle após edit → dispara quick; 5s → dispara full
- SSE do backend empurra progress
- Botão "Run Full Simulation" força
- Vitest: 4 testes de UI + integração mockada

### [ ] B5.5 — Multi-objective picker (4 h)
UI de composição de objetivos com pesos.
**DoD:**
- Painel "Objectives" lista objetivos disponíveis do domain (fetch `GET /domains/{name}/metrics`)
- Usuário adiciona objetivo, escolhe direção (min/max/target) e peso (slider)
- Aggregate score mostrado no header
- Frente de Pareto (2 objetivos) renderiza scatter com Pareto highlighted
- Vitest: 3 testes

### [ ] B5.6 — Diff view entre branches / pontos do timeline (4 h)
**DoD:**
- Selector "Compare A vs B" (branch, ou seq points)
- Diff visual: entities added/removed/edited destacados
- Métricas comparadas lado a lado
- Botão "Fork from A" cria novo branch a partir do ponto A
- Vitest: 2 testes

### Verificação final Sprint 5
- [ ] Navegação completa em 2 domínios: card game + creature RPG
- [ ] Freshness indicators respondem corretamente a edições
- [ ] Timeline scrubber restaura estado
- [ ] Screenshots dos dashboards em `README.md`

---

## Sprint 6 — Impl real Anthropic (Designer/Judge/Iterator) + prompt tuning (20 h) — **PRIMEIRA VEZ QUE PRECISA DE API KEY**

### [ ] B6.1 — `AnthropicDesigner` (4 h)
**DoD:**
- Impl do `DesignerLlm` protocol usando Anthropic SDK
- `tool_use` estruturado — schema derivado do `EntitySchema` via `to_llm_schema()`
- Retry com feedback em erro de schema (max 3 retries)
- Constraint violations pós-geração filtradas + logadas
- 3 testes com mock Anthropic (não hit real): sucesso, retry após inválido, filter constraint violation

### [ ] B6.2 — `AnthropicJudge` (4 h)
**DoD:**
- Impl do `SubjectiveJudgeLlm` protocol
- Prompts em `core/prompts/judge_<criterion>.txt` — critérios: `variety`, `cohesion`, `thematic_consistency`
- Retorna score 0-1 + rationale
- 3 testes com mock

### [ ] B6.3 — `AnthropicIterator` (4 h)
**DoD:**
- Impl do `IteratorLlm` protocol
- Prompt inclui: entidades atuais + resultados de sim + judge scores + objetivos + histórico recente de mudanças
- Retorna `list[Modification]`
- Nunca propõe mudança em entidade que já foi editada por user (respeita autoria; deixa comentário em `metadata.reasoning`)
- 3 testes com mock

### [ ] B6.4 — Config switch fake/anthropic + secrets (2 h)
**DoD:**
- Env var `LLM_BACKEND=fake|anthropic` seleciona impl no startup
- `ANTHROPIC_API_KEY` obrigatório se `LLM_BACKEND=anthropic` — startup falha claro se ausente
- Docs em `README.md` explicando como configurar

### [ ] B6.5 — Prompt tuning + validação real (6 h)
Rodar 5 loops completos com Anthropic real em cada domain (card + creature).
**DoD:**
- 5 loops card_game: brief → design → simulate → judge → iterate → converge (ou max 10 steps)
- 5 loops creature_rpg
- Sucesso rate (fração de entidades geradas que passam constraints) >80% card, >70% creature
- `docs/experiments.md` documenta iterações de prompt com métricas
- Custo total registrado no experiment log (esperado: $2-5)

### Verificação final Sprint 6
- [ ] Dois domínios convergem em <10 steps com Anthropic real
- [ ] Custo por loop documentado (~$0.30-0.80)
- [ ] Config switch fake/anthropic testado em ambos

---

## Sprint 7 — Team composition plugin + tutorial (20 h)

### [ ] B7.1 — `domains/team_composition/schema.py` (3 h)
`Person(name str, seniority cat, skills tag_set, preferred_task_types tag_set)`, `TaskType`.
**DoD:**
- Seed com 50 pessoas, 20 task types
- Schema valida seed

### [ ] B7.2 — `domains/team_composition/simulator.py` (8 h)
Modelo probabilístico de completion.
**DoD:**
- `WorkloadEnv(tasks, deadline_days, seed)` define carga
- Simulator retorna: task completion rate, avg time, blocked tasks
- Determinismo com seed
- 5 testes de comportamento

### [ ] B7.3 — Métricas team (3 h)
`SkillCoverage`, `Redundancy`, `SinglePointOfFailure`.

### [ ] B7.4 — `docs/writing-a-domain.md` — tutorial (6 h)
Passo a passo pra criar novo domain.
**DoD:**
- Quickstart 10 min (hello_domain)
- Walkthrough completo (team_composition como exemplo real)
- Checklist antes de PR
- Reader externo esboça um domain trivial em <2h seguindo o doc

### Verificação final Sprint 7
- [ ] 3 domains listados na UI, todos rodam
- [ ] Tutorial pronto e revisado

---

## Sprint 8 — Deploy + polish + migração Postgres/Redis (20 h)

### [ ] B8.1 — Deploy Fly.io + Vercel + migração de infra (8 h)
Momento planejado de trocar SQLite → Postgres e `diskcache` → Redis.
**DoD:**
- Provisionar Fly Postgres + Fly Redis (upstash) via `flyctl`
- Implementar `RedisCacheBackend` — passa mesmo test suite do `DiskCacheBackend`
- `DATABASE_URL` prod aponta pra Postgres; local segue SQLite
- `alembic upgrade head` roda contra Postgres remoto (schema portável desde Sprint 2)
- Smoke: criar scenario, iterar 3 vezes, cache hit em segunda iteração
- Frontend no Vercel
- Secrets via `fly secrets` / Vercel env vars
- URL público funcional

### [ ] B8.2 — Seed data polida por domain (3 h)

### [ ] B8.3 — README completo (5 h)

### [ ] B8.4 — Demo video 4 min + post técnico (4 h)

### Verificação final Sprint 8
- [ ] URL público funcional compartilhado
- [ ] Números embutidos no README

---

## Opções futuras (fora do MVP — atualizações se fizer sentido depois)

Registrar aqui e não implementar. Cada uma é candidata a evolução pós-TCC.

- **Multi-user sync colaborativo em tempo real** (~15-20 h): SSE + presença + last-write-wins conflict handling. Habilita:
  - (b) time de design colaborando
  - (c) loop com playtester remoto
  - (d) iteração assíncrona overnight (worker sem UI)
  - (f) observador read-only
- **CRDT / merge automático de branches** (meses): sync tipo Figma/Google Docs. Fora de escala pra TCC.
- **Managed SaaS billing** (~40 h): tier gratuito + tier pago com créditos de iteração.
- **API pública pra integrações** (~20 h): OAuth, rate limits, endpoints públicos versionados.
- **Import de dados existentes** (~15 h por formato): CSV, JSON de outros formatos de balance.
- **Preset de objetivos por vertical** (~10 h): "game F2P economy", "team hiring", "product portfolio" — templates com objetivos pré-configurados.
- **Auto-refresh entre janelas do mesmo usuário** (~2 h): file watcher local ou polling on window focus — resolve caso (a) sem sync completo.

---

## Estimativas resumidas

| Sprint | Total | Cumulativo | LLM real? |
|---|---:|---:|---:|
| 1 (feito) | 20 h | 20 h | — |
| 2 | 25 h | 45 h | Fake |
| 3 | 25 h | 70 h | Fake |
| 4 | 20 h | 90 h | — |
| 5 | 30 h | 120 h | Fake |
| 6 | 20 h | 140 h | **Sim** |
| 7 | 20 h | 160 h | — |
| 8 | 20 h | 180 h | Só demo |
