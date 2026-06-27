# SUPERSEDED / archived — gepa-shadow-2026-06-26

This is a **historical shadow campaign** (the first deterministic GEPA shadow run). It is retained as
provenance and is **not** gated by CI. Do not run candidates against it and do not re-pin it.

## Why its integrity checks drift

Its `frozen_inputs` pin earlier hashes of evaluator inputs (e.g. `evals/routing/gold/rotation-01.gold.json`,
`evals/qualification/crosswalk.json`) that have since rotated, plus Phase-8-era tool hashes that later
hardening changed. `render-promotion-bundle.py --verify` against its bundle therefore reports drift —
the drift detector working as designed, not a regression.

## What NOT to do

Do **not** re-pin this campaign to current hashes to silence CI. Per Decision 0003/0004, an evaluator or
gold change produces a **new** campaign revision; prior revisions are append-only history.

## Where integrity is gated now

See `../gepa-phase8-2026-06-26/SUPERSEDED.md`. Frozen-input integrity is gated against
`evals/behavioral/campaigns/behavioral-canonical-v2-2026-06-27/`; the bundle drift machinery is covered by
`tools/render-promotion-bundle.py --self-test`; candidate authorization is the Phase 10H0 measured boundary.
