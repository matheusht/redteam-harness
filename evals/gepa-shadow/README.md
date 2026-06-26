# GEPA shadow campaigns

Phase 2 of the GEPA autoresearch plan (`docs/gepa-autoresearch-implementation-plan.md`,
`docs/decisions/0002-gepa-autoresearch-scope.md`). This directory holds **shadow** campaigns: GEPA
proposes candidate technique-card variants, the frozen evaluators gate and score them, and a human
promotes through PR review. The shadow runner **promotes nothing** — it never writes under `skills/`
and never applies a candidate's diff.

## Layout

```
campaigns/<campaign-id>/
  campaign-manifest.json        # frozen-input hashes, mutable allowlist, immutable set, budgets, tracks
  candidates/<candidate-id>/
    candidate-manifest.json     # lineage, single mutation target, touched files, diff hash, bundle ref
    candidate.diff              # proposed patch (NOT applied in shadow mode)
    evidence-bundle.md          # human/model review surface
  report.json / report.md       # runner output: gate verdict + scoreboard per candidate
```

## Tools

- `tools/check-campaign.py` — the contract gate (Phase 1). Blocks undeclared/immutable touches, budget
  changes, frozen-input drift, diff-hash tamper, and missing bundles. A no-op baseline is an allowed control.
- `tools/hash-campaign-inputs.py` — freeze a campaign's `frozen_inputs`, or `--check` a manifest for drift.
- `tools/run-gepa-shadow.py` — gate every candidate, run the gate-passing ones through the frozen
  scorers (`run-qualification.py` + `run-hermetic-bola.py`), apply the keep/discard policy, write the
  report. `--campaign <manifest>`.
- `tools/score-candidate.py` — the keep/discard policy (Phase 3). Eligibility gates (conformance,
  zero false-discovery, no protected regression, complete evidence contract, unchanged budget, single
  mutation) are hard vetoes → `block`. An eligible candidate is `allow` only if it adds a distinct
  clean confirmed coverage case or preserves coverage at ≥10% lower cost; otherwise `probe`. A
  `judge_note` is advisory and can never override the mechanical verdict.

## Shadow honesty

There is no model in the loop yet, so candidates are scored against the campaign's frozen baseline
benchmark outputs (`evals/qualification/examples/`). Coverage delta vs the incumbent is therefore 0 by
construction. Phase 2 proves the gate → scorer → report chain runs end to end and that an invalid
candidate (one that edits the gold) is blocked. Per-candidate model-generated outputs, the
keep/discard utility comparison (Phase 3), and replay (Phase 4) come next. Promotion stays PR-only.

## First campaign: `gepa-shadow-2026-06-26`

Three independent tracks (`task-reframing` variant, `decomposition` variant, one new
`output-anchored-review` technique card), a no-op `cand-baseline` control, and one intentionally
invalid `cand-invalid-edits-gold` candidate that tries to win by relabeling routing gold — and is
blocked at the gate. Run it with:

```
python3 tools/run-gepa-shadow.py --campaign evals/gepa-shadow/campaigns/gepa-shadow-2026-06-26/campaign-manifest.json
```
