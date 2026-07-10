"""Cache backend abstraction — one interface, swappable storage.

``diskcache`` (SQLite-backed file) is the dev backend; a Redis backend lands in Sprint 8
behind the same protocol. An in-memory backend is provided for tests. Keeping the interface
generic (bytes in/out, keyed by string) is what lets the sim cache be domain- and
storage-agnostic.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class CacheBackend(Protocol):
    def get(self, key: str) -> bytes | None: ...
    def set(self, key: str, value: bytes, ttl_seconds: int | None = None) -> None: ...
    def delete(self, key: str) -> None: ...
    def keys(self, prefix: str = "") -> list[str]: ...


class InMemoryCacheBackend:
    """Dict-backed backend for tests (TTL ignored)."""

    def __init__(self) -> None:
        self._store: dict[str, bytes] = {}

    def get(self, key: str) -> bytes | None:
        return self._store.get(key)

    def set(self, key: str, value: bytes, ttl_seconds: int | None = None) -> None:
        self._store[key] = value

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def keys(self, prefix: str = "") -> list[str]:
        return [k for k in self._store if k.startswith(prefix)]


class DiskCacheBackend:
    """diskcache-backed backend (dev). File lives under ``CACHE_DIR``."""

    def __init__(self, directory: str | Path = ".diskcache"):
        import diskcache

        self._cache = diskcache.Cache(str(directory))

    def get(self, key: str) -> bytes | None:
        return self._cache.get(key)

    def set(self, key: str, value: bytes, ttl_seconds: int | None = None) -> None:
        self._cache.set(key, value, expire=ttl_seconds)

    def delete(self, key: str) -> None:
        self._cache.delete(key)

    def keys(self, prefix: str = "") -> list[str]:
        return [k for k in self._cache.iterkeys() if isinstance(k, str) and k.startswith(prefix)]
