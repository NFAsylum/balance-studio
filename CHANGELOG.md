# Changelog

## v0.2-ip-clean (2026-07-13)

**IP hygiene — nominative fair use compliance.** No functional change to the engine, but two
things affect existing data:

### Breaking

- **Preset ids renamed** to generic descriptors (`hearthstone` → `modern-mana-tcg`,
  `mtg` → `multi-color-tcg`, `yugioh` → `high-scale-duel`, `slay-the-spire` → `energy-roguelike`,
  `pokemon-gen1` → `elemental-creatures-classic`, `dark-souls` → `soulslike-enemies`,
  `monster-hunter` → `giant-beast-hunt`). A scenario persisted with an old `preset_id` keeps
  working (the id is just a reference), but `GET /presets/<old-id>` now 404s — use the new id.
- **`multi-color-tcg` (ex-`mtg`) `ability_kind` enum renamed**: `burn`/`lifegain`/`counter`/
  `cantrip` → `direct_damage`/`restore_life`/`negate`/`card_draw`. A scenario created from that
  preset before this release stores the old enum values and will **fail schema validation** on
  reload. **Recreate any such scenario** (there are no persisted users yet).
- **Visual-variant ids renamed** (`card_game.hearthstone` → `card_game.modern-mana`,
  `card_game.yugioh` → `card_game.high-scale-duel`, `creature_rpg.pokedex` →
  `creature_rpg.elemental-classic`, `creature_rpg.monster-hunter` → `creature_rpg.giant-beast`).

### Other

- Preset `name`/`description` moved to nominative comparative use ("inspired by … like X"),
  no possessive/tagline/verbatim. Example-entity names are now original.
- Anti-infringement instruction added to the LLM Designer/Iterator prompts.
- `README` gains a `## Legal` non-affiliation notice; internal design docs get a factual disclaimer.
