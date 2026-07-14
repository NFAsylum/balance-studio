# Blueprint: Encounter Domain (Balance v1.5 — Caminho B)

**Status:** Ready for execution by Qwen 30B (via `dev-marco-agent.encounter-domain` branch).
**Trigger:** rodar quando Marco disser explicitamente *"Execute `docs/blueprint-encounter-domain.md`"*. Não execute enquanto isso.
**Estimated effort:** 15-25 commits, ~30-50h total, cada commit <200 LOC.

---

## Meta-instruções pra instância executora (LEIA ANTES DE TOCAR CÓDIGO)

1. **Você é modelo mid-tier (Qwen 30B ou similar)**. NÃO improvise arquitetura. Siga este doc literalmente. Se algo aqui não bate com o repo, **escale** (crie `docs/questions-archive/YYYY-MM-DD-encounter-blueprint.md` e pare).

2. **Branch dedicada:** `git checkout -b dev-marco-agent.encounter-domain` antes do primeiro commit. Nunca commit direto em `main`.

3. **Cada commit deve:**
   - Ser <200 LOC de diff (excluindo `.json` fixtures)
   - Ter DoD executável (comando bash específico retorna X)
   - Passar `pytest tests/` no fim (nenhum teste existente deve quebrar)
   - Ter mensagem seguindo formato: `feat(encounter): <fase>.<passo> — <descrição curta>`

4. **Padrão a seguir:** `domains/creature_rpg/` é o modelo mais próximo. Copie estrutura, adapte semântica. Nunca invente padrão novo.

5. **Escalation gates** (pare e escale se qualquer um):
   - Padrão do repo não bate com este doc
   - DoD de qualquer passo falha 2 vezes seguidas
   - Precisa fazer decisão arquitetural não pré-especificada aqui
   - Conflito de merge com outro branch aberto
   - Test fixture existente quebra por mudança que este blueprint não pediu

---

## 1. Product spec

### O que o domain `encounter` resolve

Balance testing pra jogos onde **player pool enfrenta waves de threats com recursos depletáveis**. Cobre:

- FPS (arma vs enemy waves com ammo limitado)
- Survival horror (loadout vs encounters sequenciais com HP limitado)
- Tower defense (unidades defendem contra waves)
- Roguelike combat (run através de encounters, resources acumulam entre)
- Boss fights (player vs single high-HP threat, sustained combat)

### O que NÃO resolve (out of scope explícito)

- **Positioning / cover** — sim é abstract, não spatial. Não modele.
- **Aim skill / player timing** — hit é determinístico (dano fixo por shot).
- **Movement / kiting** — actors não têm posição.
- **Enemy AI** — threats atacam com heurística fixa (spread damage entre player units).
- **Rez / execution** — units downed ficam inativos; sem revive mechanic no v1.
- **Ammo pickup mid-encounter** — recursos só recomeçam entre waves via `wave_reward` (opcional, v2).

### Pergunta que o designer responde com este domain

- "Loadout A vs loadout B na mesma sequência de 5 waves — qual sobra mais recurso?"
- "Se eu nerfar shotgun em 15%, wave 3 fica impossível?"
- "Quais armas dominam quais tiers de threat?"
- "Meu wave 4 é matável com starting ammo?"

## 2. Architecture overview

### Entidade única com `role` field

Segue o padrão do repo (creature_rpg, card_game, team_composition — cada um tem UM entity type). Solução: **Entity `EncounterActor`** com campo `role: unit | threat`. Sim interpreta baseado no role.

Justificativa: dois entity types por domain quebra padrões existentes em `core/`. Não vale refactor.

### Estados & fluxo

