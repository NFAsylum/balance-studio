# INBOX — 2026-07-12 (Balance Studio — Scenario Editor + Level 2.5)

Após executar, mova pra `docs/inbox-archive/YYYY-MM-DD-scenario-editor.md`.

## Filosofia dos projetos (regra permanente)

**Todo projeto do marco é para nível de produto usável por usuário real.** Bolhas de portfólio que quebram na primeira interação são explicitamente inaceitáveis. Se você (Claude) estiver escolhendo entre "wireframe demonstrável" e "coisa que alguém consegue usar de verdade", escolha a segunda mesmo que custe mais tempo. Se algum trade-off apertar produto-usável, sinalize explicitamente ao humano — nunca corte silenciosamente.

**"Produto usável" concretamente significa:**
- Onboarding não-vazio (não abre em tela em branco sem CTA)
- Prompts LLM tunados pra **qualidade de conteúdo**, não só pra passar validação
- Erros tratados graciosamente com mensagem clara + recuperação
- Controles do usuário existem pra tudo que o LLM decide (schema, ranges, layout, style)
- Empty states informativos (não "Sem dados")
- Presets prontos pra casos reais (Hearthstone, MTG, YuGiOh — não "Balanced Set")
- Diferenciação visual — cartas, monstros e pessoas **não** parecem JSON cru
- Extensibilidade real — usuário técnico pode contribuir seus próprios layouts sem modificar core
- Fallback sempre-funciona — nada quebra mesmo com schema exótico
- Auditoria completa em `docs/product-audit.md` como referência viva

## Contexto: por que essa task existe

Balance Studio atual **é uma bolha**. Usuário abre, quer criar um jogo de cartas Yu-Gi-Oh-like ou um bestiário Pokémon-like, e bate no muro em 3 minutos porque:
- Schema hardcoded (HP > 20 rejeitado, não dá pra fazer LP 8000)
- Cards renderizam como JSON cru — Hearthstone e Team Composition ficam idênticos
- Sem presets, começa do zero
- Nomes "Carta-0" porque prompt LLM não tunado
- Skills vazias porque LLM ignora campos "opcionais"
- Só textarea "brief" — sem sliders/pickers/intent

Detalhes completos em `docs/product-audit.md` (41+3 issues, ~135h pra produto usável).

**Essa task ataca a peça central: o Scenario Editor unificado.** Ele fecha ~7 issues do audit numa feature coerente, transformando Balance de "coisa que dev testa" em "ferramenta que designer de jogo usa".

## Trilha completa (~65-100h)

Ordem sugerida — cada task tem DoD verificável. Se algo estourar 30% da estimativa, escale ao humano.

---

### FASE 1 — Backend: Scenario aceita schema customizado (~15h)

O plugin deixa de ser "dono do schema" e vira "provedor de regras + template". Scenario carrega o schema efetivo.

#### T1.1 [4h] Refactor `EntitySchema` pra aceitar overrides

**Problema:** `EntitySchema.from_dict(...)` cria schema estático. Não tem merge.

**Ação:**
1. Novo método `EntitySchema.with_overrides(overrides: dict) -> EntitySchema` que:
   - Merge shallow de fields (por `name` do field)
   - Cada field field-level pode ser sobrescrito (range, enum, min_len, max_len)
   - Fields novos podem ser adicionados
   - Fields existentes podem ser removidos via `{"name": "hp", "remove": true}`
2. `EntitySchema` ganha `origin: Literal["plugin", "user"]` por field pra tracking
3. `EntitySchema.to_llm_schema()` já existe — verificar que overrides propagam pro output

**DoD:**
- 8 testes cobrem: override de range, override de enum, add field, remove field, override em cima de range, override que conflita com kind (erro)
- `pytest tests/test_entity_schema.py` verde
- Overrides em memória, não persistidos ainda (T1.2 cuida disso)

#### T1.2 [4h] `Scenario` model persiste `schema_overrides`

