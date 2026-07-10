"""Domain registry — auto-discovers plugins under ``domains/``.

A domain is any subpackage of ``domains`` whose ``__init__`` exposes ``get_simulator()``.
The core never names a domain explicitly; it discovers whatever is installed. This keeps
the "new domain = new plugin, same core" property: dropping a package in ``domains/`` with
a ``get_simulator`` makes it routable with no core changes.
"""

from __future__ import annotations

import importlib
import logging
import pkgutil

import domains
from core.simulator_interface import SimulatorInterface

logger = logging.getLogger(__name__)


def discover_domains() -> dict[str, SimulatorInterface]:
    """Import every ``domains.*`` subpackage and register those exposing ``get_simulator``."""
    registry: dict[str, SimulatorInterface] = {}
    for module in pkgutil.iter_modules(domains.__path__):
        if not module.ispkg:
            continue
        pkg = importlib.import_module(f"domains.{module.name}")
        factory = getattr(pkg, "get_simulator", None)
        if factory is None:
            logger.info("skipping domains.%s (no get_simulator)", module.name)
            continue
        registry[module.name] = factory()
        logger.info("registered domain: %s", module.name)
    return registry


class DomainRegistry:
    """Holds the discovered simulators; refreshable for tests."""

    def __init__(self) -> None:
        self._simulators: dict[str, SimulatorInterface] = {}

    def load(self) -> None:
        self._simulators = discover_domains()

    def names(self) -> list[str]:
        return sorted(self._simulators)

    def get(self, name: str) -> SimulatorInterface | None:
        return self._simulators.get(name)

    def all(self) -> dict[str, SimulatorInterface]:
        return dict(self._simulators)


registry = DomainRegistry()