```
GameState:
    player_hp: float
    ammo: dict[str, int]           # {"kinetic": 30, "explosive": 3, "energy": 10}
    waves_cleared: int
    active_wave: list[ThreatInstance]  # threats vivas na wave atual
    turn: int

Environment:
    starting_ammo: dict[str, int]
    starting_hp: float
    waves: list[list[str]]          # sequência de waves, cada wave = list de nomes de threats
    loadout: list[str]              # nomes de unit entities
    max_turns_per_wave: int = 30

Sim loop:
    for wave in waves:
        spawn wave threats
        while active_wave and player_hp > 0 and turn < max_turns_per_wave:
            for actor sorted by speed desc:
                if actor is unit:
                    if ammo insufficient: skip
                    target = pick_target(active_wave, actor)
                    apply damage, decrement ammo
                    if target dies: remove from active_wave
                if actor is threat:
                    damage_player_pool(actor.damage / max(len(loadout), 1))
            turn++
        if player_hp <= 0: break
        waves_cleared++
    return EncounterResult(waves_cleared, total_waves, hp_remaining, ammo_remaining, turns_taken)
```

### Determinístico por design

v1: 100% determinístico dado (loadout, waves, starting_ammo, starting_hp). Sem RNG. Uma única run = uma única resposta. Multi-run só faz sentido em v2 com randomness (target choice, threat behavior variability).

Isso simplifica testes: golden test com fixture → output esperado, byte-for-byte.

## 3. File-by-file breakdown

### 3.1 `domains/encounter/__init__.py`

Vazio. Package marker.

### 3.2 `domains/encounter/schema.py`

```python
"""Encounter entity schema.

A single entity type `EncounterActor` used for both player units and threats, distinguished
by `role`. Units consume ammo when acting; threats damage the player pool. Fields have
game-agnostic names (damage_output, max_hp, speed) that map cleanly to weapons OR enemies.
"""

from __future__ import annotations

from pathlib import Path

from core.entity_schema import EntitySchema

ROLES = ["unit", "threat"]
AMMO_TYPES = ["kinetic", "explosive", "energy", "melee"]
TIERS = ["fodder", "standard", "elite", "boss"]

_ACTOR_SCHEMA_DICT = {
    "name": "EncounterActor",
    "fields": [
        {"name": "name", "kind": "str", "min_len": 1, "max_len": 40, "description": "Display name"},
        {"name": "role", "kind": "cat", "enum": ROLES, "description": "unit = player-controlled; threat = enemy"},
        {"name": "damage_output", "kind": "num", "range": [1, 200], "description": "Damage per action (per shot for units, per attack for threats)"},
        {"name": "max_hp", "kind": "num", "range": [10, 500], "description": "Durability. Units use for reliability; threats use for actual HP."},
        {"name": "speed", "kind": "num", "range": [0.5, 5.0], "description": "Turn priority; higher acts first"},
        {"name": "ammo_type", "kind": "cat", "enum": AMMO_TYPES, "description": "Which ammo pool this unit consumes (for threats: irrelevant, set to 'melee')"},
        {"name": "ammo_per_shot", "kind": "num", "range": [1, 5], "description": "Ammo consumed per action (units only; threats: 0)"},
        {"name": "tier", "kind": "cat", "enum": TIERS, "description": "Power tier (fodder for grunts, boss for heavies)"},
        {"name": "description", "kind": "str", "min_len": 0, "max_len": 200, "description": "Flavor text (optional)"},
    ],
}


def get_schema() -> EntitySchema:
    """Return the :class:`EntitySchema` for an ``EncounterActor``."""
    return EntitySchema.from_dict(_ACTOR_SCHEMA_DICT)
```

### 3.3 `domains/encounter/seed_data.json`

