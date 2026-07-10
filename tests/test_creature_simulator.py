"""Tests for domains.creature_rpg.simulator — battle, modes, determinism, matchups, cooldown."""

from core.simulator_interface import Environment, RunResult
from domains.creature_rpg.schema import get_schema, load_seed
from domains.creature_rpg.simulator import CreatureRpgSimulator, GauntletEnv


def _creature(name, ctype, hp=100, atk=80, defense=40, skills=None, resistances=None):
    model = get_schema().build_model()
    return model(
        name=name,
        type=ctype,
        hp=hp,
        atk=atk,
        defense=defense,
        skills=skills or [f"{ctype}_strike", f"{ctype}_burst"],
        resistances=resistances or {},
    )


def test_run_returns_runresult():
    sim = CreatureRpgSimulator()
    assert issubclass(sim.environment_schema(), Environment)
    result = sim.run([_creature("A", "fire"), _creature("B", "plant")], GauntletEnv(seed=1))
    assert isinstance(result, RunResult)
    assert result.outcome["winner"] in ("A", "B", None)


def test_battle_is_deterministic():
    sim = CreatureRpgSimulator()
    a, b = _creature("A", "fire"), _creature("B", "water")
    results = [sim.run([a, b], GauntletEnv(seed=7)) for _ in range(5)]
    assert len({r.outcome["winner"] for r in results}) == 1
    assert len({r.outcome["turns"] for r in results}) == 1


def test_type_advantage_wins():
    # fire is super-effective vs water's counter... use the ring: fire beats water.
    sim = CreatureRpgSimulator()
    strong = _creature("Fire", "fire", skills=["fire_burst", "fire_strike"])
    weak = _creature("Water", "water", skills=["water_strike"])
    # identical stats; fire's super-effective damage should win
    result = sim.run([strong, weak], GauntletEnv(seed=1))
    assert result.outcome["winner"] == "Fire"


def test_resistances_override_matchup():
    sim = CreatureRpgSimulator()
    attacker = _creature("Atk", "fire", skills=["fire_burst"])
    # defender resists fire heavily (0.1) despite the base table
    resistant = _creature("Def", "water", hp=100, skills=["water_strike"], resistances={"fire": 0.1})
    normal = _creature("Def", "water", hp=100, skills=["water_strike"])
    r_res = sim.run([attacker, resistant], GauntletEnv(seed=1, turn_limit=3))
    r_norm = sim.run([attacker, normal], GauntletEnv(seed=1, turn_limit=3))
    # the resistant defender keeps more HP after the same number of turns
    assert r_res.outcome["hp"]["Def"] > r_norm.outcome["hp"]["Def"]


def test_cooldown_limits_burst_reuse():
    # burst has cooldown 2; over 3 turns a lone burst-user can fire it at most twice.
    sim = CreatureRpgSimulator()
    # a tanky defender so the battle lasts the full turn limit
    attacker = _creature("A", "fire", atk=60, skills=["fire_burst"])  # only burst
    tank = _creature("B", "plant", hp=300, defense=120, skills=["plant_strike"])
    result = sim.run([attacker, tank], GauntletEnv(seed=1, turn_limit=3))
    # burst on turn 1, cooldown turns 2-3 -> can't have killed via spam; battle reaches limit
    assert result.outcome["turns"] == 3


def test_gauntlet_mode():
    sim = CreatureRpgSimulator()
    creatures = load_seed()[:10]
    runs = sim.gauntlet(creatures, GauntletEnv(seed=42, mode="gauntlet", n_battles=5))
    assert len(runs) == 10 * 5  # each creature faces 5 opponents
    # deterministic
    runs2 = sim.gauntlet(creatures, GauntletEnv(seed=42, mode="gauntlet", n_battles=5))
    assert [r.outcome for r in runs] == [r.outcome for r in runs2]


def test_tournament_mode_round_robin():
    sim = CreatureRpgSimulator()
    creatures = load_seed()[:6]
    runs = sim.tournament(creatures, GauntletEnv(seed=1, mode="tournament"))
    assert len(runs) == 15  # C(6,2)
