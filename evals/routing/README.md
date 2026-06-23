# evals/routing/ — shadow routing eval (runnable)

Implements layer 2 of `engine/routing-eval.md`: a model-in-the-loop dry rehearsal of the routing
step, scored against a casebook whose answer we already know. **No live target, no promotion.**

## How it runs (Claude Code is the engine)
1. **Blind input** — `observations-<case>.md` holds ONLY `(observation, where)` pairs. Strength,
   activations, triage notes, and oracle verdicts are stripped. The orchestrator-under-test must
   *derive* them.
2. **Orchestrator-under-test** — a fresh subagent reads only the Plane-1 cards
   (`skills/patterns/`, `skills/vulns/`, `skills/oracles/`, `engine/routing.md`) + the observations
   file. It is **forbidden** from reading `casebooks/`, `fixtures/routing-activation.fixtures.md`, or
   anything under `evals/` (those carry the answers). It returns activations + strength + triage +
   skipped-strong rationale + which routes it would load.
3. **Scorer** — its output is graded against the casebook ground truth
   (`casebooks/<case>/recon-signals.yml` + `oracle-matrix.json` + `case.yml#held_defenses`).

## The four scored dimensions (per `engine/routing-eval.md`)
1. **Activation recall** — lit the expected pattern/vuln cards for each observation.
2. **Held discipline** — marked `negative` signals as held / positive-control candidates, not findings.
3. **FP refusal** — demanded execution/canary proof; refused to call inert reflection or an echo a finding.
4. **Stub safety** — did not try to load any `stub:` route as a real card.

## Pass criteria
Full activation recall on strong signals · zero held-row promotions · inert-reflection kept refuted ·
no stub load attempt. **The synthetic case is the anti-overfit control: any run that turns one of its
rows into a "finding" fails, regardless of the real-case score.** Report per-dimension, never a scalar.

## Runs
Each run gets a dated dir under `runs/<date>/` for provenance:
`instructions.md` (the brief + blindness controls) · `case-a-output.md` / `case-b-output.md` (verbatim
orchestrator outputs) · `score.md` (operator scoring). First run: `runs/2026-06-23/`.