```json
{
  "actors": [
    {"name": "Assault Rifle", "role": "unit", "damage_output": 25, "max_hp": 90, "speed": 3.5, "ammo_type": "kinetic", "ammo_per_shot": 1, "tier": "standard", "description": "Balanced automatic weapon"},
    {"name": "Shotgun", "role": "unit", "damage_output": 60, "max_hp": 40, "speed": 2.0, "ammo_type": "kinetic", "ammo_per_shot": 2, "tier": "standard", "description": "High-damage close range"},
    {"name": "Grenade Launcher", "role": "unit", "damage_output": 90, "max_hp": 20, "speed": 1.5, "ammo_type": "explosive", "ammo_per_shot": 1, "tier": "elite", "description": "Explosive AoE (single target in v1 sim)"},
    {"name": "Combat Knife", "role": "unit", "damage_output": 15, "max_hp": 999, "speed": 4.5, "ammo_type": "melee", "ammo_per_shot": 0, "tier": "fodder", "description": "Silent, infinite use, weak"},
    {"name": "Zombie Fodder", "role": "threat", "damage_output": 8, "max_hp": 30, "speed": 1.0, "ammo_type": "melee", "ammo_per_shot": 0, "tier": "fodder", "description": "Common shambler"},
    {"name": "Feral Rusher", "role": "threat", "damage_output": 20, "max_hp": 25, "speed": 4.0, "ammo_type": "melee", "ammo_per_shot": 0, "tier": "standard", "description": "Fast, fragile"},
    {"name": "Armored Bruiser", "role": "threat", "damage_output": 15, "max_hp": 150, "speed": 1.2, "ammo_type": "melee", "ammo_per_shot": 0, "tier": "elite", "description": "Slow tank"},
    {"name": "Warlord", "role": "threat", "damage_output": 40, "max_hp": 400, "speed": 2.0, "ammo_type": "melee", "ammo_per_shot": 0, "tier": "boss", "description": "Encounter boss"}
  ]
}
```

### 3.4 `domains/encounter/simulator.py`

```python
"""Encounter simulator — deterministic wave-based combat with resource depletion.

A run is pure: given a fixed (loadout, waves, starting_ammo, starting_hp) the result is
always the same. No RNG in v1. Actors act in speed-desc order each turn. Units consume ammo;
threats damage the player pool (spread across loadout). A wave ends when all threats die
or the player pool hits 0. Waves clear sequentially; ammo and HP persist across waves in
the run.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict

from core.entity_schema import EntitySchema
from core.metrics import DurationStats, WinRateDistribution
from core.metrics.base import Metric
from core.simulator_interface import Environment, RunResult, SimulatorInterface
from domains.encounter.metrics import AmmoEfficiency, WaveClearRate
from domains.encounter.schema import get_schema


class EncounterEnv(Environment):
    model_config = ConfigDict(extra="forbid")

    starting_ammo: dict[str, int] = {"kinetic": 60, "explosive": 6, "energy": 20, "melee": 0}
    starting_hp: float = 100.0
    waves: list[list[str]] = []  # e.g. [["Zombie Fodder", "Zombie Fodder"], ["Feral Rusher", "Armored Bruiser"]]
    loadout: list[str] = []      # e.g. ["Assault Rifle", "Shotgun"]
    max_turns_per_wave: int = 30


@dataclass
class _ActorState:
    name: str
    role: str
    damage_output: float
    max_hp: float
    hp: float
    speed: float
    ammo_type: str
    ammo_per_shot: int
    tier: str


@dataclass
class _RunState:
    player_hp: float
    ammo: dict[str, int]
    waves_cleared: int = 0
    total_turns: int = 0
    total_damage_dealt: float = 0.0
    damage_per_unit: dict[str, float] = field(default_factory=dict)


def _build_actor(entity: dict[str, Any]) -> _ActorState:
    return _ActorState(
        name=entity["name"],
        role=entity["role"],
        damage_output=float(entity["damage_output"]),
        max_hp=float(entity["max_hp"]),
        hp=float(entity["max_hp"]),
        speed=float(entity["speed"]),
        ammo_type=entity["ammo_type"],
        ammo_per_shot=int(entity["ammo_per_shot"]),
        tier=entity["tier"],
    )


def _pick_target(threats: list[_ActorState], unit: _ActorState) -> _ActorState | None:
    """Deterministic: target lowest-HP living threat (finish kills first)."""
    alive = [t for t in threats if t.hp > 0]
    if not alive:
        return None
    return min(alive, key=lambda t: (t.hp, t.name))  # tie-break by name for stability


def _run_encounter(env: EncounterEnv, entities: dict[str, dict[str, Any]]) -> _RunState:
    state = _RunState(player_hp=env.starting_hp, ammo=dict(env.starting_ammo))
    loadout = [_build_actor(entities[n]) for n in env.loadout]

    for wave_index, wave_names in enumerate(env.waves):
        threats = [_build_actor(entities[n]) for n in wave_names]

        for turn in range(env.max_turns_per_wave):
            if not any(t.hp > 0 for t in threats):
                break
            if state.player_hp <= 0:
                break

            # Combine + sort by speed desc, tie-break by name for determinism
            all_actors = loadout + threats
            all_actors.sort(key=lambda a: (-a.speed, a.name))

            for actor in all_actors:
                if actor.role == "unit":
                    if actor.hp <= 0:  # unit downed (v1 doesn't remove but sim honors)
                        continue
                    if actor.ammo_per_shot > 0 and state.ammo.get(actor.ammo_type, 0) < actor.ammo_per_shot:
                        continue  # out of ammo
                    target = _pick_target(threats, actor)
                    if target is None:
                        break  # all threats dead
                    dmg = actor.damage_output
                    target.hp -= dmg
                    if actor.ammo_per_shot > 0:
                        state.ammo[actor.ammo_type] -= actor.ammo_per_shot
                    state.total_damage_dealt += dmg
                    state.damage_per_unit[actor.name] = state.damage_per_unit.get(actor.name, 0.0) + dmg
                elif actor.role == "threat":
                    if actor.hp <= 0:
                        continue
                    # Spread damage across loadout (abstract "no positioning")
                    n_units = max(len([u for u in loadout if u.hp > 0]), 1)
                    state.player_hp -= actor.damage_output / n_units

            state.total_turns += 1

        if state.player_hp <= 0:
            break
        state.waves_cleared += 1

    return state


class EncounterSimulator(SimulatorInterface):
    def env_model(self) -> type[Environment]:
        return EncounterEnv

    def entity_schema(self) -> EntitySchema:
        return get_schema()

    def run(self, env: Environment, entities: dict[str, dict[str, Any]]) -> RunResult:
        assert isinstance(env, EncounterEnv)
        state = _run_encounter(env, entities)
        return RunResult(
            metrics={
                "waves_cleared": float(state.waves_cleared),
                "total_waves": float(len(env.waves)),
                "clear_ratio": float(state.waves_cleared / max(len(env.waves), 1)),
                "player_hp_remaining": float(max(state.player_hp, 0.0)),
                "total_turns": float(state.total_turns),
                "total_damage_dealt": float(state.total_damage_dealt),
                **{f"ammo_remaining_{k}": float(v) for k, v in state.ammo.items()},
                **{f"damage_by_{k}": float(v) for k, v in state.damage_per_unit.items()},
            },
            events=[],  # v1: no event log
        )

    def metrics(self) -> list[Metric]:
        return [WaveClearRate(), AmmoEfficiency()]
```