**Problema:** Scenario atual não tem noção de schema override.

**Ação:**
1. `Scenario` Pydantic model ganha campo `schema_overrides: dict = {}`
2. `manifest.json` do scenario grava esse campo
3. `SnapshotStore` e replay preservam
4. Método `Scenario.effective_schema(plugin_registry)` retorna schema efetivo = `plugin.get_schema().with_overrides(scenario.schema_overrides)`
5. Backward compat: scenarios existentes com `schema_overrides = {}` funcionam idênticos

**DoD:**
- 4 testes: default vazio funciona, override persiste, replay preserva, effective_schema retorna correto
- Load de scenario existente (sem overrides) não quebra

#### T1.3 [3h] Sistema de presets

**Problema:** Sem presets = usuário começa do zero.

**Ação:**
1. Estrutura de pastas:
   ```
   presets/
   ├── card_game/
   │   ├── hearthstone.json
   │   ├── mtg.json
   │   ├── yugioh.json
   │   └── slay-the-spire.json
   ├── creature_rpg/
   │   ├── pokemon-gen1.json
   │   ├── monster-hunter.json
   │   └── dark-souls.json
   └── team_composition/
       ├── software-team.json
       ├── consulting.json
       └── sports-team.json
   ```
2. Cada preset JSON tem: `id`, `name`, `description`, `domain`, `schema_overrides`, `default_constraints`, `default_objectives`, `default_visual_variant`
3. Endpoint `GET /presets?domain={name}` lista presets do domain
4. Endpoint `GET /presets/{preset_id}` retorna preset completo
5. **CONTEÚDO REAL** — os presets precisam ter valores reais dos jogos (não "example values"). Pesquisar antes de escrever:
   - Hearthstone: mana 0-10, HP 1-30, attack 0-16
   - MTG: mana cost 0-10 (colored + generic), power/toughness 0-∞, life total 20
   - Yu-Gi-Oh: LP 8000, ATK/DEF 0-5000, level 1-12
   - Pokémon Gen 1: HP 10-250, ATK/DEF 5-134, 15 types
6. Presets mais estruturais (não gameplay): esses são o "gancho" pro usuário

**DoD:**
- 3+ presets por domain (9 total mínimo) com valores reais
- Endpoints funcionais
- 5 testes cobrindo load + validation
- Preset com valores errados falha claro na inicialização

#### T1.4 [4h] Endpoint de scenario com preset

**Problema:** `POST /scenarios` atual não aceita preset.

