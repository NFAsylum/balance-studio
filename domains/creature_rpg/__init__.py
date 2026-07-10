"""Creature RPG domain plugin."""

from domains.creature_rpg.schema import get_schema, load_seed
from domains.creature_rpg.simulator import CreatureRpgSimulator


def get_simulator() -> CreatureRpgSimulator:
    """Entry point the core registry uses to load this domain's simulator."""
    return CreatureRpgSimulator()


__all__ = ["CreatureRpgSimulator", "get_simulator", "get_schema", "load_seed"]