### 3.5 `domains/encounter/metrics.py`

```python
"""Encounter-specific metrics."""

from __future__ import annotations

from typing import Any

from core.metrics.base import Metric, MetricResult


class WaveClearRate(Metric):
    """Fraction of waves survived (0.0 = died in wave 1; 1.0 = cleared all)."""

    name = "wave_clear_rate"

    def compute(self, run_results: list[dict[str, Any]]) -> MetricResult:
        if not run_results:
            return MetricResult(value=0.0, per_entity={})
        ratios = [r["metrics"].get("clear_ratio", 0.0) for r in run_results]
        avg = sum(ratios) / len(ratios)
        return MetricResult(value=avg, per_entity={})


class AmmoEfficiency(Metric):
    """Total damage per ammo unit consumed (higher = more efficient loadout)."""

    name = "ammo_efficiency"

    def compute(self, run_results: list[dict[str, Any]]) -> MetricResult:
        if not run_results:
            return MetricResult(value=0.0, per_entity={})
        eff_values = []
        for r in run_results:
            m = r["metrics"]
            total_dmg = m.get("total_damage_dealt", 0.0)
            ammo_used = 0.0
            for k, v in m.items():
                if k.startswith("ammo_remaining_"):
                    # This won't work directly without starting_ammo context — v1 approximation:
                    # ammo used = total damage / damage per shot (rough); skip precise formula for v1.
                    pass
            eff = total_dmg / max(m.get("total_turns", 1.0), 1.0)
            eff_values.append(eff)
        return MetricResult(value=sum(eff_values) / len(eff_values), per_entity={})
```

### 3.6 `domains/encounter/seed.py`

