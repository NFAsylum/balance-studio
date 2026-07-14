# INBOX — 2026-07-13 (Balance Studio — Quick wins + Blueprint gate)

Após executar, mova pra `docs/inbox-archive/2026-07-13-quick-wins-and-blueprint-gate.md`.

## Status

- ✅ **QW.1** — Preset `outpost-siege.json` criado por Marco/Claude direto em 2026-07-13. Sem execução necessária.
- ✅ **QW.2** — Preset `cover-firefight.json` criado por Marco/Claude direto em 2026-07-13. Sem execução necessária.
- 🆕 **T-QW.README** — Rewrite honesto do README (pending)
- 🆕 **T-QW.GALLERY** — Starter scenarios seed on first-run (pending)
- ⏸ **BLUEPRINT-ENCOUNTER** — `docs/blueprint-encounter-domain.md` documenta o Caminho B (encounter domain). **STANDBY** — só executar quando Marco disser "Execute docs/blueprint-encounter-domain.md". Não incluir nesse commit/PR.

## Contexto

Decisão de 2026-07-13: manter Balance v1 (α — arquitetura atual). Não fazer γ (rule engine pivot) por conflito com Babel TCC + payback pessoal não fecha. Documento de referência γ salvo em `docs/roadmap-v2-rule-engine.md`.

Quick wins que **aumentam variedade e clareza** do Balance atual, sem committment arquitetural:

1. Presets criativos que reinterpretam `creature_rpg` (RE/Gears vibe) — done.
2. README honesto (retira `team_composition` e `product_management` do pitch principal, posiciona como playground exploratório pra card games e creature RPGs).
3. Starter scenarios seed on first-run — mata empty state.

Depois desses, **blueprint pra `encounter` domain está no repo** aguardando gatilho manual. Quando Marco quiser mais fidelity (55-65% pra FPS/survival), roda o blueprint.

## Red lines

- ❌ **`git rebase` proibido.** Use merge.
- ❌ **Sem force push, sem history rewrite.**
- ❌ **Não postar review/comentário/PR no GitHub sem confirmação humana.**
- ❌ **Não mexer em `docker/.env`.**
- ❌ **NÃO executar `docs/blueprint-encounter-domain.md` nesta rodada.** É standby explícito, gatilho manual do Marco.

## Ordem sequencial

Execute **apenas T-QW.README e T-QW.GALLERY** nesta rodada. Presets já estão no repo.

### T-QW.README [1-2h] Rewrite honesto do README

**Contexto:** o README atual promete generalização (card_game + creature_rpg + team_composition + insinua product management) que a implementação atual não entrega. Isso cria dissonância "Balance parece gerador de cards estático porque promete muito e entrega abstrato".

**O que fazer:**

1. **Retire do pitch principal:** menções a `team_composition` como caso de uso equivalente aos jogos e menções a "product portfolio" / "staffing" como casos de uso reais.
   - Motivo: `team_composition` é demo de generalidade do framework, não ferramenta útil pra manager real (sim linear demais pra dinâmica humana).
   - `product_management` **nem existe** como domain — retire completamente.

2. **Reposicione honestamente:** Balance é um **playground pra explorar princípios de balance em modelos simplificados de card games, creature RPGs e (com encounter blueprint no futuro) FPS/survival horror**. Não substitui playtest com humanos; substitui os primeiros 15% do trabalho onde você elimina outliers gritantes antes de comprometer tempo de outras pessoas.

3. **Mantenha:**
   - A seção "Does the loop actually balance?" com resultados medidos (creature_rpg -10.6%, card_game -2.2%). É evidência real, positiva pra credibilidade.
   - `team_composition` como **exemplo de generalidade do framework** (não caso de uso real): "Um plugin de 400 LOC pode modelar workflow de time. É demo de que o framework é agnóstico ao gênero, não substituto de EM competente."
   - Menção a Machinations/Ludii/similares como referências do espaço.

4. **Adicione seção "What Balance is (and isn't)"** — 3-4 parágrafos explicitando escopo:
   - **É**: pre-playtest sanity check; playground pra explorar hipóteses de balance; framework demo com 3+ domínios.
   - **Não é**: production balancing tool pra jogo shippado; ferramenta de management team decisions; product prioritization system.

**Onde editar:** `README.md`, seção "The problem" e "What's in the box" principalmente. Rescreva sem eliminar história (mantém commit anterior no git).

**DoD:**
- README não menciona "staffing 50 people" ou "product portfolio" como casos de uso ativos
- Seção "What Balance is (and isn't)" existe com 3-4 parágrafos claros
- Nenhuma promessa de generalização inflada
- `team_composition` mencionado só como demo de framework, não como caso de uso real
- Commit direto na `dev-marco-readme-rewrite` ou branch similar

