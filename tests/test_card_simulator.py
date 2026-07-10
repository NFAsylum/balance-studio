"""Tests for domains.card_game.simulator — determinism, abilities, and draw edge case."""

from core.simulator_interface import Environment, RunResult
from domains.card_game.schema import load_seed
from domains.card_game.simulator import (
    CardGameSimulator,
    Deck,
    MatchEnv,
    _Match,
    _PlayerState,
    _trigger_ability,
    _UnitState,
)


def _unit(name="u", cost=1, hp=5, damage=1, ability_kind="none", ability_value=0):
    return {
        "name": name,
        "cost": cost,
        "hp": hp,
        "damage": damage,
        "ability_kind": ability_kind,
        "ability_value": ability_value,
    }


def _player(hero_hp=30, hero_hp_max=30):
    return _PlayerState(id="p", hero_hp=hero_hp, hero_hp_max=hero_hp_max, draw_pile=[])


# -- interface ------------------------------------------------------------


def test_run_returns_runresult_and_env_is_matchenv():
    sim = CardGameSimulator()
    assert issubclass(sim.environment_schema(), Environment)
    assert sim.entity_schema().name == "Unit"
    assert len(sim.default_metrics()) == 3
    result = sim.run(
        [Deck(id="a", units=[_unit(damage=3)]), Deck(id="b", units=[])],
        MatchEnv(seed=42, turn_limit=10),
    )
    assert isinstance(result, RunResult)
    assert result.entities_involved == ["a", "b"]


# -- determinism ----------------------------------------------------------


def test_same_seed_same_result_five_times():
    units = [u.model_dump() for u in load_seed()]
    deck_a = Deck(id="a", units=units[:5])
    deck_b = Deck(id="b", units=units[5:])
    sim = CardGameSimulator()
    results = [sim.run([deck_a, deck_b], MatchEnv(seed=42)) for _ in range(5)]
    winners = {r.outcome["winner"] for r in results}
    turns = {r.outcome["turns"] for r in results}
    assert len(winners) == 1
    assert len(turns) == 1


def test_different_seed_can_differ():
    units = [u.model_dump() for u in load_seed()]
    deck_a, deck_b = Deck(id="a", units=units[:5]), Deck(id="b", units=units[5:])
    sim = CardGameSimulator()
    r1 = sim.run([deck_a, deck_b], MatchEnv(seed=1))
    r2 = sim.run([deck_a, deck_b], MatchEnv(seed=2))
    # Not asserting they differ (could coincide), just that both are valid runs.
    assert r1.seed == 1 and r2.seed == 2


# -- each ability ---------------------------------------------------------


def test_ability_deal_damage_burns_hero():
    active, opp = _player(), _player()
    unit = _UnitState(name="burn", hp=1, damage=0, ability_kind="deal_damage", ability_value=7)
    _trigger_ability(unit, active, opp, None)
    assert opp.hero_hp == 23
    assert active.damage_dealt == 7


def test_ability_deal_damage_hits_front_unit_if_present():
    active, opp = _player(), _player()
    blocker = _UnitState(name="blk", hp=5, damage=0, ability_kind="none", ability_value=0)
    opp.board.append(blocker)
    unit = _UnitState(name="burn", hp=1, damage=0, ability_kind="deal_damage", ability_value=3)
    _trigger_ability(unit, active, opp, None)
    assert blocker.hp == 2
    assert opp.hero_hp == 30  # hero untouched while a unit blocks


def test_ability_heal_restores_capped_at_max():
    active = _player(hero_hp=10, hero_hp_max=30)
    unit = _UnitState(name="medic", hp=1, damage=0, ability_kind="heal", ability_value=5)
    _trigger_ability(unit, active, _player(), None)
    assert active.hero_hp == 15
    active.hero_hp = 28
    _trigger_ability(unit, active, _player(), None)
    assert active.hero_hp == 30  # capped, no overheal


def test_ability_shield_buffs_the_unit():
    unit = _UnitState(name="guard", hp=5, damage=0, ability_kind="shield", ability_value=4)
    _trigger_ability(unit, _player(), _player(), None)
    assert unit.shield == 4


def test_ability_draw_pulls_cards():
    units = [_unit(name=f"u{i}") for i in range(10)]
    match = _Match(Deck(id="a", units=units), Deck(id="b", units=[]), MatchEnv(seed=3, hand_size=5))
    active = match.players[0]
    # After setup: hand full (5), pile has 5. Simulate having played 3 cards.
    del active.hand[:3]
    assert len(active.hand) == 2 and len(active.draw_pile) == 5
    unit = _UnitState(name="scholar", hp=1, damage=0, ability_kind="draw", ability_value=2)
    _trigger_ability(unit, active, match.players[1], match)
    assert len(active.hand) == 4
    assert len(active.draw_pile) == 3


# -- combat / removal -----------------------------------------------------


def test_unit_at_zero_hp_is_removed_in_combat():
    # White-box: a hitter attacks a fragile blocker that dies and is removed from the board.
    match = _Match(Deck(id="a", units=[]), Deck(id="b", units=[]), MatchEnv(seed=1))
    active, opponent = match.players
    active.board.append(_UnitState(name="hitter", hp=5, damage=9, ability_kind="none", ability_value=0))
    opponent.board.append(_UnitState(name="chump", hp=3, damage=0, ability_kind="none", ability_value=0))
    match._combat_phase(active, opponent)
    assert opponent.board == []  # HP hit zero -> removed
    assert active.damage_dealt == 9


def test_shield_absorbs_before_hp_in_combat():
    match = _Match(Deck(id="a", units=[]), Deck(id="b", units=[]), MatchEnv(seed=1))
    active, opponent = match.players
    active.board.append(_UnitState(name="hitter", hp=5, damage=4, ability_kind="none", ability_value=0))
    guarded = _UnitState(name="guard", hp=5, damage=0, ability_kind="none", ability_value=0, shield=3)
    opponent.board.append(guarded)
    match._combat_phase(active, opponent)
    # 4 damage: 3 absorbed by shield, 1 to hp -> survives at hp 4, shield 0.
    assert guarded.shield == 0 and guarded.hp == 4
    assert guarded in opponent.board


# -- draw / tie edge case -------------------------------------------------


def test_empty_decks_end_in_draw():
    sim = CardGameSimulator()
    result = sim.run([Deck(id="a", units=[]), Deck(id="b", units=[])], MatchEnv(seed=7, turn_limit=8))
    assert result.outcome["winner"] is None
    assert result.outcome["turns"] == 8
    assert result.outcome["final_hero_hp"] == {"a": 30, "b": 30}


def test_decisive_game_has_a_winner():
    sim = CardGameSimulator()
    strong = Deck(id="a", units=[_unit(name="beater", cost=1, hp=10, damage=8) for _ in range(3)])
    weak = Deck(id="b", units=[])
    result = sim.run([strong, weak], MatchEnv(seed=2, turn_limit=50))
    assert result.outcome["winner"] == "a"
