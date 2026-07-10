"""Tests for core.sim_cache — cache hit/miss, partial reuse, invalidation, freshness."""

from core.cache_backend import InMemoryCacheBackend
from core.scenario import Event, EventLog, Scenario
from core.sim_cache import IncrementalSimRunner, SimCache, SimCacheEntry
from core.simulator_interface import RunResult
from domains.card_game.schema import get_schema
from domains.card_game.simulator import CardGameSimulator, MatchEnv


def _units(names):
    model = get_schema().build_model()
    return [
        model(name=n, cost=2, hp=8, damage=3, ability_kind="deal_damage", ability_value=2)
        for n in names
    ]


def _runner(tmp_path):
    log = EventLog(base_dir=tmp_path)
    log.init_scenario(Scenario(id="s1", domain="card_game", name="T"))
    cache = SimCache(InMemoryCacheBackend())
    runner = IncrementalSimRunner(CardGameSimulator(), cache, log)
    return log, cache, runner


def test_full_miss_then_hit(tmp_path):
    _, _, runner = _runner(tmp_path)
    env = MatchEnv(seed=1)
    units = _units(["A", "B", "C"])  # 3 pairs
    first = runner.run("s1", units, env, n_runs=30)
    assert first.matchups_computed == 3 and first.matchups_reused == 0

    second = runner.run("s1", units, env, n_runs=30)
    assert second.matchups_reused == 3 and second.matchups_computed == 0  # full cache hit


def test_partial_miss_reuses_shared_matchups(tmp_path):
    _, _, runner = _runner(tmp_path)
    env = MatchEnv(seed=1)
    runner.run("s1", _units(["A", "B", "C"]), env, n_runs=30)  # AB, AC, BC cached
    report = runner.run("s1", _units(["A", "B", "C", "D"]), env, n_runs=60)  # +AD, BD, CD
    assert report.matchups_reused == 3  # AB, AC, BC
    assert report.matchups_computed == 3  # AD, BD, CD


def test_invalidate_touching_removes_entity_matchups(tmp_path):
    _, cache, runner = _runner(tmp_path)
    env = MatchEnv(seed=1)
    runner.run("s1", _units(["A", "B", "C"]), env, n_runs=30)
    removed = cache.invalidate_touching({"A"})  # AB and AC involve A
    assert removed == 2

    report = runner.run("s1", _units(["A", "B", "C"]), env, n_runs=30)
    assert report.matchups_computed == 2  # AB, AC recomputed
    assert report.matchups_reused == 1  # BC survived


def test_edit_makes_cache_stale(tmp_path):
    log, cache, runner = _runner(tmp_path)
    env = MatchEnv(seed=1)
    runner.run("s1", _units(["A", "B"]), env, n_runs=20)  # 1 matchup cached at content_seq 0
    # a user entity edit advances the content clock -> the cached matchup is now stale
    log.append("s1", Event(actor="user", kind="edit_entity", target="A", after={"hp": 12}))
    report = runner.run("s1", _units(["A", "B"]), env, n_runs=20)
    assert report.matchups_computed == 1 and report.matchups_reused == 0


def test_freshness_tag():
    entry = SimCacheEntry(
        config_hash="h",
        entities_involved=["A"],
        kind="full",
        computed_at_seq=5,
        runs=[RunResult(entities_involved=["A", "B"], outcome={"winner": "A"}, duration_steps=3, seed=1)],
    )
    assert SimCache.freshness(entry, head_seq=5) == "full"
    assert SimCache.is_stale(entry, head_seq=6) is True
    assert SimCache.freshness(entry, head_seq=6) == "stale"
