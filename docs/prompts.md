# Prompts — Balance Studio

Templates iniciais. Iterar no Sprint 6. Cada prompt versionado.

## `core/prompts/entity_generation_base.txt` (v1)

Template base do `LlmGenerator`. Cada domain concatena seu fragmento específico (`SimulatorInterface.llm_generation_prompt`).

```
You are a game/product balance designer. Generate {n} candidate entities that satisfy the given schema and constraints.

<schema>
{entity_schema_description}
</schema>

<constraints>
{constraints_description}
</constraints>

<user_intent>
{user_intent}
</user_intent>

{seed_examples_block}

{domain_specific_fragment}

Rules:
- Each entity must be a valid instance of the schema
- Each entity must satisfy all constraints
- Entities in the batch should be diverse (do not generate near-duplicates)
- Use the provided tool to output. Do not include prose outside the tool call.
```

Formato de `seed_examples_block` quando existe:

```
Previous successful examples:
{example_1_json}
{example_2_json}
{example_3_json}
```

## `domains/card_game/prompt_fragment.txt` (v1)

Fragmento acoplado ao base pelo `CardGameSimulator.llm_generation_prompt`:

```
Domain: card game combat.
Each Unit has cost (mana to play), hp (life points), damage (per attack), and one ability.

Design guidelines:
- Cost 1 units: cheap and specialized (low hp OR low damage OR situational ability)
- Cost 5 units: powerful but slow (high hp AND high damage OR game-changing ability)
- Aggressive decks favor cost 1-3 with high damage per mana
- Control decks favor high hp + defensive abilities (shield, heal)
- Combo decks favor abilities that scale with other cards
- Avoid statically dominant units (a unit that beats every other unit)
```

## `domains/creature_rpg/prompt_fragment.txt` (v1)

```
Domain: creature RPG with type advantages.
Each Creature has type (fire, water, plant, ice, electric, ground, air, ghost), hp, atk, def, resistances (0.5x from listed types), and 2-4 skills.

Design guidelines:
- Balance offense and defense: total (hp + atk + def) roughly proportional to power tier
- Type advantages create rock-paper-scissors dynamic (fire > ice > plant > water > fire)
- Skills should reinforce or contrast the creature's type (e.g., a fire creature with a water skill is a specialist counter-pick)
- Resistances lower base damage taken but should not stack on top of already-strong type advantage
- No creature should be strictly better than another with equivalent cost
```

## `domains/team_composition/prompt_fragment.txt` (v1)

```
Domain: team member allocation.
Each Person has seniority (junior, mid, senior, lead), a set of skills, and preferred task types.

Design guidelines:
- Distribute seniority realistically: mostly mid, fewer seniors, few leads, some juniors
- Skills overlap between people to enable redundancy but keep some specialization
- Preferences influence assignment but do not dictate — a senior can do junior work
- Avoid single points of failure (skills only one person has)
- Realistic teams have complementary combinations, not clones
```

## `docs/prompts/judge_realism.txt` (v1)

Usado no Sprint 6 pra validar se LLM output tem sentido semântico.

```
You are validating whether a generated {domain} entity is realistic and useful for balance testing.

<entity>
{entity_json}
</entity>

Rate from 0 to 5:
- 0: nonsense (contradictory fields, absurd values)
- 1: technically valid but useless (extreme outlier)
- 2: bland (statistically average, no interesting design)
- 3: usable (fits the domain, has some character)
- 4: strong design (creates interesting decisions)
- 5: exemplary (would be a signature entity in a shipped product)

Output only the integer 0-5.
```

## Notas de iteração (Sprint 6)

Para cada domain, criar `docs/experiments.md` com:

```markdown
## card_game — v2 prompt
Data: YYYY-MM-DD
Mudança: added 3 seed examples + design guideline about "no statically dominant unit"
Hipótese: reduz frequência de LLM gerar 6/6/1cost unit

Método: 10 gerações consecutivas, mesma constraint (cost 1-3, aggro theme)
Resultado:
- valid rate: 8 of 10 (v1: 6 of 10)
- constraint satisfaction: 9 of 10 (v1: 7 of 10)
- realism score (LLM-judge): média 3.4 (v1: 2.8)
- avg cost per generation: $0.03 (v1: $0.02, +50% por seed examples adicionados)

Decisão: aceitar v2 pro card_game
```

## Regras para o Claude ao iterar

- Nunca mudar prompt e código lógico na mesma iteração — variável isolada
- Sempre rodar 10 gerações mínimo antes de declarar melhoria
- Reportar tradeoff de custo explicitamente (few-shot examples aumentam token count)
- Se um prompt novo quebra em outro domain, isolar por domain — cada domain tem seu fragment
- Nunca vazar terminologia de um domain no prompt de outro (creature RPG não menciona "cost", card game não menciona "seniority")