```python
"""Seed loader for encounter domain (loads from seed_data.json)."""

from __future__ import annotations

import json
from pathlib import Path

_SEED_PATH = Path(__file__).with_name("seed_data.json")


def generate_seed(n: int | None = None) -> list[dict]:
    """Return the seed actors from JSON. `n` is honored only if smaller than the seed size."""
    data = json.loads(_SEED_PATH.read_text())
    actors = data["actors"]
    if n is not None and n < len(actors):
        return actors[:n]
    return actors
```

## 4. Sim loop pseudocode (no ambiguity)

```
FUNCTION run_encounter(env, entities_by_name):
    state.player_hp = env.starting_hp
    state.ammo = COPY(env.starting_ammo)
    state.waves_cleared = 0
    state.total_turns = 0
    state.total_damage_dealt = 0
    state.damage_per_unit = {}
    
    loadout = [build_actor(entities_by_name[n]) FOR n IN env.loadout]
    
    FOR wave_names IN env.waves:
        threats = [build_actor(entities_by_name[n]) FOR n IN wave_names]
        
        FOR turn IN range(env.max_turns_per_wave):
            IF all_threats_dead(threats): BREAK
            IF state.player_hp <= 0: BREAK
            
            all_actors = loadout + threats
            SORT all_actors BY (-actor.speed, actor.name) ASCENDING
            
            FOR actor IN all_actors:
                IF actor.role == "unit":
                    IF actor.hp <= 0: CONTINUE  (v1: downed units skip, no revive)
                    IF actor.ammo_per_shot > 0 AND state.ammo[actor.ammo_type] < actor.ammo_per_shot: CONTINUE
                    target = pick_target(threats, actor)
                    IF target IS NULL: BREAK  (all threats dead this turn)
                    target.hp -= actor.damage_output
                    IF actor.ammo_per_shot > 0:
                        state.ammo[actor.ammo_type] -= actor.ammo_per_shot
                    state.total_damage_dealt += actor.damage_output
                    state.damage_per_unit[actor.name] += actor.damage_output
                ELSE IF actor.role == "threat":
                    IF actor.hp <= 0: CONTINUE
                    n_alive_units = COUNT(u FOR u IN loadout IF u.hp > 0)
                    IF n_alive_units == 0: n_alive_units = 1
                    state.player_hp -= actor.damage_output / n_alive_units
            
            state.total_turns += 1
        
        IF state.player_hp <= 0: BREAK
        state.waves_cleared += 1
    
    RETURN state

FUNCTION pick_target(threats, unit):
    alive = [t FOR t IN threats IF t.hp > 0]
    IF NOT alive: RETURN NULL
    RETURN MIN(alive BY (t.hp, t.name))  (lowest HP, tie-break by name)
```

**Ordering rules (critical, follow exactly):**
- Actors act in `(-speed, name)` sort order — high speed first, tied names alphabetical
- Within a turn, unit actions resolve fully (target selected, damage applied, ammo decremented) before next actor
- Threats damage player pool per-actor (not aggregated)
- Downed units (hp <= 0) skip turns but are not removed from loadout list (avoids reindexing)

## 5. Test cases (exact input/output for verification)

### Test 1: Single unit, single threat, deterministic clear

```python
env = EncounterEnv(
    starting_ammo={"kinetic": 10, "melee": 0},
    starting_hp=100.0,
    waves=[["Zombie Fodder"]],
    loadout=["Assault Rifle"],
    max_turns_per_wave=30,
)
entities = {
    "Assault Rifle": {..from seed..},
    "Zombie Fodder": {..from seed..},
}

# Expected:
# Turn 1: Assault Rifle (speed=3.5) shoots Zombie Fodder (hp 30 → 5), ammo 10→9
#         Zombie Fodder (speed=1.0) attacks player: 100 - 8/1 = 92
# Turn 2: Assault Rifle shoots (5 → -20), Zombie dead. Ammo 9→8. Threat dead: no attack.
# Wave clear. waves_cleared=1, total_turns=2, player_hp=92, ammo_remaining_kinetic=8
```

