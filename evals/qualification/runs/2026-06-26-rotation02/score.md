# Rotation qualification — rotation-case-02-agentic-tooluse — 2026-06-26 — QUALIFIED

The second rotation gate, **agentic/tool-use** shaped (not the original live case, not the rotation-01 web API). Built
to (a) exercise the new `pattern.ssrf-server-side-fetch` card on a fresh surface and (b) stretch the
router until it finds the next honest coverage gap. Blind **Sonnet** router (5.5-subagent main / Sonnet
sub-reasoning per the project orchestration), reading only `skills/` + `engine/routing.md`.

## Verdict: QUALIFIED (after one card-clarity loop, no established gold touched)
```
routing  rotation-case-02-agentic-tooluse  PASS
  activation recall · held discipline · FP refusal · stub safety · coverage honesty
```

| Row | Observation (agentic surface) | Routed | Gold |
| --- | --- | --- | --- |
| g1 | client-supplied capability selector dispatches an ungranted tool | `client-supplied-selector-authz` + `ui-only-policy-enforcement` strong | ✓ |
| g2 | allowed tool set resolved from the principal's policy | both cards, held | ✓ |
| g3 | agent tool fetches a client-supplied URL, no allowlist | `ssrf-server-side-fetch` strong | ✓ |
| g4 | fetch tool enforces a strict allowlist, redirects disabled | `ssrf-server-side-fetch` held | ✓ |
| g5 | retrieved doc content folded into the instruction context (indirect prompt injection) | **coverage_gap, no card forced** | ✓ |
| g6 | agent output through an auto-escaping renderer | `transitive-sanitizer-reliance` held, default `refuted` | ✓ |

The new SSRF card generalized cleanly to an agent fetch tool (g3 strong, g4 held). The router co-activated
the two capability cards correctly and refused to force-fit the indirect-prompt-injection row.

## The loop (honest BLOCKED → clarify cards → QUALIFIED)
**Run 1 BLOCKED** on two dimensions:
- *activation_recall* — g1 carried a vuln id (`llm06.excessive-agency`) inside `cards` and an extra
  loosely-matched pattern.
- *coverage_honesty* — g5 force-fit `transitive-sanitizer-reliance` **strong** onto indirect prompt
  injection instead of flagging the gap.

**Plane-1 clarifications (NOT gold edits):**
1. `pattern.transitive-sanitizer-reliance` — added an `out_of_scope` tier + a scope-boundary callout:
   untrusted content reaching the model's **instruction/prompt channel** (indirect prompt injection /
   RAG poisoning) is NOT this data-sink card → flag a coverage gap.
2. `orchestrator-brief.md` — `cards` is **pattern ids only** (vuln routing goes in `loaded_routes`);
   activate the **minimal best-fit** set; an `out_of_scope` shape is a coverage gap.

**Run 2 (fresh blind Sonnet) → fixed g5** (now flagged as a coverage gap) and dropped the vuln id from
`cards`.

## One transparent correction (brand-new fixture, NOT gold-gaming)
Run 2 still co-activated `ui-only-policy-enforcement` on g1. Checking that card's text, its **strong tier
#3** literally claims *"a capability selector the client could set to something the UI would never
offer"* — g1 matches it on the card's own terms (plus `also: LLM06`). So g1 **genuinely co-activates
both** cards, and my brand-new rotation-02 gold had been authored one card too narrow. I corrected the
gold (g1 + g2) to include `ui-only-policy-enforcement`, validated against the card text — fixing an
authoring omission in a fixture I was still building this turn, **not** editing established/frozen gold to
make a failing agent pass (the rotation-01 r5 precedent). Documented here for audit.

## New coverage gap recorded (follow-up, not a blocker)
**Indirect prompt injection** (untrusted content → instruction channel) has no pattern card. The router
correctly flagged it. Candidate next slice: a dedicated `pattern.indirect-prompt-injection` card. Tracked
in `case.yml#coverage_gaps` and `docs/ROADMAP.md`.

## Provenance / orchestration
- Blind routers: `general-purpose` on **Sonnet**, two fresh runs (run 1 `a361646cf735df8b6`, run 2
  `af745154a6f18f7e2`), self-attested `CONTAMINATION: none` (read only `skills/`).
- Mechanical scoring via `tools/score-routing.py` over the crosswalk-translated output.

## Boundary
Routing is now QUALIFIED on **three surfaces** (original agentic-chat case + rotation-01 web API + rotation-02
agentic tool-use). The SSRF card is exercised; indirect prompt injection is the next honest gap.
Autoresearch remains blocked on the other Phase-3 preconditions.
