"""Card game simulator — deterministic turn-based 1v1 combat.

Two decks fight. Each side has a hero with HP; a side loses when its hero reaches 0.
The only randomness is the seeded deck shuffle, so a given ``(decks, seed)`` always
produces the same match — a hard requirement for reproducible balance experiments.

Rules summary:
- Mana starts at ``mana_per_turn`` and grows by ``mana_per_turn`` each of a player's turns,
  capped at ``mana_cap``. Unspent mana does not carry over.
- At the start of a turn the active player draws one card (hand capped at ``hand_size``).
- Play phase: the active player repeatedly plays the leftmost affordable unit until none
  is affordable. Each unit's ability triggers as it is played, in play order.
- Combat phase: each of the active player's board units attacks the opponent's front unit
  (shield absorbs first, then HP); a unit at HP <= 0 is removed. With no enemy units, the
  attack hits the enemy hero.
- The game ends at a lethal hero or when ``turn_limit`` global turns elapse (then the higher
  hero HP wins; equal HP is a draw).

Abilities (trigger on play):
- ``deal_damage``: burn the enemy hero for ``ability_value``.
- ``heal``: restore the active hero by ``ability_value`` (capped at starting hero HP).
- ``shield``: give the just-played unit ``ability_value`` shield.
- ``draw``: draw ``ability_value`` cards from the active player's deck.
- ``none``: no effect.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict

from core.entity_schema import EntitySchema
from core.metrics import DurationStats, EloMmrRating, WinRateDistribution
from core.metrics.base import Metric
from core.simulator_interface import Environment, RunResult, SimulatorInterface
from domains.card_game.schema import get_schema


class MatchEnv(Environment):
    """Environment for a single card game match."""

    model_config = ConfigDict(extra="forbid")

    hand_size: int = 5
    turn_limit: int = 50
    hero_hp: int = 30
    mana_cap: int = 10
    mana_per_turn: int = 1


class Deck(BaseModel):
    """A named pile of units. Not an EntitySchema entity — just a run-time container."""

    model_config = ConfigDict(extra="forbid")

    id: str
    units: list[dict[str, Any]]


# -- internal mutable state ----------------------------------------------


@dataclass
class _UnitState:
    name: str
    hp: float
    damage: float
    ability_kind: str
    ability_value: float
    shield: float = 0.0


@dataclass
class _PlayerState:
    id: str
    hero_hp: float
    hero_hp_max: float
    draw_pile: list[dict[str, Any]]
    hand: list[dict[str, Any]] = field(default_factory=list)
    board: list[_UnitState] = field(default_factory=list)
    mana: int = 0
    turns_taken: int = 0
    damage_dealt: float = 0.0


def _to_unit_dict(unit: Any) -> dict[str, Any]:
    """Normalise a unit given as a Pydantic model or a plain dict into a dict."""
    if isinstance(unit, BaseModel):
        return unit.model_dump()
    if isinstance(unit, dict):
        return dict(unit)
    raise TypeError(f"unit must be a dict or BaseModel, got {type(unit)!r}")


def _coerce_deck(entity: Any, index: int) -> Deck:
    """Accept a Deck, a ``{id, units}`` dict, or a bare list of units."""
    if isinstance(entity, Deck):
        return entity
    if isinstance(entity, dict) and "units" in entity:
        return Deck(id=str(entity.get("id", f"deck_{index}")), units=[_to_unit_dict(u) for u in entity["units"]])
    if isinstance(entity, list):
        return Deck(id=f"deck_{index}", units=[_to_unit_dict(u) for u in entity])
    raise TypeError(f"entity {index} is not a deck (got {type(entity)!r})")


class CardGameSimulator(SimulatorInterface):
    """Runs deterministic 1v1 matches between two decks of :class:`Unit`."""

    def entity_schema(self) -> EntitySchema:
        return get_schema()

    def environment_schema(self) -> type[Environment]:
        return MatchEnv

    def default_metrics(self) -> list[Metric]:
        return [EloMmrRating(), WinRateDistribution(), DurationStats()]

    def llm_generation_prompt(self, constraints: list[Any]) -> str:
        return (
            "You are designing units for a turn-based 1v1 card game. A good unit set is "
            "diverse across archetypes (aggro: cheap, high damage; control: durable, heal/"
            "shield; combo: card draw). Keep power roughly proportional to cost. Abilities "
            "must be one of: none, deal_damage, heal, shield, draw. Respect all constraints."
        )

    def run(self, entities: list[Any], env: Environment) -> RunResult:
        if len(entities) != 2:
            raise ValueError(f"card game needs exactly 2 decks, got {len(entities)}")
        if not isinstance(env, MatchEnv):
            env = MatchEnv(**env.model_dump())
        deck_a = _coerce_deck(entities[0], 0)
        deck_b = _coerce_deck(entities[1], 1)
        return _Match(deck_a, deck_b, env).play()


class _Match:
    """One match instance. Holds all mutable state for a single ``play()``."""

    def __init__(self, deck_a: Deck, deck_b: Deck, env: MatchEnv):
        self.env = env
        self.rng = random.Random(env.seed)
        self.players = [self._make_player(deck_a), self._make_player(deck_b)]

    def _make_player(self, deck: Deck) -> _PlayerState:
        pile = list(deck.units)
        self.rng.shuffle(pile)
        player = _PlayerState(
            id=deck.id,
            hero_hp=float(self.env.hero_hp),
            hero_hp_max=float(self.env.hero_hp),
            draw_pile=pile,
        )
        for _ in range(self.env.hand_size):
            self._draw(player)
        return player

    def _draw(self, player: _PlayerState) -> None:
        if player.draw_pile and len(player.hand) < self.env.hand_size:
            player.hand.append(player.draw_pile.pop(0))

    def play(self) -> RunResult:
        turns = 0
        active_idx = 0
        winner: str | None = None

        while turns < self.env.turn_limit:
            active = self.players[active_idx]
            opponent = self.players[1 - active_idx]
            turns += 1
            active.turns_taken += 1
            active.mana = min(self.env.mana_cap, active.turns_taken * self.env.mana_per_turn)
            self._draw(active)
            self._play_phase(active, opponent)
            self._combat_phase(active, opponent)
            if opponent.hero_hp <= 0:
                winner = active.id
                break
            active_idx = 1 - active_idx

        if winner is None:
            winner = self._winner_on_hp()

        a, b = self.players
        return RunResult(
            entities_involved=[a.id, b.id],
            outcome={
                "winner": winner,
                "turns": turns,
                "damage_dealt": {a.id: a.damage_dealt, b.id: b.damage_dealt},
                "final_hero_hp": {a.id: a.hero_hp, b.id: b.hero_hp},
            },
            duration_steps=turns,
            seed=self.env.seed,
        )

    def _winner_on_hp(self) -> str | None:
        a, b = self.players
        if a.hero_hp > b.hero_hp:
            return a.id
        if b.hero_hp > a.hero_hp:
            return b.id
        return None  # draw

    def _play_phase(self, active: _PlayerState, opponent: _PlayerState) -> None:
        while True:
            idx = next(
                (i for i, card in enumerate(active.hand) if card["cost"] <= active.mana),
                None,
            )
            if idx is None:
                return
            card = active.hand.pop(idx)
            active.mana -= card["cost"]
            unit = _UnitState(
                name=card["name"],
                hp=float(card["hp"]),
                damage=float(card["damage"]),
                ability_kind=card["ability_kind"],
                ability_value=float(card["ability_value"]),
            )
            active.board.append(unit)
            _trigger_ability(unit, active, opponent, self)

    def _combat_phase(self, active: _PlayerState, opponent: _PlayerState) -> None:
        # Attackers are never removed during their own combat, so iterate a snapshot.
        for attacker in list(active.board):
            if opponent.board:
                target = opponent.board[0]
                _apply_damage_to_unit(target, attacker.damage)
                active.damage_dealt += attacker.damage
                if target.hp <= 0:
                    opponent.board.pop(0)  # HP zero = remove
            else:
                opponent.hero_hp -= attacker.damage
                active.damage_dealt += attacker.damage


def _apply_damage_to_unit(unit: _UnitState, amount: float) -> None:
    absorbed = min(unit.shield, amount)
    unit.shield -= absorbed
    unit.hp -= amount - absorbed


def _trigger_ability(
    unit: _UnitState, active: _PlayerState, opponent: _PlayerState, match: _Match
) -> None:
    """Apply a unit's on-play ability. Kept module-level so tests can exercise each kind."""
    kind, value = unit.ability_kind, unit.ability_value
    if kind == "deal_damage":
        if opponent.board:
            target = opponent.board[0]
            _apply_damage_to_unit(target, value)
            if target.hp <= 0:
                opponent.board.pop(0)
        else:
            opponent.hero_hp -= value
        active.damage_dealt += value
    elif kind == "heal":
        active.hero_hp = min(active.hero_hp_max, active.hero_hp + value)
    elif kind == "shield":
        unit.shield += value
    elif kind == "draw":
        for _ in range(int(value)):
            match._draw(active)
    # "none" -> no effect
