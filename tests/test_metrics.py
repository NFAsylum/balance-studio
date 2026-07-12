"""Tests for core.metrics — rating, distribution, aggregation, domain-agnosticism."""

import pathlib

import pytest

from core.metrics import (
    DurationStats,
    EloMmrRating,
    Metric,
    WinRateDistribution,
    aggregate_metrics,
)
from core.metrics.base import MetricResult
from core.simulator_interface import RunResult


def _match(a: str, b: str, winner: str | None, steps: int = 10, seed: int = 0) -> RunResult:
    return RunResult(
        entities_involved=[a, b],
        outcome={"winner": winner},
        duration_steps=steps,
        seed=seed,
    )


def test_metric_is_abstract():
    with pytest.raises(TypeError):
        Metric()  # type: ignore[abstract]


def test_elo_mmr_returns_entity_to_float_map():
    runs = [_match("a", "b", "a")]
    result = EloMmrRating().compute(runs)
    assert isinstance(result, MetricResult)
    assert result.kind == "rating"
    assert set(result.data) == {"a", "b"}
    assert all(isinstance(v, float) for v in result.data.values())
    # Winner gains, loser loses relative to the shared initial rating.
    assert result.data["a"] > 1500.0 > result.data["b"]


def test_elo_mmr_ranks_stronger_higher_over_100_runs():
    # 100 synthetic runs: "strong" wins 80%, deterministic pattern (every 5th goes to weak).
    runs = [_match("strong", "weak", "weak" if i % 5 == 0 else "strong", seed=i) for i in range(100)]
    ratings = EloMmrRating().compute(runs).data
    assert ratings["strong"] > ratings["weak"]


def test_elo_mmr_is_deterministic():
    runs = [_match("a", "b", "a" if i % 3 else "b", seed=i) for i in range(30)]
    assert EloMmrRating().compute(runs).data == EloMmrRating().compute(runs).data


def test_winrate_distribution_mean_std_and_per_entity():
    # a wins both its games, b loses both -> winrates 1.0 and 0.0, mean 0.5.
    runs = [_match("a", "b", "a"), _match("a", "b", "a")]
    data = WinRateDistribution().compute(runs).data
    assert data["per_entity"] == {"a": 1.0, "b": 0.0}
    assert data["mean"] == pytest.approx(0.5)
    assert data["std"] == pytest.approx(0.5)


def test_winrate_distribution_flags_outlier():
    # Nine evenly-matched entities near 0.5, one dominant "boss" at 1.0 -> boss is an outlier.
    runs = []
    pairs = [("p%d" % i, "p%d" % (i + 1)) for i in range(0, 8, 2)]
    for a, b in pairs:
        runs.append(_match(a, b, a))
        runs.append(_match(a, b, b))  # 50/50 among the normal pack
    for i in range(6):
        runs.append(_match("boss", "punching_bag_%d" % i, "boss"))
    data = WinRateDistribution().compute(runs).data
    assert "boss" in data["outliers"]


def test_duration_stats():
    runs = [_match("a", "b", "a", steps=s) for s in (4, 6, 8)]
    data = DurationStats().compute(runs).data
    assert data["mean"] == pytest.approx(6.0)
    assert data["min"] == 4 and data["max"] == 8


def test_aggregate_metrics_keys_by_name():
    runs = [_match("a", "b", "a")]
    results = aggregate_metrics([EloMmrRating(), WinRateDistribution()], runs)
    assert set(results) == {"elo_mmr", "winrate_distribution"}
    assert all(isinstance(r, MetricResult) for r in results.values())


def test_aggregate_metrics_rejects_duplicate_names():
    with pytest.raises(ValueError):
        aggregate_metrics([EloMmrRating(), EloMmrRating()], [])


def test_metrics_package_does_not_import_domains():
    metrics_dir = pathlib.Path(__file__).resolve().parents[1] / "core" / "metrics"
    for py in metrics_dir.glob("*.py"):
        source = py.read_text()
        assert "import domains" not in source
        assert "from domains" not in source