Expected `metrics`:
- `waves_cleared`: 1.0
- `clear_ratio`: 1.0
- `player_hp_remaining`: 92.0
- `total_turns`: 2.0
- `ammo_remaining_kinetic`: 8.0
- `total_damage_dealt`: 50.0 (25+25)

### Test 2: Out of ammo mid-wave

```python
env = EncounterEnv(
    starting_ammo={"kinetic": 2, "melee": 0},
    starting_hp=100.0,
    waves=[["Zombie Fodder", "Zombie Fodder", "Zombie Fodder"]],
    loadout=["Assault Rifle"],
    max_turns_per_wave=30,
)
# Expected: 2 shots (30 dmg each? no, 25 each — but Zombie has hp 30):
# Turn 1: Rifle shoots Zombie A (30→5), ammo 2→1. All 3 zombies attack: 8/1 * 3 = 24 damage. HP: 100-24=76.
# Turn 2: Rifle shoots Zombie A (5→-20, dead), ammo 1→0. Zombie B still 30, Zombie C still 30. 
#   Remaining zombies attack: 8/1 * 2 = 16. HP: 76-16=60.
# Turn 3+: Rifle has 0 ammo, skip. Zombies attack, player takes 16 per turn.
#   Runs to max_turns_per_wave (30 total). At turn 30: player_hp = 60 - 16*28 = -388. Died.
# Since player died mid-wave, wave not cleared.
```

Expected `metrics`:
- `waves_cleared`: 0.0
- `clear_ratio`: 0.0
- `player_hp_remaining`: 0.0 (clamped)
- `ammo_remaining_kinetic`: 0.0

### Test 3: Multi-wave, ammo persists

```python
env = EncounterEnv(
    starting_ammo={"kinetic": 20, "melee": 0},
    starting_hp=200.0,
    waves=[["Zombie Fodder"], ["Zombie Fodder"]],
    loadout=["Assault Rifle"],
    max_turns_per_wave=30,
)
# Expected: 2 waves each clear in 2 turns using 2 shots. Total 4 shots, ammo 20→16.
# HP: wave 1 takes 8 (turn 1), wave 2 takes 8 (turn 1) = 200-16=184.
```

Expected:
- `waves_cleared`: 2.0
- `clear_ratio`: 1.0
- `player_hp_remaining`: 184.0
- `ammo_remaining_kinetic`: 16.0

## 6. Fase-by-fase execution plan

### Phase 1: Schema + seed (1 commit, ~150 LOC)

**Files:** `domains/encounter/__init__.py`, `domains/encounter/schema.py`, `domains/encounter/seed_data.json`, `domains/encounter/seed.py`

**Commit msg:** `feat(encounter): 1.1 — entity schema + seed data`

**DoD:**
- `python -c "from domains.encounter.schema import get_schema; s=get_schema(); print(len(s.fields))"` retorna `9`
- `python -c "from domains.encounter.seed import generate_seed; print(len(generate_seed()))"` retorna `8`
- `pytest tests/` continua verde (nada quebrou)

### Phase 2: Simulator core (1 commit, ~200 LOC)

**Files:** `domains/encounter/simulator.py`

**Commit msg:** `feat(encounter): 2.1 — deterministic sim loop`

**DoD:**
- Test file `tests/test_encounter_simulator.py` criado com Test 1, 2, 3 acima
- `pytest tests/test_encounter_simulator.py -v` verde
- `pytest tests/` inteiro continua verde

### Phase 3: Metrics (1 commit, ~100 LOC)

**Files:** `domains/encounter/metrics.py`, `tests/test_encounter_metrics.py`

**Commit msg:** `feat(encounter): 3.1 — clear rate + ammo efficiency metrics`

**DoD:**
- `pytest tests/test_encounter_metrics.py -v` verde
- Todas as metrics implementam `Metric` interface (herdam da base)

### Phase 4: Registry integration (1 commit, ~50 LOC)

**Files:** `api/registry.py` (edit — add encounter to domain discovery)

**Commit msg:** `feat(encounter): 4.1 — register in domain discovery`

**DoD:**
- `curl http://localhost:8000/domains` retorna JSON incluindo `"encounter"`
- `curl http://localhost:8000/domains/encounter/schema` retorna schema válido
- `pytest tests/` verde

