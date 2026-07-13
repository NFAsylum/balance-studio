> **Note:** This document discusses design considerations that reference commercial games by name for comparative and structural purposes. See README `## Legal` section for full non-affiliation disclosure.

# Q2 — Post-PR#9 IP audit (2026-07-13)

**Trigger:** T-REV.2 of the PR-#9 review inbox. `gh pr list --state open` = only #9; PRs #2–#7 are all **merged**, so `main` (`0c4ef32`) now carries feature content (FASE 2 visual variants + FASE 5 example entities) that PR #9 — branched from a **pre-merge** `main` — never covered.

**Reading:** (a) confirmed — the PRs merged; PR #9 is **stale and incomplete** against current main. It renamed presets that main has since re-modified (added `examples`), so PR #9 is `mergeable_state=dirty`.

## Trademark/character matches on current main (43)

```
core/presets.py:10:is what makes YuGiOh (HP→5000, level 1-12) differ from Hearthstone (mana 0-10, hp 1-30) — but
domains/creature_rpg/simulator.py:45: # supplies its own type roster + matrix here (e.g. a Pokemon 18-type chart).
presets/card_game/hearthstone.json:2: "id": "hearthstone",
presets/card_game/hearthstone.json:3: "name": "Hearthstone",
presets/card_game/hearthstone.json:5: "description": "Blizzard's Hearthstone: minions on a 0-10 mana curve, health up to 30, attack up to ~16.",
presets/card_game/hearthstone.json:58: "default_visual_variant": "card_game.hearthstone",
presets/card_game/mtg.json:2: "id": "mtg",
presets/card_game/mtg.json:88: "name": "Serra Angel",
presets/card_game/slay-the-spire.json:3: "name": "Slay the Spire",
presets/card_game/yugioh.json:2: "id": "yugioh",
presets/card_game/yugioh.json:3: "name": "Yu-Gi-Oh!",
presets/card_game/yugioh.json:58: "default_visual_variant": "card_game.yugioh",
presets/card_game/yugioh.json:61: "name": "Blue-Eyes White Dragon",
presets/card_game/yugioh.json:70: "name": "Dark Magician",
presets/card_game/yugioh.json:79: "name": "Kuriboh",
presets/creature_rpg/dark-souls.json:2: "id": "dark-souls",
presets/creature_rpg/dark-souls.json:3: "name": "Dark Souls",
presets/creature_rpg/dark-souls.json:45: "name": "Ornstein",
presets/creature_rpg/dark-souls.json:58: "name": "Havel",
presets/creature_rpg/dark-souls.json:71: "name": "Sif",
presets/creature_rpg/monster-hunter.json:2: "id": "monster-hunter",
presets/creature_rpg/monster-hunter.json:3: "name": "Monster Hunter",
presets/creature_rpg/monster-hunter.json:42: "default_visual_variant": "creature_rpg.monster-hunter",
presets/creature_rpg/monster-hunter.json:45: "name": "Rathalos",
presets/creature_rpg/monster-hunter.json:60: "name": "Lagiacrus",
presets/creature_rpg/monster-hunter.json:74: "name": "Barroth",
presets/creature_rpg/pokemon-gen1.json:2: "id": "pokemon-gen1",
presets/creature_rpg/pokemon-gen1.json:3: "name": "Pokemon (Gen 1 stats, full type chart)",
presets/creature_rpg/pokemon-gen1.json:30: "description": "Pokemon type"
presets/creature_rpg/pokemon-gen1.json:457: "name": "Charizard",
presets/creature_rpg/pokemon-gen1.json:473: "name": "Blastoise",
presets/creature_rpg/pokemon-gen1.json:489: "name": "Venusaur",
tests/test_api_scenarios.py:149: resp = client.post("/scenarios", json={"domain": "card_game", "name": "Duel", "preset_id": "yugioh"})
tests/test_api_scenarios.py:152: assert resp.json()["preset_id"] == "yugioh"
tests/test_api_scenarios.py:153: assert resp.json()["visual_variant"] == "card_game.yugioh"
tests/test_api_scenarios.py:158: assert hp["range"] == [1, 5000] # yugioh rescaled DEF/HP
tests/test_api_scenarios.py:163: resp = client.post("/scenarios", json={"domain": "card_game", "preset_id": "hearthstone", "schema_overrides": over})
tests/test_api_scenarios.py:175: r = client.post("/scenarios", json={"domain": "card_game", "preset_id": "pokemon-gen1"})
tests/test_declarative_enums.py:88:def test_mtg_preset_carries_sim_config_and_renamed_enum(client):
tests/test_declarative_enums.py:89: resp = client.post("/scenarios", json={"domain": "card_game", "preset_id": "mtg"})
tests/test_presets.py:38: assert store.get("yugioh") is not None
tests/test_presets.py:44: yugioh = PresetStore().get("yugioh").apply_to(reg.get("card_game").entity_schema())
tests/test_presets.py:45: assert next(f for f in yugioh.fields if f.name == "hp").range == (1, 5000)
tests/test_presets.py:77: assert client.get("/presets/hearthstone").json()["id"] == "hearthstone"
tests/test_presets.py:92: pk = PresetStore().get("pokemon-gen1")
tests/test_scenario.py:89: log.init_scenario(Scenario(id="s1", domain="card_game", name="T", schema_overrides=ov, preset_id="yugioh"))
tests/test_scenario.py:91: assert reloaded.schema_overrides == ov and reloaded.preset_id == "yugioh"
ui/src/domain-views/SafeView.test.tsx:31: const ok = getViewById("card_game.hearthstone")!;
ui/src/domain-views/SafeView.test.tsx:33: expect(screen.getByTestId("hearthstone-card")).toBeInTheDocument();
ui/src/domain-views/card_game/HearthstoneStyle.tsx:6:/** Hearthstone-style minion card (vertical): mana gem top-left, attack + health at the
ui/src/domain-views/card_game/HearthstoneStyle.tsx:18: id: "card_game.hearthstone",
ui/src/domain-views/card_game/HearthstoneStyle.tsx:19: name: "Hearthstone",
ui/src/domain-views/card_game/HearthstoneStyle.tsx:34:export default function HearthstoneStyle({ entity, size = "md", mapping }: EntityViewProps) {
ui/src/domain-views/card_game/HearthstoneStyle.tsx:41: data-testid="hearthstone-card"
ui/src/domain-views/card_game/YuGiOhStyle.tsx:6:/** Yu-Gi-Oh-style monster card (landscape): gold name banner, level stars top-right, a big
ui/src/domain-views/card_game/YuGiOhStyle.tsx:18: id: "card_game.yugioh",
ui/src/domain-views/card_game/YuGiOhStyle.tsx:19: name: "Yu-Gi-Oh!",
ui/src/domain-views/card_game/YuGiOhStyle.tsx:33:export default function YuGiOhStyle({ entity, size = "md", mapping }: EntityViewProps) {
ui/src/domain-views/card_game/YuGiOhStyle.tsx:40: data-testid="yugioh-card"
ui/src/domain-views/card_game/cardviews.test.tsx:4:import HearthstoneStyle from "./HearthstoneStyle";
ui/src/domain-views/card_game/cardviews.test.tsx:5:import YuGiOhStyle from "./YuGiOhStyle";
ui/src/domain-views/card_game/cardviews.test.tsx:11: test("HearthstoneStyle shows name, mana, attack, health", () => {
ui/src/domain-views/card_game/cardviews.test.tsx:12: render(<HearthstoneStyle entity={CARD} schema={SCHEMA} />);
ui/src/domain-views/card_game/cardviews.test.tsx:13: expect(screen.getByTestId("hearthstone-card")).toBeInTheDocument();
ui/src/domain-views/card_game/cardviews.test.tsx:20: test("YuGiOhStyle shows name, ATK/DEF and level stars", () => {
ui/src/domain-views/card_game/cardviews.test.tsx:21: render(<YuGiOhStyle entity={CARD} schema={SCHEMA} />);
ui/src/domain-views/card_game/cardviews.test.tsx:29: render(<HearthstoneStyle entity={{}} schema={SCHEMA} />);
ui/src/domain-views/card_game/cardviews.test.tsx:30: render(<YuGiOhStyle entity={{}} schema={SCHEMA} />);
ui/src/domain-views/card_game/cardviews.test.tsx:31: expect(screen.getByTestId("hearthstone-card")).toBeInTheDocument();
ui/src/domain-views/card_game/cardviews.test.tsx:32: expect(screen.getByTestId("yugioh-card")).toBeInTheDocument();
ui/src/domain-views/creature_rpg/MonsterHunterStyle.tsx:6:/** Monster Hunter-style wiki entry (dark): a monster silhouette, a stat line, and
ui/src/domain-views/creature_rpg/MonsterHunterStyle.tsx:19: id: "creature_rpg.monster-hunter",
ui/src/domain-views/creature_rpg/MonsterHunterStyle.tsx:20: name: "Monster Hunter",
ui/src/domain-views/creature_rpg/MonsterHunterStyle.tsx:43: data-testid="monster-hunter-card"
ui/src/domain-views/creature_rpg/PokedexStyle.tsx:6:/** Pokedex-style entry (horizontal split): a big type emoji + type badge on the left, name,
ui/src/domain-views/creature_rpg/PokedexStyle.tsx:21: name: "Pokedex",
ui/src/domain-views/creature_rpg/PokedexStyle.tsx:50:export default function PokedexStyle({ entity, size = "md", mapping }: EntityViewProps) {
ui/src/domain-views/creature_rpg/creatureviews.test.tsx:5:import PokedexStyle from "./PokedexStyle";
ui/src/domain-views/creature_rpg/creatureviews.test.tsx:19: test("PokedexStyle shows name, type, stats and skills", () => {
ui/src/domain-views/creature_rpg/creatureviews.test.tsx:20: render(<PokedexStyle entity={CREATURE} schema={SCHEMA} />);
ui/src/domain-views/creature_rpg/creatureviews.test.tsx:30: expect(screen.getByTestId("monster-hunter-card")).toBeInTheDocument();
ui/src/domain-views/creature_rpg/creatureviews.test.tsx:37: render(<PokedexStyle entity={{}} schema={SCHEMA} />);
ui/src/domain-views/creature_rpg/creatureviews.test.tsx:40: expect(screen.getByTestId("monster-hunter-card")).toBeInTheDocument();
ui/src/domain-views/registry.ts:10:import HearthstoneStyle, { meta as hearthstoneMeta } from "./card_game/HearthstoneStyle";
ui/src/domain-views/registry.ts:11:import YuGiOhStyle, { meta as yugiohMeta } from "./card_game/YuGiOhStyle";
ui/src/domain-views/registry.ts:13:import PokedexStyle, { meta as pokedexMeta } from "./creature_rpg/PokedexStyle";
ui/src/domain-views/registry.ts:27: view(hearthstoneMeta, HearthstoneStyle),
ui/src/domain-views/registry.ts:28: view(yugiohMeta, YuGiOhStyle),
ui/src/domain-views/registry.ts:29: view(pokedexMeta, PokedexStyle),
ui/src/domain-views/types.ts:22: id: string; // e.g. "card_game.hearthstone", "custom.MyCard"
```

