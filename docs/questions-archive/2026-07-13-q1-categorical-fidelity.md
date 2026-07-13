# Questions for the human (Balance Studio)

Perguntas abertas que precisam da sua decisão. Responda inline (ou no chat) e eu sigo.

---

## Q1 — Fidelidade categórica vs. simulador determinístico (bloqueia parte da FASE 2/T5)

**Data:** 2026-07-13 · **Contexto:** trilha do Scenario Editor, fim da FASE 1 (PR #2).

### O achado

Lendo o código a fundo: os **simuladores hardcodam os enums categóricos** de cada domínio —
- `creature_rpg`: `type` tem uma tabela de **matchup** fixa (fire/water/plant/…, 8 tipos);
- `card_game`: `ability_kind` tem **efeitos** implementados (deal_damage/heal/shield/draw);
- `team_composition`: `seniority` mapeia **velocidade** (junior/mid/senior/lead).

Presets e overrides **reescalam ranges numéricos e adicionam campos livremente** — é isso que
faz YuGiOh (HP→5000, level 1-12) diferir de Hearthstone (mana 0-10, hp 1-30). Mas **trocar
aqueles enums** (ex.: os 15 tipos do Pokémon do T5.2) **quebraria a simulação determinística**,
que é o núcleo de credibilidade do framework ("ganhou 62% dos matches" é ground truth).

### O que NÃO está bloqueado

- Reescalar números (o headline "muda preset → ranges mudam") — **funciona 100%**.
- As **variantes visuais da FASE 2** (Pokédex, Hearthstone, etc.) — renderizam os campos
  existentes; só a paleta de *tipos* fica sendo a do engine (8 elementos), não os 15 do Pokémon.

### A decisão

- **(A) — recomendada.** Aceitar range-rescaling + enums do engine. Sigo a FASE 2 assim, sem
  tocar nos simuladores. Entrega o produto usável sem arriscar o determinismo. O T5.2
  ("Pokémon 15 types") vira "Pokémon-scale stats com os tipos do engine".
- **(B).** Fidelidade categórica entra no escopo (15 tipos, enums arbitrários por preset).
  Isso exige **mudar os simuladores** (matchup dinâmico, efeitos genéricos, velocidade por
  enum) — um sub-épico novo que eu **estimo e escalo antes** de executar.

**Minha recomendação:** (A). Posso seguir a FASE 2 já com (A) — T2.1 (`DefaultListView`) e T2.2
(view registry) são o alicerce e independem dessa escolha.

**Sua resposta:**
