"""Tests for domains.creature_rpg.metrics — tiers, dominance, usage coverage."""

from core.simulator_interface import RunResult
from domains.creature_rpg.metrics import DominanceIndex, TierEmergence, UsageCoverage


def _match(a, b, winner):
    return RunResult(entities_involved=[a, b], outcome={"winner": winner}, duration_steps=5, seed=1)


def _skewed_runs():
    """A dominates, then a descending ladder of win rates."""
    runs = []
    # A beats everyone (5-0), B beats C/D/E, C beats D/E, D beats E, E loses all
    ladder = ["A", "B", "C", "D", "E"]
    for i, strong in enumerate(ladder):
        for weak in ladder[i + 1 :]:
            runs.append(_match(strong, weak, strong))  # higher in ladder wins
    return runs


def test_tier_emergence_ranks_into_tiers():
    result = TierEmergence().compute(_skewed_runs())
    assert result.kind == "tier"
    by_entity = result.data["by_entity"]
    # A (best win rate) lands in S; E (worst) in the lowest tier present
    assert by_entity["A"] == "S"
    assert by_entity["E"] == "D"
    # every entity is placed in exactly one tier
    placed = [e for tier in result.data["tiers"].values() for e in tier]
    assert sorted(placed) == ["A", "B", "C", "D", "E"]


def test_dominance_index_high_when_top_wins():
    # 'boss' wins many decisive matches -> high dominance
    runs = [_match("boss", f"mook{i}", "boss") for i in range(9)]
    runs.append(_match("mook0", "mook1", "mook0"))
    result = DominanceIndex(top_fraction=0.2).compute(runs)
    assert result.kind == "index"
    assert result.data["dominance_index"] >= 0.8
    assert "boss" in result.data["top_entities"]


def test_usage_coverage_counts_by_threshold():
    runs = [_match("A", "B", "A"), _match("A", "C", "A")]  # A:2, B:1, C:1
    covered_all = UsageCoverage(min_matches=1).compute(runs).data
    assert covered_all["covered"] == 3 and covered_all["total"] == 3
    covered_2 = UsageCoverage(min_matches=2).compute(runs).data
    assert covered_2["covered"] == 1  # only A appears in >= 2 matches


def test_metrics_read_only_generic_runresult_fields():
    # These metrics must not depend on creature-specific data — plain ids suffice.
    runs = [_match("x", "y", "x")]
    for metric in (TierEmergence(), DominanceIndex(), UsageCoverage()):
        result = metric.compute(runs)
        assert result.name and isinstance(result.data, dict)