**Se travar** (mudança de tom parece drástica demais): escale mostrando 2-3 opções de posicionamento pro Marco decidir. Não decida sozinho.

### T-QW.GALLERY [2-4h] Starter scenarios seed on first-run

**Contexto:** empty state atual ("Nenhum cenário") é sinal de que Balance é ferramenta ambiciosa mas fria. Curated gallery elimina paralisia e ensina através de exemplos.

**O que fazer:**

1. **Criar script `scripts/seed_starter_scenarios.py`** que:
   - Checa se `scenarios/` está vazio (nenhum cenário existente na storage)
   - Se vazio, cria 4-5 cenários pré-populados com:
     - `preset_id` explícito (usa presets existentes — `modern-mana-tcg`, `high-scale-duel`, `outpost-siege`, `cover-firefight`, `elemental-creatures-classic`)
     - `brief` real e pedagógico
     - Entidades pre-designadas (não vazias) — use os `examples` do preset como seed
     - `visual_variant` explícito (não None)
   - Cada scenario tem nome descritivo tipo "Modern Mana: teste dominância de creatures cost 5"

2. **Wire ao startup do backend** — chamar de dentro do `api/dependencies.py::lifespan` **antes** de yield.
   - Idempotente: se já existem scenarios, no-op.

3. **Docs curtos** em `docs/starter-scenarios.md` explicando o que cada um explora.

**Sugestões de starter scenarios:**

| ID | Preset | Brief | Que ensina |
|---|---|---|---|
| `starter-hearthstone-like` | modern-mana-tcg | "Cost curve dominance test — is 5-cost card 3 outlier?" | Modern-mana curve tuning |
| `starter-yugioh-scale` | high-scale-duel | "High-ATK monster viability in duel format" | High-scale balance |
| `starter-outpost-siege` | outpost-siege | "Shotgun vs Rifle vs Pistol dominance — plus armored zombie stress test" | Weapon vs enemy matchups (RE-flavor) |
| `starter-cover-firefight` | cover-firefight | "Locust waves against Gears-style loadout — is Hammer of Dawn OP given HP=20?" | Cover-shooter loadout tuning |
| `starter-pokedex-kanto` | elemental-creatures-classic | "Charizard-like fire creature dominates or types keep it in check?" | Type-effectiveness balance |

**DoD:**
- `scripts/seed_starter_scenarios.py` existe e é idempotente
- Startup do backend fresh (storage vazio) cria os 5 starters automaticamente
- `curl http://localhost:8000/scenarios` retorna os 5 starters em backend fresh
- `docs/starter-scenarios.md` existe com descrição de cada
- `pytest tests/test_starter_scenarios.py` verde (idempotency, no-op quando já existem, cria quando vazio)
- Nenhum teste existente quebra

**Se travar** (integração com lifespan handler dá conflict): escale antes de tocar arquitetura de bootstrap.

## Depois de tudo verde

1. `git push` das branches (README + gallery podem ser 1 PR só ou 2, tanto faz — apenas garante que rebase não é usado)
2. Abrir PR(s): título `feat: quick wins — README rewrite + starter gallery`
3. Body do PR:
   - Menciona QW.1 e QW.2 (presets) como pré-existentes no branch
   - Explica motivação (framing honesto + empty state elimination)
   - Screenshot da home page nova com galeria (se tempo)
4. **Aguardar autorização humana** pra merge

## Diretiva sobre escopo

Execute **T-QW.README + T-QW.GALLERY** nesta ordem. **Não execute**:
- `docs/blueprint-encounter-domain.md` — standby explícito
- Qualquer feature nova além do listado
- Refactors de código existente que não estejam pedidos aqui

Se qualquer DoD falhar após 2 tentativas: **escale**. Precedente: preemptive cuts geram under-delivery.

Reporte no próximo prompt:
- SHA dos commits
- Confirmação de DoD verde de cada task
- Se acionou o blueprint accidentalmente: escale IMEDIATAMENTE (não deveria ter)

## Referências

- `docs/roadmap-v2-rule-engine.md` — γ (rule engine pivot) documentado como STANDBY futuro
- `docs/blueprint-encounter-domain.md` — Caminho B (encounter domain) STANDBY até Marco acionar
- `presets/creature_rpg/outpost-siege.json` — RE-vibe preset (já no repo)
- `presets/creature_rpg/cover-firefight.json` — Gears-vibe preset (já no repo)
