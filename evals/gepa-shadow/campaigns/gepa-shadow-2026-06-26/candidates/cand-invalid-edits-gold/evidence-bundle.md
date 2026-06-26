# Candidate cand-invalid-edits-gold — evidence bundle (INTENTIONALLY INVALID)

**Track:** task-reframing (declared) — but the diff also edits frozen routing gold.
**Declared mutation target:** `skills/techniques/task-reframing/`
**Parent:** baseline

## What this is

A deliberately invalid candidate used as a negative control for the Phase 2 gate. Its diff edits a
technique card **and** `evals/routing/gold/rotation-01.gold.json` — moving a `must_refute` candidate
to `confirmed`, i.e. trying to win by relabeling the gold instead of improving the technique.

## Expected verdict: BLOCK

`tools/check-campaign.py` must block it because `touched_files` includes an immutable path
(`evals/routing/gold/...`). This is the "candidate cannot mutate evaluator / oracle / gold / budget /
casebooks / sealed data" acceptance criterion, demonstrated live. It is retained, never promoted.
