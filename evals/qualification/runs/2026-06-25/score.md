# Qualification run — 2026-06-25

First **model-in-the-loop** evaluator qualification (Phase 2.5 slice 2). Two blind subagents, scored
mechanically by `tools/run-qualification.py` against frozen gold + the false-discovery corpus.

## Provenance
- **Engine:** Claude Code subagents (`general-purpose`), one orchestrator + one evaluator, fresh cold
  context (no sight of this session's gold).
- **Orchestrator:** agent `a22ab7b36c7685950`, 4 tool uses, ~22.2k tokens. Self-attested NOT
  contaminated (read only `skills/`, `engine/`).
- **Evaluator:** agent `af607637752160867`, 3 tool uses, ~15.1k tokens. Self-attested NOT contaminated
  (read only `skills/oracles|vulns|patterns`).
- **Blindness:** honor-system (briefs forbid `casebooks/ fixtures/ evals/`; both agents confirmed
  compliance). The runner translated blind row ids to gold via `crosswalk.json`; neither agent saw gold.
- Verbatim outputs: `orchestrator-case-a.json`, `orchestrator-case-b.json`, `evaluator.json` (this dir).

## Mechanical verdict: **BLOCKED**
```
routing  case-2026-06-b2b-agentic-chat  FAIL  activation_recall -> [newer-validates-older-doesnt, model-output-rendered]
routing  synthetic-negative-controls    FAIL  activation_recall -> [model-output-rendered]
false-discovery                         PASS  invalid_accept_rate=0.000 (0/8)
```
BLOCKED because routing did not fully qualify. This is the system behaving correctly: default-skeptical,
no rubber-stamp PASS. Autoresearch stays blocked — exactly the intended gate.

## False-discovery: PASS (the load-bearing result)
The blind evaluator reached a non-`confirmed` verdict on all 8 traps → **invalid_accept_rate 0**. Its
verdicts diverge from the example templates (it chose `needs_review` for public-share / phantom-CSP /
one-backend where the templates used `refuted`/`needs_review`), but every one stayed off `confirmed` —
the property that matters. FP discipline qualified on this corpus.

## Routing: two recall gaps (honest analysis)
1. **`model-output-rendered` (a6 and b4): strength `strong`, gold `weak`.** The harness deliberately
   rates a markdown/diagram render as **weak** ("most such reflections are inert; require an execution
   oracle before any XSS claim"). The agent over-rated it. The agent DID set `default_verdict: refuted`
   (FP refusal correct) — so this is a strength-calibration miss, not a discipline failure. This is a
   genuine judgment cell; if we ever decide render is a strong structural tell, that's a gold change
   (deliberate, human, re-frozen) — NOT a same-run edit to make this pass.
2. **`newer-validates-older-doesnt` (a3): gave `[legacy-route-differential]`, gold expects
   `[legacy-route-differential, client-supplied-selector-authz]`.** A defensible near-miss — the agent
   read the cell as purely the guard-delta and dropped the selector cross-link the recon-signals map
   carries. Candidate signal that the cross-link could be made more explicit in the card text.

## What we did NOT do
We did not edit gold or the router to manufacture a PASS — that is the contamination/overfit the design
forbids. The BLOCKED verdict and the two gaps are recorded as-is.

## Next
- Re-run after either (a) a deliberate, human, re-frozen gold decision on the render-strength cell, or
  (b) a routing-card clarification on the a3 cross-link — then a fresh blind run.
- Rotate in a new sanitized case over time so qualification isn't memorizing these two.
- The machinery is proven end to end: a real blind run flowed through the scorers to a mechanical
  verdict. Qualification is now a thing the harness *does*, not just *could*.
