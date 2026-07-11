"""Team composition domain plugin (extensibility demo)."""

from domains.team_composition.schema import get_schema, load_seed
from domains.team_composition.simulator import TeamCompositionSimulator


def get_simulator() -> TeamCompositionSimulator:
    """Entry point the core registry uses to load this domain's simulator."""
    return TeamCompositionSimulator()


__all__ = ["TeamCompositionSimulator", "get_simulator", "get_schema", "load_seed"]