## Scope not covered by PR #9

- **Preset files on main are the OLD-named ones** (`hearthstone.json`, `mtg.json`, …) **with `examples` containing character names** (Charizard, Blue-Eyes White Dragon, Serra Angel, Rathalos, Ornstein, Sif, …). PR #9 renamed the *pre-example* versions → hard delete/modify conflict with main.
- **Visual variants** (`HearthstoneStyle.tsx`, `YuGiOhStyle.tsx`, `MonsterHunterStyle.tsx`, `PokedexStyle.tsx`) + `registry.ts` + `cardviews.test.tsx` — the T-IP.9 carve-out that T-REV.4 now **upgrades to HIGH**. Not on PR #9's base.
- **Core docstrings/comments** referencing Pokémon (`core/presets.py`, `domains/creature_rpg/simulator.py`).

## Decision needed (human)

PR #9 (from old main) cannot cleanly absorb this via merge — resolving would mean re-doing the deleted-vs-modified preset files by hand and layering the visual-variant + example-name cleanup, all **IP-sensitive conflicts** that T-REV.1 explicitly routes to escalation.

**Options:**
- **(A) Close PR #9; do one fresh comprehensive IP-hygiene pass on current main** — rename presets, originalise example character names, rename visual variants (T-REV.4), harden prompts, fix core comments, docs. One clean PR against the real trunk. *Recommended.*
- **(B) Salvage PR #9** — merge main in, resolve every IP-sensitive conflict by hand, then add the missing example/visual-variant scope. Messier; more conflict surface.
