# Case A (b2b) — raw blind orchestrator output (verbatim)

Subagent `general-purpose`, blind to verdicts. Input: `observations-b2b.md` (8 observations). Captured
exactly as returned — this is the data that was scored in `score.md`.

---

| # | strength | patterns | vuln-cards-loaded | triage | likely-held |
| --- | --- | --- | --- | --- | --- |
| 1 | strong | pattern.client-supplied-selector-authz | vulns/broken-object-level-authz | Point owner-id at a 2nd principal I control with a planted canary; A/B selector absent/self/other. Control that must hold: the no-selector/self negative control MUST decline (and canary, not own data) before any confirm. | no |
| 2 | strong | pattern.legacy-route-differential | vulns/broken-object-level-authz (resolved via routed selector/policy patterns) | Run one fixed authorized request against v1 and v2, diff the authorization outcome (not response shape). Control: the canonical sibling (v2) must DENY the same action — same actor, same payload, route the only variable. | no |
| 3 | strong | pattern.legacy-route-differential (+ pattern.client-supplied-selector-authz) | vulns/broken-object-level-authz | Carry the owner-id selector across siblings: the value the new (validating) handler rejects, replay on the old handler. Control: validating sibling = positive control returning 403; legacy = the one missing the guard. | no |
| 4 | strong | pattern.ui-only-policy-enforcement | vulns/broken-object-level-authz | Send a `modelAi` value the UI would never offer (outside allowlist). Control: echo ≠ proof — require response metadata showing the disallowed model actually ANSWERED; and confirm my account isn't entitled. | no |
| 5 | strong | pattern.ui-only-policy-enforcement | vulns/broken-object-level-authz | Send a `mandatoryTools` entry for a deactivated/never-offered tool. Control: prove the tool's EFFECT (real tool events/output), not its presence in a list; rule out legitimate entitlement. | no |
| 6 | weak | pattern.transitive-sanitizer-reliance | vulns/injection | Inject an INERT local execution canary (document.title/console/DOM) through the mermaid/markdown path; calibrate the execution detector first (positive control). Control: EXECUTION oracle — reflection is `needs_review` at most; no canary fired → refuted. | yes |
| 7 | negative | pattern.ui-only-policy-enforcement (negative) | none (defense present — record as held / positive-control candidate) | Confirm the filter is applied unconditionally to ALL user classes incl. a fail-open seat (non-workspace/non-admin); this is the validating sibling for #4. Control: this held filter is the positive control proving the guard CAN exist next to the failing modelAi sibling. | yes |
| 8 | negative | pattern.client-supplied-selector-authz (negative) | none (defense present — record as held / positive-control candidate) | Re-confirm export/owner resolves from the session principal, not a request field; try injecting an owner-id field anyway. Control: this is the negative control / validating sibling for observations 1 and 3. | yes |

## NOTES

**Markdown/diagram render (obs 6) — reflection-vs-execution stance.** I treat this as guilty-of-being-inert. Mermaid/markdown renderers are sandboxed-to-inert-SVG by design, so this is the common false-positive direction. Before calling it a finding I require: (a) a calibrated execution detector (positive control where a known-executing case fires the local canary first), then (b) the INERT local canary (title/console/DOM mutation) actually FIRES at the sink. Payload merely appearing in the DOM/source = reflection = `needs_review` at most; if the renderer escapes/sandboxes and the canary never fires → `refuted`. No external-callback/egress canary without scope + operator confirm.

**Routes I would load (resolved via routes_to, no stubs):**
- pattern.client-supplied-selector-authz → load **vulns/broken-object-level-authz**. SKIPPED stub: `stub:vulns/llm06-excessive-agency`.
- pattern.legacy-route-differential → routes to other pattern cards (pattern.client-supplied-selector-authz, pattern.ui-only-policy-enforcement), which in turn load **vulns/broken-object-level-authz**. No stubs in its routes_to.
- pattern.ui-only-policy-enforcement → load **vulns/broken-object-level-authz**. SKIPPED stub: `stub:vulns/llm06-excessive-agency`.
- pattern.transitive-sanitizer-reliance → load **vulns/injection**. SKIPPED stub: `stub:vulns/llm05-improper-output-handling`.

Net vuln cards loaded: **vulns/broken-object-level-authz** and **vulns/injection**. The llm07-system-prompt-leakage card is NOT routed to by any activated pattern here, so I did not load it. I am loading **zero `stub:` routes**; the two stubs skipped are `stub:vulns/llm06-excessive-agency` and `stub:vulns/llm05-improper-output-handling`.

**Am I confirming any finding right now?** No. I have no live target, no captured responses, and no verdicts — every row is an activation + triage plan only. Nothing reaches `confirmed`: signal-oracle requires a captured response and adjudication requires negative-control-declined + positive-control + contamination-ruled-out + replay, none of which exist at routing time. Observations 7 and 8 are recorded as held/positive-control candidates, not findings.
