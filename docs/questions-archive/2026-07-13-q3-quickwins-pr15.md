# Open questions — Quick wins (README + starter gallery), PR #15 (2026-07-14)

**Trigger:** executing the 2026-07-13 inbox (`T-QW.README` + `T-QW.GALLERY`). Two items need a
human call before merge. Archive this file to `docs/questions-archive/` once resolved.

---

## Q1 — `SEED_STARTERS` default: off (current) or on?

**Context:** the gallery DoD asks for two things that directly conflict:
1. "Fresh backend startup (empty store) auto-creates the 5 starters" and "`curl /scenarios` on a
   fresh backend returns the 5 starters."
2. "No existing test breaks."

The test suite assumes an **empty** store — `tests/test_api_scenarios.py::test_list_scenarios`
asserts `GET /scenarios == []`, and 5 `TestClient` files boot the lifespan against a fresh
`tmp_path`. Seeding unconditionally in the lifespan therefore breaks at least that test.

**Resolution shipped:** seeding is wired into the API lifespan but **gated by `SEED_STARTERS`,
defaulting to `off`**. Tests are unaffected (flag unset); the documented dev/deploy command sets
`SEED_STARTERS=1`. Verified end-to-end: a fresh store with the flag on returns 5 populated
scenarios. `tests/test_starter_scenarios.py` exercises the seed function directly (4 tests).

**Trade-off:** a bare `uvicorn api.main:app` (no flag) does **not** auto-seed — it only seeds via
the documented command. This satisfies "no existing test breaks" but only satisfies the
"automatic on fresh startup" DoD line *when the flag is set*.

**Decision needed:**
- **(A) Keep default off (current).** Safest; zero test churn; auto-seed is opt-in via the
  documented command / deploy env. *Recommended.*
- **(B) Flip default on.** Truly automatic on any fresh start, but requires updating the one test
  that asserts an empty store (`test_list_scenarios`) to expect the seeded starters (or to set
  `SEED_STARTERS=0` in the `client` fixtures). Small change, but it touches existing tests, which
  the inbox flagged as escalate-before-touching.

---

## Q2 — Untracked artifacts now landing in PR #15 (FYI + confirm)

**Discovery:** several files the inbox treated as "already in the repo" were in fact **untracked**
in the working tree — never committed to `main`:

- `presets/creature_rpg/outpost-siege.json`, `presets/creature_rpg/cover-firefight.json`
  (the QW.1/QW.2 presets)
- `docs/inbox.md` (the inbox itself)
- `docs/blueprint-encounter-domain.md`, `docs/roadmap-v2-rule-engine.md` (standby reference docs)

**What was done:** the two presets are a hard dependency of the starter gallery (the seed skips a
starter whose preset is missing, so a clean clone would seed only 3 of 5) — they land in PR #15.
The inbox is archived to `docs/inbox-archive/2026-07-13-quick-wins-and-blueprint-gate.md`. The
blueprint and rule-engine roadmap are committed as **standby reference docs only — not executed**
(the encounter domain remains gated on an explicit manual trigger).

**Confirm:** OK to land the blueprint/roadmap docs as tracked reference files in this PR? If you'd
rather keep them out of a "quick wins" PR, they can be dropped from PR #15 and committed
separately — but the two presets must stay (the gallery depends on them).

---

## Resolução (2026-07-14 01:45 UTC)

**PR #15 mergeado** antes das respostas formais. Retroativamente:

- **Q1**: **A** confirmada. `SEED_STARTERS` default OFF é a decisão de produto. Deploy command com `SEED_STARTERS=1` documentado permanece o path oficial de auto-seed em fresh installs.
- **Q2**: **Deixar no PR #15** confirmada. Blueprint + roadmap-v2 como reference docs no repo. Zero risco funcional, referência preservada.

Instância pode arquivar contexto e seguir. Próximo trabalho não bloqueado por esses items.
