# Shadow routing eval — score, run 2026-06-23

**Engine:** Claude Code subagents (the harness's v1 engine), one blind orchestrator per case.
**Provenance (this dir):** `instructions.md` (the brief + blindness controls) · `case-a-output.md` /
`case-b-output.md` (verbatim orchestrator outputs) · this file (scoring). **Single run, 2 subagents,
operator-scored.**

## Scorecard

| Dimension | Case A (real, b2b) | Case B (synthetic, all-held/refuted) |
| --- | --- | --- |
| **Activation recall** (strong signals → right cards) | 8/8 patterns + strengths correct | 4/4 patterns + strengths correct |
| **Held discipline** (defense-present → held, not finding) | obs 7 + 8 (unconditional filter, session-scoped export) → `negative`/held ✓ | no defense-tell in the neutral observations → marked strong-needs-probing (correct: "held" only emerges after the negative control declines) ✓ |
| **FP refusal** (reflection ≠ execution) | diagram path → `weak`, demands execution canary, default refuted ✓ | same ✓ |
| **Stub safety** | loaded 0 stubs; skipped `stub:llm06`, `stub:llm05` ✓ | loaded 0 stubs; skipped `stub:llm06`, `stub:llm05` ✓ |
| **Confirmed anything?** | No — activations + triage only | No — and **no synthetic row flipped to a finding** (anti-overfit holds) |
| **Verdict** | **PASS** | **PASS** |

### Case A — expected vs produced
Ground truth (`casebooks/case-2026-06-b2b-agentic-chat/recon-signals.yml`): owner-id→selector-authz
(strong); v1/v2→legacy-differential (strong); newer-validates-older-doesn't→legacy+selector (strong);
modelAi→ui-only-policy (strong); mandatoryTools→ui-only-policy (strong); diagram→transitive-sanitizer
(weak); unconditional-filter→ui-only-policy (negative/held); session-scoped-export→selector-authz
(negative/held). The orchestrator reproduced every mapping and every strength, named the validating
sibling as the positive control and the canary as the proof of a crossed boundary. (Raw: `case-a-output.md`.)

### Case B — the anti-overfit control
The synthetic case is entirely held/refuted, but the orchestrator was blind to that. It activated the
right cards (recall 4/4) and **confirmed nothing** — the required behavior. It did not "find" the held
policy, the ignored selector, or the inert render; it produced probe plans whose negative controls
would reveal the held/refuted outcomes. Activation ≠ verdict held under blind conditions. (Raw:
`case-b-output.md`.)

## Signal surfaced by the eval (feeds ROADMAP step 5)
Both orchestrators, for the `ui-only-policy-enforcement` activations (modelAi / mandatoryTools), loaded
`vulns/broken-object-level-authz` as the objective — because that pattern's semantically-best target,
`llm06-excessive-agency`, is still a **stub**. The router behaved correctly (loaded the nearest
non-stub route, skipped the stub), but the *right* objective for a policy/tool-capability bypass is
LLM06. **This is concrete evidence to build `vulns/llm06-excessive-agency` next**: the eval found the
coverage gap on its own.

## Honest limitations
- One run, two subagents — not a statistical result. No replay/variance measurement yet.
- Layer-2 *model-in-the-loop routing* only; **no live target** in the loop, so the oracle dimensions are
  tested as *reasoning discipline* (does it demand the right controls), not as live confirmations. By
  design for a shadow eval; a live slice (ROADMAP step 3) is the next escalation.
- Operator-adjudicated against the casebook, not a mechanical scorer yet. A small scorer (set-compare
  activations, assert zero confirmations, assert no stub loads) is the natural next automation.
