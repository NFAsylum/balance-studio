"""Creature RPG simulator — deterministic 1v1 battles, gauntlet and tournament modes.

A battle is pure: given two creatures and a turn limit it always yields the same result
(there is no in-battle RNG). Randomness only picks gauntlet opponents, seeded by the env.
Each turn both creatures pick their highest-power ready skill; the two actions resolve in
skill-priority order; a used skill goes on cooldown. Damage scales attack vs defense and is
multiplied by type effectiveness (the creature's ``resistances`` override the matchup table).
"""

from __future__ import annotations

import itertools
import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from core.entity_schema import EntitySchema
from core.metrics import DurationStats, EloMmrRating, WinRateDistribution
from core.metrics.base import Metric
from core.simulator_interface import Environment, RunResult, SimulatorInterface
from domains.creature_rpg.schema import SKILLS_BY_NAME, Skill, get_schema

_MATCHUPS_PATH = Path(__file__).with_name("matchups.json")


def load_matchups() -> dict[str, dict[str, float]]:
    """Load the pluggable type-effectiveness table (attacker -> defender -> multiplier)."""
    return json.loads(_MATCHUPS_PATH.read_text())


class GauntletEnv(Environment):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["gauntlet", "tournament"] = "gauntlet"
    n_battles: int = 10  # gauntlet: opponents faced per creature
    turn_limit: int = 50
    subset_size: int | None = None  # tournament: cap the field


@dataclass
class _CreatureState:
    name: str
    ctype: str
    hp: float
    max_hp: float
    atk: float
    defense: float
    resistances: dict[str, float]
    skills: list[Skill]
    cooldowns: dict[str, int] = field(default_factory=dict)


def _to_dict(creature: Any) -> dict[str, Any]:
    return creature.model_dump() if isinstance(creature, BaseModel) else dict(creature)


def _state(data: dict[str, Any]) -> _CreatureState:
    skills = [SKILLS_BY_NAME[name] for name in data["skills"] if name in SKILLS_BY_NAME]
    return _CreatureState(
        name=data["name"],
        ctype=data["type"],
        hp=float(data["hp"]),
        max_hp=float(data["hp"]),
        atk=float(data["atk"]),
        defense=float(data["defense"]),
        resistances=dict(data.get("resistances", {})),
        skills=skills,
    )


def _effectiveness(matchups: dict[str, dict[str, float]], skill_type: str, defender: _CreatureState) -> float:
    if skill_type in defender.resistances:
        return defender.resistances[skill_type]
    return matchups.get(skill_type, {}).get(defender.ctype, 1.0)


def _pick_skill(state: _CreatureState) -> Skill | None:
    ready = [s for s in state.skills if state.cooldowns.get(s.name, 0) == 0]
    if not ready:
        return None
    return max(ready, key=lambda s: (s.power, s.name))


def _damage(attacker: _CreatureState, defender: _CreatureState, skill: Skill, matchups) -> float:
    base = skill.power * (attacker.atk / (attacker.atk + defender.defense))
    return base * _effectiveness(matchups, skill.type, defender)


class CreatureRpgSimulator(SimulatorInterface):
    def __init__(self) -> None:
        self.matchup_table = load_matchups()

    def entity_schema(self) -> EntitySchema:
        return get_schema()

    def environment_schema(self) -> type[Environment]:
        return GauntletEnv

    def default_metrics(self) -> list[Metric]:
        return [EloMmrRating(), WinRateDistribution(), DurationStats()]

    def llm_generation_prompt(self, constraints: list[Any]) -> str:
        return (
            "You are designing creatures for a type-based RPG. Spread creatures across the 8 "
            "types, keep stat totals comparable across types, give each 2-4 skills (prefer "
            "at least one of its own type), and avoid one type dominating the matchup ring."
        )

    def run(self, entities: list[Any], env: Environment) -> RunResult:
        if len(entities) != 2:
            raise ValueError(f"a creature battle needs exactly 2 creatures, got {len(entities)}")
        turn_limit = env.turn_limit if isinstance(env, GauntletEnv) else 50
        return self._battle(_to_dict(entities[0]), _to_dict(entities[1]), turn_limit, env.seed)

    def matchups(self, entities: list[BaseModel]) -> list[list[BaseModel]]:
        return [[entities[i], entities[j]] for i, j in itertools.combinations(range(len(entities)), 2)]

    def run_batch(self, entities: list[Any], env: Environment, n_runs: int) -> list[RunResult]:
        # Battles are deterministic, so a pair yields one result; a full set defaults to a tournament.
        if len(entities) == 2:
            return [self.run(entities, env)]
        return self.tournament(entities, env)

    # -- domain modes ------------------------------------------------------

    def gauntlet(self, creatures: list[Any], env: GauntletEnv) -> list[RunResult]:
        """Each creature faces ``env.n_battles`` random opponents (seeded)."""
        rng = random.Random(env.seed)
        data = [_to_dict(c) for c in creatures]
        runs: list[RunResult] = []
        for creature in data:
            others = [o for o in data if o["name"] != creature["name"]]
            opponents = rng.sample(others, min(env.n_battles, len(others)))
            for opponent in opponents:
                runs.append(self._battle(creature, opponent, env.turn_limit, env.seed))
        return runs

    def tournament(self, creatures: list[Any], env: GauntletEnv | Environment) -> list[RunResult]:
        """Round-robin over the field (optionally capped by ``subset_size``)."""
        data = [_to_dict(c) for c in creatures]
        subset = getattr(env, "subset_size", None)
        if subset is not None:
            data = data[:subset]
        turn_limit = getattr(env, "turn_limit", 50)
        return [
            self._battle(data[i], data[j], turn_limit, env.seed)
            for i, j in itertools.combinations(range(len(data)), 2)
        ]

    # -- battle engine -----------------------------------------------------

    def _battle(self, a: dict[str, Any], b: dict[str, Any], turn_limit: int, seed: int) -> RunResult:
        state_a, state_b = _state(a), _state(b)
        turns = 0
        winner: str | None = None

        while turns < turn_limit:
            turns += 1
            for state in (state_a, state_b):
                for name in list(state.cooldowns):
                    state.cooldowns[name] = max(0, state.cooldowns[name] - 1)

            skill_a, skill_b = _pick_skill(state_a), _pick_skill(state_b)
            actions = [(state_a, state_b, skill_a), (state_b, state_a, skill_b)]
            # Higher priority acts first; ties broken by atk then name (deterministic).
            actions.sort(key=lambda x: (-(x[2].priority if x[2] else -1), -x[0].atk, x[0].name))

            for attacker, defender, skill in actions:
                if skill is None:
                    continue
                defender.hp -= _damage(attacker, defender, skill, self.matchup_table)
                attacker.cooldowns[skill.name] = skill.cooldown
                if defender.hp <= 0:
                    winner = attacker.name
                    break
            if winner is not None:
                break

        if winner is None:
            winner = self._winner_by_hp(state_a, state_b)

        return RunResult(
            entities_involved=[state_a.name, state_b.name],
            outcome={
                "winner": winner,
                "turns": turns,
                "hp": {state_a.name: state_a.hp, state_b.name: state_b.hp},
            },
            duration_steps=turns,
            seed=seed,
        )

    @staticmethod
    def _winner_by_hp(a: _CreatureState, b: _CreatureState) -> str | None:
        frac_a, frac_b = a.hp / a.max_hp, b.hp / b.max_hp
        if frac_a > frac_b:
            return a.name
        if frac_b > frac_a:
            return b.name
        return None
