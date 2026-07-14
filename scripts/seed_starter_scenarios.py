"""Seed a curated gallery of starter scenarios on a fresh install.

An empty scenario list makes Balance Studio read as a cold, abstract tool. This script pre-loads
a handful of ready-to-explore scenarios (built from existing presets, populated with the presets'
example entities) so the first run teaches by example instead of showing an empty state.

Idempotent by design: it seeds only when the store holds no scenarios, so it is safe to call on
every startup. Wire it into the API lifespan (gated by ``SEED_STARTERS``) or run it standalone::

    SCENARIOS_DIR=scenarios python -m scripts.seed_starter_scenarios

Names and briefs are deliberately trademark-free (see the project's IP-hygiene notes): they
describe the *balance question* each scenario poses, not a specific commercial game.
"""

from __future__ import annotations

import logging
import os
import uuid

from core.objectives import Objective
from core.presets import PresetStore
from core.scenario import Event, EventLog, Scenario

logger = logging.getLogger(__name__)


# (preset_id, scenario name, pedagogical brief) — one starter per entry, in gallery order.
STARTERS: list[tuple[str, str, str]] = [
    (
        "modern-mana-tcg",
        "Modern Mana: cost-curve dominance",
        "Cost-curve dominance test — on a 0-10 mana curve, is any single cost tier an outlier "
        "that wins far more than its neighbours?",
    ),
    (
        "high-scale-duel",
        "High-Scale Duel: high-ATK viability",
        "High-ATK monster viability in a high-scale duel format — do the biggest attackers "
        "dominate, or does the level/DEF spread keep them in check?",
    ),
    (
        "outpost-siege",
        "Outpost Siege: weapon vs. enemy dominance",
        "Shotgun vs. rifle vs. pistol dominance against a mixed enemy pool, plus an armored "
        "bruiser as a stress test — does one loadout trivialise the siege?",
    ),
    (
        "cover-firefight",
        "Cover Firefight: loadout tuning",
        "Insectoid waves against a cover-shooter loadout — is the heavy weapon overpowered "
        "given its wielder's low HP, or is the risk/reward balanced?",
    ),
    (
        "elemental-creatures-classic",
        "Elemental Classic: type-effectiveness check",
        "Does a strong fire-type creature dominate the roster, or does the 18-type effectiveness "
        "chart keep it honest?",
    ),
]


def seed_starter_scenarios(
    event_log: EventLog,
    registry: object,
    presets: PresetStore | None = None,
) -> list[str]:
    """Create the starter scenarios if the store is empty; return the created scenario ids.

    ``registry`` is any object exposing ``get(domain) -> simulator`` (duck-typed, so this stays
    decoupled from the API registry). No-op (returns ``[]``) when any scenario already exists.
    """
    if event_log.list_scenarios():  # idempotent: never touch a non-empty store
        return []

    presets = presets or PresetStore()
    created: list[str] = []

    for preset_id, name, brief in STARTERS:
        preset = presets.get(preset_id)
        if preset is None:
            logger.warning("starter skipped — preset %r not found", preset_id)
            continue
        simulator = registry.get(preset.domain)  # type: ignore[attr-defined]
        if simulator is None:
            logger.warning("starter skipped — domain %r not registered", preset.domain)
            continue

        model = simulator.entity_schema().with_overrides(preset.schema_overrides).build_model()
        try:
            entities = [model(**ex).model_dump() for ex in preset.examples]
        except Exception:  # noqa: BLE001 - a malformed example must not abort the whole seed
            logger.exception("starter skipped — preset %r has an example invalid for its schema", preset_id)
            continue
        if not entities:
            logger.warning("starter skipped — preset %r ships no example entities", preset_id)
            continue

        scenario = Scenario(
            id=uuid.uuid4().hex[:12],
            domain=preset.domain,
            name=name,
            brief=brief,
            n_entities=max(len(entities), 8),
            preset_id=preset.id,
            schema_overrides=preset.schema_overrides,
            constraints=preset.default_constraints,
            sim_config=preset.sim_config,
            visual_variant=preset.default_visual_variant,
            objectives=[Objective(**o) for o in preset.default_objectives],
        )
        event_log.init_scenario(scenario)
        event_log.append_many(
            scenario.id,
            [Event(actor="user", kind="create_entity", target=e["name"], after=e) for e in entities],
        )
        created.append(scenario.id)
        logger.info("seeded starter %r (%s) with %d entities", name, scenario.id, len(entities))

    return created


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    from api.registry import registry

    registry.load()
    event_log = EventLog(base_dir=os.getenv("SCENARIOS_DIR", "scenarios"))
    ids = seed_starter_scenarios(event_log, registry)
    print(f"seeded {len(ids)} starter scenario(s): {ids}" if ids else "store not empty — nothing seeded")


if __name__ == "__main__":
    main()
