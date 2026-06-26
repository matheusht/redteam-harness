# Qualification run b — 2026-06-25 — BLOCKED (b1 only)

Second blind run, after the first two card clarifications (render-strength + legacy co-activation).
Routing case A now PASSES; case B fails on a single cell. See `../2026-06-25c/score.md` for the full
progression and the third clarification that closed it.

- Orchestrator: agent `a7b76c803ded3ab8c`, not contaminated.
- Routing: case A **PASS**; case B **FAIL** — `b1` (a bare owner-id field) rated `weak` vs gold `strong`.
  The agent conflated activation strength with confidence-of-exploitation.
- False-discovery: **PASS** (0/8 invalid accepts).
- Verdict: **BLOCKED**. Led to the `client-supplied-selector-authz` activation-vs-adjudication clarification.
