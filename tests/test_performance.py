"""Performance benchmarks + regression guards (Sprint 4 B4.4).

Thresholds are the DoD targets, which the single-threaded implementation beats by a wide
margin (see docs/performance.md). They fail only on a catastrophic regression, never on
per-machine noise.
"""

import random
import time

from core.cache_backend import InMemoryCacheBackend
from core.parallel_runner import run_matches_parallel
from core.scenario import EventLog, Scenario
from core.sim_cache import IncrementalSimRunner, SimCache
from domains.card_game.schema import load_seed as card_seed
from domains.card_game.simulator import CardGameSimulator, Deck, MatchEnv
from domains.creature_rpg.schema import load_seed as creature_seed
from domains.creature_rpg.simulator import CreatureRpgSimulator, GauntletEnv


def test_creature_gauntlet_100x1000_under_30s():
    sim = CreatureRpgSimulator()
    creatures = creature_seed()  # 100
    start = time.perf_counter()
    runs = sim.gauntlet(creatures, GauntletEnv(seed=42, n_battles=10))  # 100 * 10 = 1000
    elapsed = time.perf_counter() - start
    assert len(runs) == 1000
    assert elapsed < 30.0, f"gauntlet took {elapsed:.2f}s (target <30s)"


def test_creature_quick_estimate_under_2s():
    sim = CreatureRpgSimulator()
    start = time.perf_counter()
    sim.gauntlet(creature_seed(), GauntletEnv(seed=1, n_battles=1))  # quick: 100 battles
    assert time.perf_counter() - start < 2.0


def test_card_500_pool_1000_matches_under_60s():
    sim = CardGameSimulator()
    base = [u.model_dump() for u in card_seed()]
    cards = [{**base[i % len(base)], "name": f"c{i}"} for i in range(500)]
    rng = random.Random(1)
    start = time.perf_counter()
    for k in range(1000):
        a, b = rng.sample(range(500), 2)
        sim.run(
            [Deck(id=cards[a]["name"], units=[cards[a]]), Deck(id=cards[b]["name"], units=[cards[b]])],
            MatchEnv(seed=k),
        )
    assert time.perf_counter() - start < 60.0


def test_parallel_matches_match_serial():
    sim = CreatureRpgSimulator()
    creatures = creature_seed()[:12]
    matchups = sim.matchups(creatures)
    env = GauntletEnv(seed=3)
    serial = [sim.run(m, env) for m in matchups]
    parallel = run_matches_parallel(sim, matchups, env, max_workers=4)
    # order-preserving and identical outcomes
    assert [r.outcome for r in parallel] == [r.outcome for r in serial]


def test_cache_hit_repeat_under_100ms(tmp_path):
    log = EventLog(base_dir=tmp_path)
    log.init_scenario(Scenario(id="s1", domain="creature_rpg", name="perf"))
    runner = IncrementalSimRunner(CreatureRpgSimulator(), SimCache(InMemoryCacheBackend()), log)
    creatures = creature_seed()[:20]  # C(20,2) = 190 matchups
    env = GauntletEnv(seed=1)

    runner.run("s1", creatures, env, n_runs=190)  # cold: compute all
    start = time.perf_counter()
    report = runner.run("s1", creatures, env, n_runs=190)  # warm: full cache hit
    elapsed = time.perf_counter() - start
    assert report.matchups_computed == 0 and report.matchups_reused == 190
    assert elapsed < 0.1, f"cache hit took {elapsed * 1000:.1f}ms (target <100ms)"
