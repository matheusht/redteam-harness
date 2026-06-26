# Qualification run c — 2026-06-25 — QUALIFIED

Third blind run, after two rounds of **card** clarifications (gold never edited). Clean QUALIFIED.

## Progression (same frozen gold throughout)
| Run | Orchestrator | Routing | False-discovery | Verdict |
| --- | --- | --- | --- | --- |
| `2026-06-25/`  | agent a22ab7b3 | FAIL — a3 cross-link dropped; a6/b4 render rated strong | PASS (0/8) | **BLOCKED** |
| `2026-06-25b/` | agent a7b76c80 | FAIL — b1 selector rated weak (presence vs differs) | PASS (0/8) | **BLOCKED** |
| `2026-06-25c/` | agent a2f1bf05 | **PASS** | PASS (0/8) | **QUALIFIED** |

## What changed between runs — three card clarifications, zero gold edits
1. **`transitive-sanitizer-reliance`** — render *presence* demoted to **weak**; **strong** reserved for a
   sink-danger tell (unsafe sink / sanitizer bypass / active-HTML / execution route). Resolved a real
   card↔gold contradiction (the card had listed markdown/diagram render under strong). Fixed a6 & b4.
2. **`legacy-route-differential`** — explicit **co-activation rule**: a differential driven by a
   client-controlled selector fires `client-supplied-selector-authz` too. Fixed a3.
3. **`client-supplied-selector-authz`** — **activation vs adjudication** rule: a selector field being
   *present/functioning* is strong on sight; whether it differs from the principal or is re-resolved is
   an adjudication call, not an activation precondition. Fixed b1.

Each gap the eval surfaced was a genuine, *generalizable* card-clarity issue — not the agent being
reckless (it defaulted render to refuted every time, and never confirmed a trap).

## Provenance / honesty
- Run-c orchestrator: agent `a2f1bf05e9c76c2f3`, 9 tool uses, ~25.9k tokens, self-attested not contaminated.
- Evaluator output carried from run b (`a7b76c80`, a genuine blind run, 0/8) — the card edits were
  routing-only, so the evaluator dimension was not re-spawned. Its verdicts: all 8 non-`confirmed`.
- **No gold or input answer was edited to manufacture the pass.** Only Plane-1 cards were clarified, and
  those clarifications stand on their own as better routing guidance.

## Boundary (unchanged)
QUALIFIED on these TWO cases is **necessary, not sufficient**. Before declaring routing broadly
qualified, rotate in at least one fresh sanitized case (so the eval can't be memorized). Autoresearch
stays blocked on the remaining Phase-3 preconditions.
