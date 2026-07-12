# Balance Studio

A generic, LLM-collaborative **balancing framework**. Point it at any domain — a card game,
an RPG bestiary, a team roster — and get schema-driven entities, deterministic simulation,
objective + subjective metrics, an event-sourced history you can branch and time-travel, and
three LLM "hats" (designer / judge / iterator) that co-edit the same state alongside you.

> **Framework, not a vertical tool.** A card game with 10 units? A creature RPG with 100
> monsters? Staffing 50 people across a workload? Same core, same UI — you swap a **~400-line
> plugin**, not the engine. The `core/` (≈2.5k LOC) is ~6× the size of any one domain plugin.

## The problem

"Is this balanced?" is the same question across games, teams, and product portfolios, but the
tooling is always rebuilt from scratch and vertical. Balance Studio makes the *loop* generic —
**brief → LLM designs → simulate → metrics + LLM judge → propose changes → repeat** — while
keeping the credible part (simulation) LLM-free and deterministic, so "won 62% of matches" is
ground truth, not an opinion.

## Does the loop actually balance?

Measured, not asserted. Starting from a known-imbalanced seed roster and running the Iterator
(a local 7B) with **surgical edits**, over 3 seeds:

| Domain | Win-rate dispersion (↓ = more balanced) | Variety (guardrail) |
|---|---|---|
| **creature_rpg** | 0.273 → 0.244 (**−10.6%**) | −3.9% (preserved) |
| **card_game** | 0.315 → 0.308 (**−2.2%**) | −5.4% (preserved) |
| team_composition | flat (within noise) | −0.6% |

**The Iterator cut win-rate dispersion in 2 of 3 domains while keeping variety intact** — and
the process surfaced a real finding: naive "change everything" passes *raise* imbalance in
combat domains (non-linear stat→outcome), so the Iterator is capped to a few targeted edits.
Full methodology, the negative first attempt, and the diagnosis: [`docs/experiments.md`](docs/experiments.md).

## What's in the box

Three working domains, all on the same infrastructure:

| Domain | Entity | Simulation | Domain metrics |
|---|---|---|---|
| **card_game** | `Unit` (cost/hp/damage/ability) | turn-based 1v1, seeded | win-rate, Elo, TTK |
| **creature_rpg** | `Creature` (type/stats/skills/resistances) | gauntlet + tournament, type-matchup | tier emergence, dominance, usage coverage |
| **team_composition** | `Person` (seniority/skills) | probabilistic workload completion | skill coverage, redundancy, single points of failure |

## Architecture

```
┌─────────────────────────── Next.js 15 UI ───────────────────────────┐
│  domain picker · generic EntityEditor (renders any schema) ·         │
│  timeline scrubber · freshness metrics · Pareto picker · branch diff │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ HTTP + JSON
┌───────────────────────────────▼─────────────────────────────────────┐
│                               FastAPI                                 │
│   /domains/{n}/{schema,metrics,simulate}   /scenarios/... (CRUD,      │
│                                            iterate, branches, diff)   │
└───────────────────────────────┬─────────────────────────────────────┘
┌───────────────────────────────▼─────────────────────────────────────┐
│                                CORE                                   │
│  entity_schema (DSL→Pydantic)   constraint_engine   metrics/          │
│  scenario (append-only event log)   snapshot (zstd + replay)         │
│  iteration_engine   objectives (+Pareto)   sim_cache (incremental)   │
│  llm_hats (Designer/Judge/Iterator protocols)  ·  Fake / Local impls │
└───────────────────────────────┬─────────────────────────────────────┘
┌───────────────────────────────▼─────────────────────────────────────┐
│           DOMAINS (plugins) — schema · simulator · metrics · seed     │
│           card_game        creature_rpg        team_composition       │
└──────────────────────────────────────────────────────────────────────┘
```

**Golden rule:** the core never imports a domain (`grep -rn "from domains" core/` is empty).
Domains implement `SimulatorInterface`; the core discovers them by folder.

### Ideas that make it more than a card-game balancer

- **Fluid human/LLM collaboration.** No modal turns — you and the LLM edit the same state at
  any time. Every change is an append-only event; the iterator LLM never overwrites an entity
  you last touched.
- **Event-sourced, portable scenarios.** State is a `scenarios/<id>/events.jsonl` you can
  branch, diff, time-travel (replay to any point), and `tar` up and move.
- **Multi-objective.** Compose weighted objectives (balance + variety + cohesion …); the UI
  shows the aggregate score and the Pareto front when they conflict.
- **Incremental simulation cache.** Editing one entity re-simulates only the matchups it
  touches; freshness (🟢 full / 🟡 quick / 🔴 stale) is tracked per config.
- **Three LLM hats, pluggable backend.** `Designer` (brief → entities), `Judge` (variety /
  cohesion / thematic), `Iterator` (metrics → change proposals). Backend is `fake` (dev,
  deterministic) or `local` (an OpenAI-compatible llama-server) — the domain never knows which.

## Numbers

- **Simulation** (single-thread, beats every target by ~1000×): creature gauntlet 100×10 =
  **1000 battles in 0.03 s**; card 500-pool 1000 matches in **0.06 s**; incremental cache hit
  **< 5 ms**. (`docs/performance.md`)
- **LLM design** on a local **Qwen2.5-Coder-7B** (free, unlimited): **100 %** schema+constraint
  valid entities on both card_game and creature_rpg — 33/33. Judge discriminates
  (variety 0.30 for near-duplicate cards, with a coherent rationale). (`docs/experiments.md`)
- **Scale:** core ≈2.5k LOC vs ~400 LOC per domain plugin. **183 backend tests + 25 UI tests.**

## Screenshots

*(To be captured from a `pnpm dev` / deployed run — the sandbox has no headless browser.)*
Home (domain picker + scenarios) · scenario detail (entities + metrics + freshness) · timeline
scrubber · branch diff.

## Run it locally

```bash
# backend (discovers every domain in domains/)
poetry install
poetry run uvicorn api.main:app --port 8000

# frontend
cd ui && pnpm install && pnpm dev      # http://localhost:3000
```

LLM backend via `.env` (`LLM_BACKEND=fake` needs nothing; `local` needs `LOCAL_LLM_URL` to an
OpenAI-compatible server). Cache backend via `CACHE_BACKEND=disk|redis`.

End-to-end demos (no browser needed):

```bash
poetry run python -m scripts.demo_sprint2 --brief "aggro deck" --n 5 --domain card_game
BASE_URL=http://localhost:8000 bash scripts/demo_sprint3.sh   # scenario API flow
LLM_BACKEND=local poetry run python scripts/smoke_local.py    # local LLM hats
```

## Extending — add your own domain

A new domain is `schema.py` + `simulator.py` + `metrics.py` + `seed_data.json` + a
`get_simulator()` export. The step-by-step (with a validated 10-minute quickstart) is in
**[docs/writing-a-domain.md](docs/writing-a-domain.md)**.

## Stack

Python 3.11 · FastAPI · Pydantic v2 · pytest · Next.js 15 · Tailwind · Radix · Tanstack Query ·
Recharts · Vitest. Dev persistence is file-based (event log) + diskcache; prod cache swaps to
Redis by config. Deploy target: Fly.io (back) + Vercel (front).

## Status

Sprints 1–7 complete (core, 3 domains, event log + branching, multi-objective, incremental
cache, full UI, real local LLM). Sprint 8 (deploy + demo video + write-up) in progress.

## License

[MIT](LICENSE) © 2026 Marco
