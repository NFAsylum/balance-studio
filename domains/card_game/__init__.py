"""Card game domain plugin."""

from domains.card_game.simulator import CardGameSimulator
from domains.card_game.schema import get_schema, load_seed


def get_simulator() -> CardGameSimulator:
    """Entry point the core registry uses to load this domain's simulator."""
    return CardGameSimulator()


__all__ = ["CardGameSimulator", "get_simulator", "get_schema", "load_seed"]
