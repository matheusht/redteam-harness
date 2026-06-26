# Candidate cand-baseline — evidence bundle (no-op control)

**Track:** task-reframing (declared, but the candidate changes nothing)
**Mutation target:** `skills/techniques/task-reframing/`
**Parent:** baseline

## What this is

The retained **no-op control**. It touches no files and applies no diff. Its purpose is to anchor the
campaign: when scored against the baseline benchmark outputs it reproduces the incumbent result
(routing QUALIFIED, false-discovery invalid_accept_rate 0), so any future candidate's claimed delta is
measured against a real, reproducible control rather than an assumed one.

## Expected verdict: ALLOW (and never promoted)

`is_baseline: true`, `touched_files: []` → the gate allows it as a control. A baseline that touched any
file would block. Nothing is promoted.

## Replay (Phase 4)

Replay artifacts under `replays/` (primary + two fresh-session replays + `replay-summary.json`). The
control reproduces the incumbent scoreboard across all three runs at identical benchmark version and
budget (cost spread 0, replay-stable), which is exactly what anchors the campaign. Final verdict:
**probe** (a control is never promoted).