**Ação:**
1. `POST /scenarios` body ganha campos opcionais:
   - `preset_id: str` — carrega schema + constraints + objectives do preset
   - `schema_overrides: dict` — overrides adicionais em cima do preset
   - `visual_variant: str` — qual layout usar (default: preset's default)
2. Validação: se `preset_id` inválido ou não bate com domain, 422
3. `preset_id` gravado no scenario pra referência
4. Compat: `preset_id = null` funciona (default do plugin, comportamento atual)

**DoD:**
- Curl end-to-end: criar scenario com preset, `GET /scenarios/{id}` retorna schema efetivo com overrides do preset
- Testes de API cobrem happy path + erros
- Documentação em `docs/architecture.md`

---

### FASE 2 — Level 2.5: Domain visual system (~30-45h)

Cada plugin fornece 2-3 variantes visuais pré-shipped + framework core tem `DefaultListView` fallback + pasta custom que usuário pode dropar seus próprios `.tsx`.

#### T2.1 [3h] `DefaultListView` — fallback que **sempre funciona**

**Problema:** Framework precisa garantir que qualquer schema tem visualização. Zero cenário de "tela quebrada".

**Ação:**
1. Criar `ui/src/domain-views/DefaultListView.tsx`
2. Renderiza qualquer entidade:
   - Título = primeiro campo `str` do schema (ou field literalmente chamado `name`, ou "Untitled")
   - Sections agrupadas por kind:
     - Identifiers (str/cat): key-value list, valor destacado
     - Numeric fields: grid 2-3 colunas com label + value
     - Tag sets: chips coloridos
     - Maps: mini-tabela key×value
     - Booleans: check/x com label
3. Tipografia neutra (sem cor decorativa), Tailwind default
4. Props: `entity: object, schema: EntitySchema, size?: 'sm'|'md'|'lg'`
5. Registrar no view registry como fallback

**DoD:**
- Renderiza qualquer schema sem quebrar
- Vitest test com 3 schemas distintos
- Screenshot no `docs/screenshots/default-view.png`

#### T2.2 [3h] View registry + discovery

**Problema:** Sistema precisa saber quais views existem, qual usar quando.

**Ação:**
1. Criar `ui/src/domain-views/registry.ts`:
   ```typescript
   interface EntityView {
     id: string;              // "card_game.hearthstone" ou "custom.MyCard"
     name: string;            // "Hearthstone" ou "My Custom Card"
     domain: string | "*";    // domain aplicável ou "*" pra any
     component: React.ComponentType<EntityViewProps>;
     defaultMapping: Record<string, string>;  // qual field do schema vai em cada slot
   }
   ```
2. Discovery via Vite's `import.meta.glob('./{card_game,creature_rpg,team_composition,custom}/*.tsx', { eager: true })`
3. Cada view file exporta metadata + component. Registry indexa.
4. Método `getViewsForDomain(domain: string): EntityView[]` retorna views aplicáveis + `DefaultListView` sempre
5. Método `getViewById(id: string): EntityView | null`

**DoD:**
- Registry auto-descobre views ao build
- Adicionar novo `.tsx` na pasta correta aparece no dropdown sem código extra
- 4 testes: discovery, filter by domain, get by id, default fallback

#### T2.3 [4-5h] Card Game — 1-2 variantes reais

**Problema:** Ship pré-construídas pros jogos populares.

**Ação (mínimo 1 variante, ideal 2):**

**HearthstoneStyle.tsx** — vertical:
- Border color por `ability_kind` (attack=red, heal=green, shield=blue, draw=purple)
- Nome em topo com fonte serif
- Círculo de mana top-left, HP crystal bottom-right, damage sword bottom-left
- Espaço central pra "ability text" ou emoji do ability kind
- Layout ~250×350px em `md` size

**YuGiOhStyle.tsx** (opcional se tempo permitir) — horizontal:
- Layout apaisado, banner de nome no topo com border dourada
- Level stars no topo direito (número de estrelas = level)
- Área central pra emoji do type
- Row de ATK / DEF na base
- Layout ~350×250px em `md` size

**Cada variante:**
1. `.tsx` file com component
2. `defaultMapping` object mapeando slots pra field names esperados
3. Prop `mapping` permite user remapear
4. Tratamento de campo faltando: mostra "—" em vez de crashar

**DoD:**
- 1-2 variantes visualmente distintas do JSON cru
- Cards renderizam corretamente pra seed data do card_game
- Vitest snapshot test
- Screenshots em `docs/screenshots/`

#### T2.4 [4-5h] Creature RPG — 1-2 variantes reais

**PokedexStyle.tsx** — horizontal split:
- Left panel (~40%): sprite/emoji grande do tipo (fire=🔥, water=💧, etc.), badge do tipo colorido
- Right panel (~60%):
  - Nome no topo bold
  - Stats grid: HP, ATK, DEF em rows com bars visuais
  - Skills como chips
  - Resistances como mini-icon grid
- Layout ~400×200px em `md` size

**MonsterHunterStyle.tsx** (opcional) — cinza escuro:
- Silhueta do tipo estilizada
- Grid de fraquezas/resistances como star ratings
- Layout mais "wiki entry"

**DoD:** análogo ao T2.3

#### T2.5 [4-5h] Team Composition — 1-2 variantes reais

**BadgeStyle.tsx** — vertical badge:
- Avatar circular com initial do nome + color hash
- Nome grande
- Seniority chip (junior/mid/senior/lead)
- Skills como pills
- Preferred task types como tags menores
- Layout ~200×280px

**RosterStyle.tsx** (opcional) — grid card compact:
- Layout tipo LinkedIn card
- Foto placeholder (emoji ocupação se possível)
- Info organizada em rows

**DoD:** análogo

#### T2.6 [3h] Pasta `custom/` + discovery de user components

**Problema:** Power users precisam de Level 3, sem construir designer visual.

**Ação:**
1. Criar `ui/src/domain-views/custom/` com README explicando:
   - "Drop `.tsx` files here. They appear automatically in scenario editor."
   - Interface `EntityViewProps` documentada
   - Exemplo mínimo (2 arquivos: `example-simple.tsx`, `example-with-mapping.tsx`)
2. Discovery já cobre isso via glob (T2.2)
3. Custom views aparecem em section separada no dropdown ("Custom variants")
4. Error boundary em volta de cada custom view — se quebrar, fallback pro DefaultListView + toast avisando

**DoD:**
- Adicionar arquivo `.tsx` na pasta aparece na UI
- Error boundary testado com component que joga exceção
- 2 exemplos funcionais na pasta

#### T2.7 [3h] Documentação `writing-a-view.md`

**Problema:** Pasta custom sem doc é feature invisível.

**Ação:**
1. Criar `docs/writing-a-view.md`:
   - Overview (por que Level 2.5)
   - Interface EntityViewProps completa
   - Quickstart 10min: exemplo simple
   - Best practices (Tailwind, responsividade, handle missing fields)
   - Sandboxing e security note (self-host only pra custom, SaaS futuro)
2. Adicionar link no README principal e no scenario editor UI

**DoD:**
- Doc explica em <15 min de leitura
- Reader externo escreve view minimal seguindo doc em <1h (validar informalmente)
- README linka

---

### FASE 3 — Scenario Editor UI (~15-20h)

O centro do produto — onde tudo se conecta.

#### T3.1 [4h] Preset picker + skeleton do editor

**Ação:**
1. Nova rota `/scenarios/new` com editor de 3 painéis:
   - Left: preset picker + list of fields
   - Right: live preview area (usando selected view)
   - Bottom: constraints + intent
2. Preset picker dropdown: fetch `GET /presets?domain={name}`, agrupado ("Card Game", "Creature RPG", etc.)
3. Escolher preset preenche todos os campos default
4. Botão "Start blank" ignora preset

**DoD:**
- Editor abre, presets listam, escolher preset preenche layout
- Testes Vitest

#### T3.2 [6h] Field builder — add/edit/remove/reorder fields

**Ação:**
1. Cada field é um card editável com:
   - Name (str input)
   - Kind (select: num, cat, bool, str, tag_set, map)
   - Kind-specific config: range (num), enum (cat/tag_set/map), min_len/max_len (str)
   - Botão delete
2. Botão "Add field" com dialog
3. Drag handle pra reorder (dnd-kit ou react-beautiful-dnd)
4. Preview atualiza live conforme user edita
5. Validação inline (name único, range válido, etc.)

**DoD:**
- Add/edit/remove/reorder funciona sem lag
- Validação impede submit inválido
- Preview reflete mudanças em <500ms
- Testes cobrem operações principais

#### T3.3 [3h] Visual variant picker + field mapping

**Ação:**
1. Dropdown "Layout style" mostra views aplicáveis ao domain + Custom section + Default (sempre)
2. Ao escolher, preview usa aquela variante
3. Se variante espera slots (name, cost, hp, etc.) que não batem com fields do schema, mostra "Field Mapping" panel:
   - Row por slot esperado
   - Select com fields do schema disponíveis
4. Mapping persistido no scenario config
5. Botão "Preview with example entity" gera 1 entity de exemplo (usando ranges do schema) e mostra no preview

**DoD:**
- Dropdown lista variantes corretas
- Mapping UI aparece só quando necessário
- Preview atualiza ao trocar variante ou mapping
- Testes cobrem cada caso

#### T3.4 [4h] Constraints editor

**Ação:**
1. Panel "Constraints" com lista + add button
2. Cada constraint tem: kind (range, sum_of_fields, forbidden_combo, required_tag, unique_across_set), params UI específico do kind
3. Constraints do preset carregados default
4. Visual feedback: constraint violation destacada em preview de sample entity

**DoD:**
- Todos 5 kinds do ConstraintEngine editáveis via UI
- Preview mostra violação em tempo real
- Testes

#### T3.5 [3h] Intent panel — sliders

**Ação:**
1. Painel "Generation Intent" com sliders:
   - Power scale (weak / average / strong) — 3 posições
   - Variety (uniform / mixed / experimental)
   - Complexity (simple / moderate / rich)
   - Theme adherence (loose / balanced / strict)
2. Textarea "Theme brief" pra prosa livre
3. Sliders traduzem em modificadores no prompt do Designer
4. Preview: "when you click Generate, LLM will receive: {schema} + {constraints} + {intent modifiers}"

**DoD:**
- Sliders funcionais
- Estado persiste em session state
- Preview mostra prompt final (debug view opcional)

#### T3.6 [2h] Generate button + preview antes de commit

**Ação:**
1. Botão "Preview 1 entity" gera **um** entity apenas (rápido, ~10s), mostra no preview
2. User pode "Try again" (regenerate) ou ajustar sliders/constraints
3. Botão "Generate N entities" faz o commit final (usa entities no scenario)
4. Loading state progressivo (SSE se der tempo)

**DoD:**
- Preview de 1 entity funciona
- Regenerate mantém seed configurável (reproducible)
- Generate final cria scenario válido

---

### FASE 4 — LLM Designer prompt tunado (~5-7h)

Prompts hoje otimizam validação. Precisa otimizar **qualidade**.

#### T4.1 [3h] Prompt do Designer com contexto full

**Ação:**
1. Reescrever system prompt do `LocalDesigner.design()`:
   - Instrução de dar nomes **temáticos** (não "Card-1", "Entity-A")
   - Instrução de **preencher todos os campos** (skills não pode ficar vazio)
   - Descrições ricas quando o field existe
   - Referência ao preset name (se scenario usa Hearthstone, mencionar tone Hearthstone)
   - Intent modifiers (weak/strong, uniform/varied, simple/rich) traduzem em instruções concretas
2. User prompt inclui:
   - Preset ref
   - Effective schema (com overrides)
   - Constraints em texto
   - Intent sliders traduzidos
   - 2-3 few-shot examples do preset (uma entity ilustrativa de cada)
3. `to_llm_schema()` marca **todos** os fields como `required` (não deixa LLM omitir)

**DoD:**
- Teste manual: gerar 5 cartas com preset Hearthstone e brief "aggro deck" → nomes temáticos ("Ember Warrior", não "Card-1"), skills preenchidas, descrições coerentes
- Comparação antes/depois documentada em `docs/experiments.md`

#### T4.2 [2h] Field completude enforcement

**Ação:**
1. Verificar `to_llm_schema()` — marcar required
2. Pós-validação: se LLM retorna entity com field faltando, adicionar ao retry feedback ("required field `skills` was missing, please include it")
3. Timeout mais generoso (60s) pra deixar LLM ter espaço de completar

**DoD:**
- Teste: mock LLM omite skills → sistema tenta 3x com feedback claro → retorna erro semanticamente útil
- Produção: <5% de entities faltando fields em amostra de 20

#### T4.3 [2h] Iterator com reasoning narrativo

**Ação:**
1. Prompt do Iterator inclui: "For each proposed change, provide reasoning in this format: (a) which entity is outlier and why, (b) which specific stat/field you'll adjust, (c) how much and why that amount, (d) which objective this addresses."
2. Cada `Modification.reasoning` fica com formato consistente
3. UI da timeline lê reasoning e exibe estruturado

**DoD:**
- Reasoning tem estrutura previsível
- UI parse e exibe legível
- Teste manual: 3 iterações consecutivas produzem reasonings distintos e coerentes

---

### FASE 5 — Preset content de qualidade (~5-8h)

Presets são o "gancho" do produto. Se preset ruim, produto parece amador.

#### T5.1 [3h] Pesquisar + escrever presets de card game

**Ação:**
Card game (arquivos em `presets/card_game/`):

**hearthstone.json:**
- Ranges: mana 0-10, HP 1-30, attack 0-16 (baseado em cards reais)
- Constraints: mana_curve realista, no more than X% legendary
- Objectives: winrate variance <15%, class balance
- Visual variant default: `card_game.hearthstone`
- 3 example entities (Bloodfen Raptor, Fireball, etc. — cards emblemáticos)

**mtg.json:**
- Ranges: mana cost 0-10 (multi-colored complexity anotada), power/toughness 0-15
- Constraints
- Objectives
- Default variant: mtg style (se implementar)
- Examples reais

**yugioh.json:**
- Ranges: LP 8000, ATK/DEF 0-5000, level 1-12
- Constraints
- Objectives
- Examples reais

**slay-the-spire.json** (opcional):
- Escalas menores, energy-based

**DoD:**
- Cada preset carrega sem erro
- Ranges e constraints baseados em jogos reais (documentar fontes)
- Teste: gerar entities com preset → resultado plausível pra alguém que joga o jogo

#### T5.2 [3h] Presets creature_rpg + team_composition

**Análogo:**
- `pokemon-gen1.json` — 15 tipos, stat ranges reais dos 151 originais, moves
- `monster-hunter.json` — sizes, weaknesses (fire/water/thunder/ice/dragon)
- `dark-souls.json` — resistances (fire/lightning/magic/dark), armor tier
- `software-team.json` — Junior/Mid/Senior/Lead + skills reais (backend/frontend/etc.)
- `consulting.json` — different seniority curve + client-facing skills
- `sports-team.json` — positions + stats

**DoD:** análogo

#### T5.3 [2h] Doc de "how presets work" pra developer

**Ação:**
Adicionar seção em `docs/writing-a-domain.md` (ou novo `docs/writing-a-preset.md`) explicando:
- Como criar preset novo
- Guidelines: baseado em real product/game, valores documentados
- Validation checklist antes de submeter

**DoD:**
- Doc claro
- Reader escreve preset em <30min

---

### FASE 6 — Polish final (~5h)

#### T6.1 [3h] Onboarding + example scenario

**Ação:**
1. Home detecta primeira visita
2. Hero: título + parágrafo + 2 botões: "Try example (Hearthstone-like)" e "Start from scratch"
3. Example scenario tem 10 cards pré-gerados via LLM (rodar 1x, salvar output no repo como fixture)
4. Guided tour opcional highlighting timeline, freshness, objectives (Intro.js ou similar)

**DoD:**
- First visit shows hero
- Example loads em <2s (fixture pré-computada)
- Tour dismissible

#### T6.2 [2h] Empty states + error boundaries generalizados

**Ação:**
1. Cada empty state ganha ilustração/emoji + microcopy + CTA relevante
2. Error boundaries em componentes principais (EntityEditor, MetricsPanel, DomainView) com "Try again" + toast
3. Custom view crash → fallback pro DefaultListView (already covered T2.6)

**DoD:**
- Nenhum empty state seco
- Errors não quebram app inteiro

---

## Resposta à Q1 do `docs/questions.md` (fidelidade categórica) — decidido: (B) escopada

Lida a Q1. Boa análise, mas a decisão é **(B) escopada**, não (A).

**Por que rejeitar (A):**
- (A) entrega presets fake: "Pokémon com 8 tipos" quando Pokémon tem 18, "MTG com engine's abilities" quando MTG tem burn/counter/mill/etc.
- Isso é exatamente o padrão que o humano vem rejeitando há vários dias: produto que quebra na primeira interação porque o headline promete X e entrega X-com-asterisco.
- Se um preset é "Pokémon", ele tem que ser Pokémon. Se for "Pokémon-scale mas tipos do engine", vira demo que enganamos usuário — não usável.

**(B) escopada — o que refactorar:**

Não abstrai tudo. Move o mapping enum→comportamento de código Python pra data JSON, com contorno curado:

### card_game — abilities como primitivas + renomeáveis

Manter conjunto fixo de primitivos no engine (deal_damage, heal, shield, draw + talvez add: buff, debuff, summon, transform pra cobrir MTG/YuGiOh). Preset pode:
- **Renomear** ("burn" no preset MTG = "deal_damage" internamente)
- **Selecionar subset** (Slay the Spire usa só damage+shield)
- **Não** cria efeitos novos via DSL — se o efeito não existe no engine, preset não pode usar

Preset JSON:
```json
"ability_kinds": {
  "burn": {"maps_to": "deal_damage", "display": "Burn"},
  "counterspell": {"maps_to": "shield", "display": "Counter"}
}
```

Simulator usa o `maps_to` interno; UI e LLM veem o `display`. Determinismo preservado.

### creature_rpg — matchup table como data

Refactor `matchups.json` já existe. Preset declara:
- Lista de types próprios (Pokémon: 18, Digimon: 10, MTG-colors: 5, Souls-like: fire/lightning/magic/dark)
- Matriz N×N de multiplicadores
- Type icons opcional (emoji/svg reference)

Simulator carrega o matchup do preset, computa via lookup. Zero código Python muda além de "ler do preset em vez de matchups.json fixo".

### team_composition — seniority como axis numérico

Seniority vira label arbitrário com peso numérico. Preset declara:
```json
"seniority_levels": [
  {"name": "intern", "speed_multiplier": 0.5},
  {"name": "junior", "speed_multiplier": 0.7},
  {"name": "staff", "speed_multiplier": 1.3},
  {"name": "principal", "speed_multiplier": 1.7}
]
```

Simulator lê speed pelo lookup do label. Testes existentes de determinismo continuam válidos.

### Escopo estimado

- card_game abilities refactor: ~4h (renomeação layer + selection filter)
- creature_rpg matchup from preset: ~4h (já está semi-separado em `matchups.json`; expandir pra vir do preset é pequeno)
- team_composition seniority declarativa: ~3h (mais simples dos três)
- Update `Preset` schema (Pydantic) pra aceitar esses campos: ~2h
- Testes: 3 novos casos por domain (~3h)
- Docs em `docs/writing-a-preset.md` sobre como declarar enums custom: ~2h

**Total adicionado: ~18h.** Trilha vira ~105-120h. Ainda cabe em 5 dias.

### Sequência

- **Fazer esse sub-épico ANTES de FASE 2 T5.1/T5.2 (preset content).** Ordem correta: primeiro dá capacidade do engine, depois escreve presets que exercitam essa capacidade. Se fizer preset primeiro, presets serão de novo aproximados e vai precisar retrabalho.
- **T2.1 (`DefaultListView`) e T2.2 (view registry) seguem em paralelo** — como você mesma sugeriu, são alicerce independente.
- **Após esse sub-épico completo:** T5.1 pode ter Hearthstone com 4 primitivos, MTG com 8 (burn/counter/mill/tutor/discard/lifegain/exile/damage), YuGiOh com seus specifics. T5.2 pode ter Pokémon-18-types, Digimon-10-attributes.

### Marcar como fase 1.5

Insira como **"FASE 1.5 — Enums declarativos por preset"** entre a FASE 1 (schema overrides) e FASE 2 (visual). Depois desse trabalho, o resto do escopo original executa normalmente.

Move `docs/questions.md` pra `docs/questions-archive/2026-07-13-q1-categorical-fidelity.md` após ler e prossegue.

---

## Diretiva sobre escopo

**Execute a trilha completa.** Todas as fases, todas as tasks, todas as DoDs. Não há autorização pra cortes preventivos — o budget de tempo comporta o escopo completo com folga.

Se algo travar tecnicamente (bug em dep externa, requisito ambíguo, DoD irrealista após leitura profunda do código), **escale ao humano imediatamente**. Nunca decida corte sozinho. O humano tem contexto sobre budget, prioridade cross-projeto e prazo — só ele pode aprovar reduções de escopo.

Comportamentos proibidos:
- "Vou fazer só 1 variante por domain em vez de 2 pra economizar tempo" ❌
- "3 presets por domain é muito, faço 2" ❌
- "Skip T4.3 reasoning narrativo, deixa como está" ❌
- "T3.5 intent sliders são polish, corto variety+complexity" ❌

Comportamentos corretos:
- "T2.3 HearthstoneStyle está em 8h (estimativa 5h), o retrieval de campo tá tricky — escalando pra decidir se continuo ou simplifico layout" ✅
- "Preset Yu-Gi-Oh requer entender X regra específica, não achei ref confiável — escalando pra humano pesquisar ou aceitar aproximação" ✅
- "Discovery de custom `.tsx` via `import.meta.glob` tem edge case com Turbopack — escalando pra confirmar fallback aceitável" ✅

**Presets, variantes e polish são features CENTRAIS do produto, não decoração.** Ship the whole thing.

---

## Coordenação com projeto irmão (Storyteller)

Instância do Storyteller está trabalhando em paralelo na trilha "usável single-user" (bug reflection, controls, memory inspector real, responsivo, tema, export). Zero coupling — containers isolados, mesmo llama-server.

Se você precisar de referência de padrão de UI (setup wizards, edit-inline patterns), inspire-se no Storyteller mas **não copie código** — projetos independentes.

## Verificação final da trilha

- [ ] `pytest` inteiro verde (backend, todos os testes atuais + novos)
- [ ] `pnpm test` verde (frontend Vitest)
- [ ] Manual test scenario:
  1. Abrir home fresh
  2. Clicar "Try Hearthstone example"
  3. Ver scenario carregado com 10 cards estilo Hearthstone
  4. Abrir Scenario Editor, mudar preset pra YuGiOh
  5. Ranges mudam automaticamente (HP → LP 8000, ATK/DEF sobem)
  6. Adicionar field `custom_effect` do tipo `str`
  7. Escolher visual variant
  8. Preview mostra 1 entity de amostra
  9. Ajustar constraints (max cost)
  10. Ajustar intent (power scale = strong)
  11. Generate 5 entities → recebe cards temáticos, nomes coerentes, campos completos, layout renderizado corretamente
  12. Timeline mostra evento com actor + reasoning legível
- [ ] `docs/product-audit.md` atualizado marcando issues fechados (3.1, 3.2, 3.3, 11.1, 11.2, 11.3, 2.1, 2.2, 1.1, 1.2, etc.)
- [ ] Screenshots atualizados no README com produto real

## Notas gerais

- Custo LLM: ~$0-2 (só rodar generation pra criar example scenario fixture, resto local)
- Timeline realista: ~85-100h (~2-3 semanas com bom ritmo)
- Se apertar, negocie escopo — nunca corte silenciosamente
- Após fim, mova este arquivo pra archive e reporte em `docs/session-report-2026-XX-XX.md`
- **Lembrete central:** o objetivo é produto que designer indie de card game consegue usar pra prototipar seriamente. Não bolha de portfólio. Cada decisão passa por esse filtro.