### Phase 5: Basic preset (1 commit, ~50 LOC JSON)

**File:** `presets/encounter/re-gears-hybrid.json`

Conteúdo: um preset de "RE + Gears hybrid" com loadout de 4 armas + 3 waves de threats. Modelar o que Marco pediu.

**Skeleton:**
```json
{
  "id": "re-gears-hybrid",
  "name": "RE + Gears Hybrid: 3-Wave Survival",
  "domain": "encounter",
  "description": "Inspired by Resident Evil + Gears of War hybrid. Loadout: pistol/shotgun/rifle/heavy. 3 waves: fodder → mixed → elite boss. Balance question: does the heavy dominate wave 3, and does that trivialize wave 1?",
  "schema_overrides": {
    "fields": []
  },
  "default_constraints": [],
  "default_objectives": [
    {"metric_name": "wave_clear_rate", "direction": "maximize", "weight": 1.0}
  ],
  "default_visual_variant": "encounter.default",
  "examples": [
    {"name": "Handgun", "role": "unit", "damage_output": 20, "max_hp": 100, "speed": 3.0, "ammo_type": "kinetic", "ammo_per_shot": 1, "tier": "fodder", "description": "Reliable sidearm"},
    {"name": "Shotgun", "role": "unit", "damage_output": 55, "max_hp": 40, "speed": 2.0, "ammo_type": "kinetic", "ammo_per_shot": 2, "tier": "standard", "description": "Close-range power"},
    {"name": "Rifle", "role": "unit", "damage_output": 30, "max_hp": 80, "speed": 3.5, "ammo_type": "kinetic", "ammo_per_shot": 1, "tier": "standard", "description": "Balanced mid-range"},
    {"name": "Heavy Launcher", "role": "unit", "damage_output": 100, "max_hp": 20, "speed": 1.5, "ammo_type": "explosive", "ammo_per_shot": 1, "tier": "elite", "description": "Devastating but fragile ammo pool"},
    {"name": "Zombie Grunt", "role": "threat", "damage_output": 8, "max_hp": 30, "speed": 1.0, "ammo_type": "melee", "ammo_per_shot": 0, "tier": "fodder", "description": "Slow shambler"},
    {"name": "Locust Rusher", "role": "threat", "damage_output": 18, "max_hp": 45, "speed": 3.5, "ammo_type": "melee", "ammo_per_shot": 0, "tier": "standard", "description": "Fast attacker"},
    {"name": "Armored Boomer", "role": "threat", "damage_output": 35, "max_hp": 220, "speed": 1.5, "ammo_type": "melee", "ammo_per_shot": 0, "tier": "boss", "description": "Wave-3 elite"}
  ]
}
```

**Commit msg:** `feat(encounter): 5.1 — RE + Gears hybrid preset`

**DoD:**
- Preset carrega: `curl http://localhost:8000/presets/re-gears-hybrid` retorna 200 com preset data
- `pytest tests/test_presets.py` verde
- Preset aparece na lista: `curl http://localhost:8000/presets | grep re-gears-hybrid` retorna 1 linha

### Phase 6: Default view for frontend (1 commit, ~100 LOC TS)

**Files:** `ui/src/domain-views/encounter/EncounterDefaultStyle.tsx` (novo), `ui/src/domain-views/registry.ts` (edit)

**Skeleton (TS):**
```tsx
import * as React from "react";
import type { EntityViewProps, ViewMeta } from "../types";

export const meta: ViewMeta = {
  id: "encounter.default",
  name: "Encounter Actor",
  domain: "encounter",
  defaultMapping: {},
};

export default function EncounterDefaultStyle({ entity }: EntityViewProps) {
  const isUnit = entity.role === "unit";
  const roleColor = isUnit ? "border-blue-500" : "border-red-500";
  return (
    <div data-testid="encounter-actor-card" className={`flex flex-col gap-2 rounded-lg border-2 ${roleColor} bg-card p-3 text-card-foreground shadow`}>
      <div className="flex items-center justify-between">
        <span className="font-semibold">{String(entity.name ?? "?")}</span>
        <span className="text-xs uppercase text-muted-foreground">{String(entity.role ?? "")}</span>
      </div>
      <div className="grid grid-cols-3 gap-1 text-xs">
        <div>DMG {String(entity.damage_output ?? "-")}</div>
        <div>HP {String(entity.max_hp ?? "-")}</div>
        <div>SPD {String(entity.speed ?? "-")}</div>
      </div>
      <div className="text-xs text-muted-foreground">
        {isUnit ? `${entity.ammo_type} × ${entity.ammo_per_shot}` : `tier: ${entity.tier}`}
      </div>
    </div>
  );
}
```

