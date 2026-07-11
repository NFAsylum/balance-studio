"""Contract tests for CacheBackend — same suite runs against every backend (Disk, Redis later)."""

import pytest

from core.cache_backend import (
    CacheBackend,
    DiskCacheBackend,
    InMemoryCacheBackend,
    RedisCacheBackend,
)


@pytest.fixture(params=["memory", "disk", "redis"])
def backend(request, tmp_path) -> CacheBackend:
    if request.param == "memory":
        return InMemoryCacheBackend()
    if request.param == "disk":
        return DiskCacheBackend(directory=tmp_path / "dc")
    # Redis backend exercised against fakeredis — proves it satisfies the same contract
    # without a live server (real REDIS_URL swaps in for prod).
    import fakeredis

    return RedisCacheBackend(client=fakeredis.FakeStrictRedis())


def test_set_get_round_trip(backend):
    backend.set("a", b"hello")
    assert backend.get("a") == b"hello"


def test_missing_key_returns_none(backend):
    assert backend.get("nope") is None


def test_delete(backend):
    backend.set("a", b"x")
    backend.delete("a")
    assert backend.get("a") is None
    backend.delete("a")  # deleting a missing key is a no-op


def test_keys_prefix_filter(backend):
    backend.set("sim:1", b"x")
    backend.set("sim:2", b"y")
    backend.set("idx:A", b"z")
    assert sorted(backend.keys("sim:")) == ["sim:1", "sim:2"]
    assert backend.keys("idx:") == ["idx:A"]


def test_satisfies_protocol(backend):
    assert isinstance(backend, CacheBackend)
