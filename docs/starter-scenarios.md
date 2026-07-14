# Starter scenarios

Balance Studio ships a small **starter gallery** so a fresh install opens on real, explorable
work instead of an empty state. On startup, when the scenario store is empty *and*
`SEED_STARTERS=1` is set, the API seeds the scenarios below (see
`scripts/seed_starter_scenarios.py`). Seeding is **idempotent** — it never touches a store that
already holds scenarios — so it is safe to leave enabled.

Each starter is built from an existing preset and pre-populated with that preset's example
entities, so every card/creature is already designed. From there the usual loop applies: run
`simulate`, read the metrics, then let the iterator (or you) tune for balance.

| Scenario | Preset | Domain | What it explores |
|---|---|---|---|
| **Modern Mana: cost-curve dominance** | `modern-mana-tcg` | card_game | Whether any single cost tier on a 0–10 mana curve is an outlier that wins far more than its neighbours. |
| **High-Scale Duel: high-ATK viability** | `high-scale-duel` | card_game | Whether the biggest attackers dominate a high-scale duel format, or the level/DEF spread keeps them in check. |
| **Outpost Siege: weapon vs. enemy dominance** | `outpost-siege` | creature_rpg | Shotgun vs. rifle vs. pistol against a mixed enemy pool, with an armored bruiser as a stress test — does one loadout trivialise the siege? |
| **Cover Firefight: loadout tuning** | `cover-firefight` | creature_rpg | Insectoid waves against a cover-shooter loadout — is the heavy weapon overpowered given its wielder's low HP? |
| **Elemental Classic: type-effectiveness check** | `elemental-creatures-classic` | creature_rpg | Whether a strong fire-type creature dominates, or the 18-type effectiveness chart keeps it honest. |

Names and briefs describe the **balance question** each scenario poses rather than any specific
commercial game, in line with the project's IP-hygiene stance (see the README's *Legal* note).

## Enabling / running

```bash
# Automatic on a fresh backend:
SEED_STARTERS=1 poetry run uvicorn api.main:app --port 8000

# Or standalone against the configured store:
SCENARIOS_DIR=scenarios poetry run python -m scripts.seed_starter_scenarios
```

`SEED_STARTERS` defaults to off so automated tests (which assume an empty store) are unaffected.
To reseed from scratch, clear the `scenarios/` directory and start again.
