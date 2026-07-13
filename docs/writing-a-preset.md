# Writing a preset

A **preset** is a ready-made scenario starting point for a domain — a real game or team, not
"example values". It seeds the schema (via overrides), constraints, objectives, the default
visual variant, and — when the domain simulator supports it — declarative enums. Files live in
`presets/<domain>/<id>.json` and are served by `GET /presets`.

## Anatomy

```jsonc
{
  "id": "hearthstone",                    // unique; the filename stem
  "name": "Hearthstone",                  // label in the picker
  "domain": "card_game",                  // must match the folder
  "description": "…",
  "schema_overrides": { "fields": [ … ] },// edits on the plugin schema (ranges/enums/add/remove)
  "sim_config": { … },                    // declarative env config (see below)
  "default_constraints": [ … ],           // ConstraintEngine constraints
  "default_objectives": [ … ],            // Objective list
  "default_visual_variant": "card_game.hearthstone",
  "examples": [ … ]                       // illustrative real entities (few-shot / reference)
}
```

## Guidelines

- **Base it on a real product/game.** Ranges and constraints should come from the actual game;
  document the source in `description`. E.g. Hearthstone mana 0-10 / health 1-30; Yu-Gi-Oh
  level 1-12 / ATK-DEF 0-5000; Pokemon Gen-1 base stats ~5-190.
- **Rescale numbers freely.** `schema_overrides` on `num` fields is always safe.
- **Declarative enums** (needs the simulator's support — see `docs/architecture.md`):
  - `card_game`: `sim_config.ability_map` renames/curates ability primitives (MTG
    `"burn" → "deal_damage"`). Override the `ability_kind` enum to your names in `schema_overrides`.
  - `creature_rpg`: `sim_config.type_matchup` supplies your own type roster + N×N chart (the
    Pokemon preset ships the full 18-type chart). Override `type` and `resistances` enums to match.
  - `team_composition`: `sim_config.seniority_speed` declares your ladder → speed multiplier.
  Empty `sim_config` = the plugin default; determinism is preserved either way.
- **`examples`** are 2-3 emblematic entities (real cards/creatures). They must validate against
  the effective schema — the preset test enforces this. They double as few-shot material.

## Validation checklist

- [ ] `GET /presets/{id}` loads without error (structure + domain/folder match).
- [ ] `preset.apply_to(base_schema)` succeeds (overrides valid for the real schema).
- [ ] Every `examples` entity validates against the effective schema.
- [ ] Numeric ranges and constraints reflect the real game (source noted in `description`).
- [ ] If you declared a custom enum, its `sim_config` matches (matchup covers your types, etc.).

`tests/test_presets.py` checks load + apply + examples for every shipped preset, so a bad
preset fails CI immediately.
