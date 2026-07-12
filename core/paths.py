"""Centralised ID validation — the defence against path traversal (audit #01).

``scenario_id`` and ``branch_id`` become filesystem path components (``<base>/<scenario_id>/``,
``<branch_id>-seq-N.json.zst``). A value like ``../etc`` or ``..`` would escape the base dir,
letting an HTTP client read/write arbitrary files under (or above) the mounted volume.

Two layers, both cheap:

1. A strict whitelist regex — ``..``, ``/``, ``\\``, ``~``, ``%``, and non-ASCII all fail it.
2. ``safe_under`` re-resolves the composed path and asserts it stays inside its base
   (defence in depth, in case a caller forgets to validate).
"""

from __future__ import annotations

import re
from pathlib import Path

# No ``.`` in the class, so ``..`` (and any dot-only value) is rejected outright.
_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class InvalidId(ValueError):
    """Raised when a scenario/branch id fails validation. Mapped to HTTP 422 by the API."""


def validate_id(value: str, kind: str = "id") -> str:
    """Return ``value`` unchanged if it is a safe path component, else raise ``InvalidId``."""
    if not isinstance(value, str) or not _SAFE_ID.match(value):
        raise InvalidId(f"invalid {kind}: {value!r} (must match {_SAFE_ID.pattern})")
    return value


def safe_under(base: Path, *parts: str) -> Path:
    """Join ``parts`` under ``base`` and assert the resolved path stays inside ``base``."""
    base_resolved = base.resolve()
    joined = base.joinpath(*parts).resolve()
    if joined != base_resolved and not joined.is_relative_to(base_resolved):
        raise InvalidId(f"path escapes base: {parts!r}")
    return joined
