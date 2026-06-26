# GEPA shadow campaigns

GEPA/autoresearch shadow campaigns (`docs/gepa-autoresearch-implementation-plan.md`,
`docs/decisions/0002-gepa-autoresearch-scope.md`). This directory holds **shadow** campaigns:
optimizer/adapters propose candidate technique-card variants, the frozen evaluators gate and score
them, and a human promotes through PR review. The shadow runner **promotes nothing** — it never
writes under `skills/` and never applies a candidate's diff.

## Layout

```
campaigns/<campaign-id>/
  campaign-manifest.json        # frozen-input hashes, mutable allowlist, immutable set, budgets, tracks
  candidates/<candidate-id>/
    candidate-manifest.json     # lineage, single mutation target, touched files, diff hash, bundle ref
    candidate.diff              # proposed patch (NOT applied in shadow mode)
    evidence-bundle.md          # human/model review surface
    gepa-trace.json             # Phase 8 optimizer trace/summary for generated candidates
    scores.json                 # per-candidate index into report/replay results
  report.json / report.md       # runner output: gate verdict + scoreboard per candidate
  replay-report.json/.md        # primary + two replay summary
```

## Tools

- `tools/check-campaign.py` — the contract gate (Phase 1). Blocks undeclared/immutable touches, budget
  changes, frozen-input drift, diff-hash tamper, and missing bundles. A no-op baseline is an allowed control.
- `tools/hash-campaign-inputs.py` — freeze a campaign's `frozen_inputs`, or `--check` a manifest for drift.
- `tools/run-gepa-shadow.py` — gate every candidate, run the gate-passing ones through the frozen
  scorers (`run-qualification.py` + `run-hermetic-bola.py` + `run-hermetic-fakemodel.py`), apply the
  keep/discard policy, write the report. `--campaign <manifest>`.
- `tools/run-gepa-real.py` — Phase 8 adapter/driver. Generates candidate artifacts, then optionally
  runs shadow scoring, replay, promotion-bundle rendering, and per-candidate `scores.json`. Backends:
  `--backend deterministic` (CI-safe control), `--backend gepa` (GEPA `optimize_anything` when the
  package and LM config exist), and `--backend auto` (GEPA if available, otherwise an explicit
  deterministic fallback recorded in `gepa-trace.json`).
- `tools/score-candidate.py` — the keep/discard policy (Phase 3). Eligibility gates (conformance,
  zero false-discovery, no protected regression, complete evidence contract, unchanged budget, single
  mutation) are hard vetoes → `block`. An eligible candidate is `allow` only if it adds a distinct
  clean confirmed coverage case or preserves coverage at ≥10% lower cost; otherwise `probe`. A
  `judge_note` is advisory and can never override the mechanical verdict.
- `tools/replay-candidate.py` — the replay & variance gate (Phase 4). Primary + two fresh-session
  replays at identical benchmark version and budget; downgrades a non-reproducible `allow` to `probe`,
  never upgrades. Writes `candidates/<id>/replays/` + a campaign `replay-report`.
- `tools/render-promotion-bundle.py` — the promotion bundle + PR path (Phase 5). Joins the Phase 3 and
  replay-adjusted verdicts with the diff, manifests, scorer/replay results, cost comparison, redaction
  report, and human checklist. Promotable only if the replay-adjusted verdict is `allow` AND redaction
  is clean; otherwise archived-only. Promotes nothing — promotion is a reviewed PR on an isolated
  branch (`.github/PULL_REQUEST_TEMPLATE/gepa-promotion.md`).
- `tools/apply-candidate-eval.py` — candidate-applied evaluation (Phase 9). Gates each candidate, then
  actually **applies its diff in an isolated `git worktree` at HEAD** (the live tree is asserted
  byte-identical), re-runs `check-conformance.py` against the patched workspace, and feeds the measured
  result through the keep/discard policy. A variant that breaks the harness now `block`s by measurement
  (not assumption); a clean variant is `probe` until `--backend model` (an LM) re-routes against the
  patched workspace to produce a real behavioral coverage delta. Promotes nothing.

## Shadow honesty

The Phase 8 adapter can produce real candidate deltas, but the frozen scorers do not read technique
cards, so applying a card variant cannot move routing/coverage without a model. **Phase 9
(`tools/apply-candidate-eval.py`)** now applies each candidate diff in an isolated `git worktree` and
re-measures: the model-free signal it gains is **conformance against the patched tree** (a card-breaking
variant blocks by measurement), while behavioral coverage delta stays 0 until `--backend model` puts an
LM in the loop. So the chain is now optimizer → manifest/diff/evidence → contract gate → frozen
scorers → replay → promotion bundle → **isolated apply + re-measure**. The remaining model-dependent
step is re-routing the blind orchestrator against the patched workspace to earn a real `allow`/`block`
from behavior rather than provenance.

## First campaign: `gepa-shadow-2026-06-26`

Three independent tracks (`task-reframing` variant, `decomposition` variant, one new
`output-anchored-review` technique card), a no-op `cand-baseline` control, and one intentionally
invalid `cand-invalid-edits-gold` candidate that tries to win by relabeling routing gold — and is
blocked at the gate. Run it with:

```
python3 tools/run-gepa-shadow.py --campaign evals/gepa-shadow/campaigns/gepa-shadow-2026-06-26/campaign-manifest.json
```

This campaign is historical provenance. Later routing/crosswalk expansion intentionally drifted some
of its pinned inputs, so CI no longer treats it as the active frozen-input sentinel. Use the Phase 8
campaign below for current integrity checks.

## Phase 8 adapter campaign: `gepa-phase8-2026-06-26`

This campaign freezes the broader evaluator (routing case-a/b + rotation-01 + rotation-02,
false-discovery, adversarial candidates, no-model BOLA, and four fake-model hermetic targets). It
generates:

- one `task-reframing` candidate;
- one `decomposition` candidate;
- one new `output-anchored-review` technique-card candidate;
- a no-op baseline; and
- one invalid gold-touch control that must block.

Local execution used the deterministic backend because GEPA is not installed/configured in this
environment:

```
python3 tools/run-gepa-real.py --campaign evals/gepa-shadow/campaigns/gepa-phase8-2026-06-26/campaign-manifest.json --backend deterministic
```

To run an actual GEPA optimization later, install/configure GEPA and use:

```
python3 tools/run-gepa-real.py --campaign evals/gepa-shadow/campaigns/gepa-phase8-2026-06-26/campaign-manifest.json --backend gepa
```
