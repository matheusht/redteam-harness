# Candidate cand-new-output-anchored-review — evidence bundle

**Track:** new-technique-card (new-technique-card)
**Mutation target:** `skills/techniques/output-anchored-review/` (single new component)
**Parent:** baseline

## What changed

Proposes one new technique card, `technique.output-anchored-review`, adding a single new file under a
new directory. No existing card or evaluator file is touched.

## Why it might help

Generalizes the "ride on the assistant's own output" idea from the task-reframing variant into a
first-class technique the router could load on its own. Kept benign by construction (self-review /
self-extension only).

## Shadow status (no promotion)

Shadow candidate. The runner gates it and runs the frozen scorers against the campaign baseline
outputs. The new card is **not** added to Plane 1, not routed, and not promoted. A new card only earns
promotion through Phase 5 (replay + promotion bundle + PR review). Coverage delta is 0 here by
construction.

## Gate expectations

- adds only files under `skills/techniques/output-anchored-review/` → single-mutation ok
- no immutable file → scope fence ok
- bundle present, diff hash matches → ALLOW

## Replay (Phase 4)

Replay artifacts under `replays/` (primary + two fresh-session replays + `replay-summary.json`), at
identical benchmark version and budget. Deterministic shadow benchmark → identical reproductions, cost
spread 0, replay-stable. Final verdict after the replay gate: **probe** — a new card only promotes via
Phase 5 (promotion bundle + PR review).