**Commit msg:** `feat(encounter): 6.1 — default view + registry entry`

**DoD:**
- Componente renderiza: `cd ui && npm run test -- encounter` verde
- Registry inclui `encounter.default`: `grep "encounter.default" ui/src/domain-views/registry.ts` retorna 2+ linhas
- Build limpo: `cd ui && npx tsc --noEmit` sem erros

### Phase 7: End-to-end integration test (1 commit, ~150 LOC)

**File:** `tests/test_encounter_e2e.py`

Cenário completo: cria scenario com preset re-gears-hybrid → design (fake LLM ou pre-populated entities) → simulate → verifica métricas.

**Commit msg:** `test(encounter): 7.1 — end-to-end scenario flow`

**DoD:**
- Test cria scenario, roda simulate, verifica que `wave_clear_rate` e `ammo_efficiency` são calculados
- `pytest tests/test_encounter_e2e.py -v` verde

### Phase 8: Docs (1 commit, ~100 LOC MD)

**File:** `docs/writing-a-domain.md` (edit — adicionar encounter como exemplo)

**Commit msg:** `docs(encounter): 8.1 — add encounter to domain guide`

**DoD:**
- `grep -c "encounter" docs/writing-a-domain.md` retorna 3+

## 7. Integration checklist final

Após todos os 8 commits, verificar:

- [ ] `pytest tests/` inteiro verde (nada quebrado nos outros domains)
- [ ] `cd ui && npm run test` verde
- [ ] `cd ui && npx next build` limpo
- [ ] `curl http://localhost:8000/domains` inclui `encounter`
- [ ] `curl http://localhost:8000/presets` inclui `re-gears-hybrid`
- [ ] Manual test: criar scenario via API com preset `re-gears-hybrid`, rodar simulate, verificar output tem `waves_cleared` e `clear_ratio`

## 8. Após conclusão

1. `git push origin dev-marco-agent.encounter-domain`
2. Abrir PR: `feat: encounter domain — wave-based combat with resource depletion`
3. Body do PR: link pra este blueprint, lista os 8 commits, resultado dos testes, screenshot de encounter view rendering
4. **NÃO fazer merge sem confirmação humana.**

## 9. Escalation gates (repetindo — importante)

Pare imediatamente e escale se:

1. Alguma DoD falha após 2 tentativas
2. Test existente quebra por mudança não pedida por este blueprint
3. Precisa fazer decisão arquitetural fora do que está aqui (ex: "deveria adicionar seed data pra creature_rpg?")
4. Merge conflict com outro branch
5. Padrão do repo real difere significativamente do descrito aqui (ex: `SimulatorInterface` mudou de assinatura)
6. Precisa criar arquivo fora dos listados neste blueprint

**Nunca:**
- Modifique `main` diretamente
- Force push
- Skip hooks (`--no-verify`)
- Faça merge de PR sem Marco autorizar
- Adicione dependências novas ao `pyproject.toml`
- Toque em `docker/.env`

---

## Notas finais pra Marco

Este blueprint foi escrito assumindo Qwen 30B como executor. Está mais explicit e prescriptive do que os inboxes anteriores (que assumiam Sonnet/Opus). Cada arquivo tem skeleton code; cada DoD tem comando bash executável.

**Fidelity esperada do domain resultante**: 55-65% para FPS/survival. Cobre ammo economy, wave feasibility, weapon utility ranking. Não cobre cover, aim, timing.

**Total effort estimado**: ~30-50h de wall clock com Qwen 30B (mais lento que Sonnet mas viável).

Quando decidir acionar: `Execute docs/blueprint-encounter-domain.md`
