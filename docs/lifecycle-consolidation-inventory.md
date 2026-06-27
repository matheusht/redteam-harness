# Lifecycle consolidation — inventory & authority map (Phase 14A/14B)

The experiment lifecycle is one pipeline:

```text
preflight -> apply -> measure -> score -> replay -> record
```

The pieces already exist and are individually tested. They were just spread across several scripts and
artifact layers. This document classifies every entrypoint, names the **one** public flow, and defines
the shared lifecycle-result contract. **It changes no verdict semantics.**

## The one public flow

```text
python3 tools/run-experiment-lifecycle.py \
  --campaign <campaign-manifest.json> \
  --backend deterministic|gepa \
  --behavioral-backend none|fake|model [--behavioral-model-cmd "..."] \
  [--candidate <id>]
```

It **composes** the existing tested functions (it reimplements none of them) and writes one
`lifecycle-result.json` per candidate + a campaign `lifecycle-report.json`. It writes only under the
campaign directory; it never writes to `skills/` or Plane 1.

## Authority rule (Decision 0004 / Phase 10H0)

The **measured materialization** is the boundary, and the **broker-mediated behavioral verdict** is the
authoritative learning signal. The deterministic shadow scoreboard is **advisory** — it does not apply
the diff and must never be read as the authoritative verdict. Precedence:

```text
materialization-block > off-scope > behavioral > shadow
```

## Entrypoint classification

| Tool | Class | Lifecycle stage(s) | Authoritative output | Advisory output | Self-test |
| --- | --- | --- | --- | --- | --- |
| `run-experiment-lifecycle.py` | **public** (the command to run) | record (composes all) | `lifecycle-result.json` (`authoritative_stage`/`authoritative_verdict`/`promotable`) | — | yes |
| `run-gepa-real.py` | internal orchestrator (building block) | apply→…→record + `behavioral_bridge` | `bridge-result.json` (per candidate) | `gepa-adapter-report.json`, shadow `report.json` | yes |
| `apply-candidate-eval.py` | internal building block | **measure** (`materialize_candidate`) | materialization verdict (applied-tree, conformance) | deterministic candidate-applied eval | yes |
| `run-behavioral-eval.py` | internal building block | **score (behavioral)** (`run_cli`, broker) | behavioral verdict + immutable run (`events.jsonl`) | — | yes |
| `check-campaign.py` | internal building block | **preflight** (`gate`) | — (preflight only — cannot authorize) | gate verdict (advisory) | yes |
| `replay-candidate.py` | internal building block | **replay** (variance, downgrade-only) | replay-stability (can only downgrade) | cost variance | yes |
| `render-promotion-bundle.py` | internal building block | **record** (promotion bundle) | `promotion-bundle.json` (`authoritative_verdict`, `behavioral_evidence`, `promotable`) | shadow "Mechanical results" (labelled non-authoritative) | yes |
| `run-gepa-shadow.py` | **historical/advisory** | score (deterministic scoreboard) | — (never authoritative; does not apply diffs) | shadow scoreboard | yes |
| `ollama-researcher-cli.py` | researcher backend (model-cmd) | — (drives `score:behavioral`) | — (broker owns truth) | — | yes (offline) |
| `claude-researcher-cli.py` | researcher backend (model-cmd) | — | — (broker owns truth) | — | yes (offline) |
| `fake-researcher-cli.py` | **test-only** | — | — | — | (is the CI control) |
| `score-candidate.py` | internal building block | score (keep/discard policy) | keep/discard verdict | — | yes |
| `score-routing.py`, `score-false-discovery.py`, `run-qualification.py`, `run-hermetic-*.py` | internal scorers/benchmarks | measure (frozen scorers) | scorer outputs | — | yes |
| `hash-campaign-inputs.py` | internal utility | record (frozen-input integrity) | drift report | — | yes |

## Overlapping responsibilities (why one public flow helps)

- **Two verdict layers used to be readable side by side.** The shadow scoreboard (`run-gepa-shadow`)
  emits `probe`/`block` without applying the diff; the measured boundary (`apply-candidate-eval`) +
  behavioral evaluator (`run-behavioral-eval`) emit the authoritative verdict. Phase 10H0/13 made the
  measured/behavioral answer authoritative and the promotion bundle leads with it; Phase 14 adds the
  single `lifecycle-result.json` so a reader never has to know the precedence by heart.
- **`run-gepa-real.py` already orchestrates the whole chain** (generate → shadow score → replay →
  promotion → behavioral bridge). The lifecycle entrypoint does not replace it — it *calls* its
  `generate(...)` and then assembles the unified record. `run-gepa-real` stays as the internal
  orchestrator/building block.

## The lifecycle-result contract (14B)

One machine-readable shape, schema `schemas/lifecycle-result.schema.json`. GEPA, materialization,
behavioral, replay, and promotion map **into** it; none of them invent competing truth fields.

```json
{
  "campaign_id": "...",
  "candidate_id": "...",
  "status": "completed | skipped | failed",
  "stages": {
    "preflight":      { "verdict": "allow|block", "reasons": [] },
    "materialization":{ "verdict": "allow|block", "conformance_passed": true,
                        "base_tree": "...", "candidate_tree": "...", "actual_paths": [] },
    "scope":          { "in_scope": true, "violations": [] },
    "behavioral":     { "verdict": "allow|block|probe", "cost": {}, "fdr_invalids": [],
                        "coverage_delta": [], "replay": {} } ,
    "replay":         { "stable": true },
    "promotion":      { "promotable": false }
  },
  "authoritative_stage": "materialization | scope | behavioral | shadow | unavailable",
  "authoritative_verdict": "allow | block | probe",
  "promotable": false,
  "artifacts": {
    "candidate_manifest": "...", "diff": "...", "materialization": "...",
    "bridge_result": "...", "broker_events": "...", "replay": "...", "promotion_bundle": "..."
  },
  "reasons": []
}
```

Field authority:

- **`authoritative_stage` + `authoritative_verdict` are the single truth a reader/automation should
  consult.** They come from the measured/behavioral layers (precedence above), never the shadow score.
- A `behavioral` stage that is `null` means the candidate blocked before behavioral evaluation
  (materialization/scope) or no behavioral run occurred — never a silent pass.
- **`status`** describes the run, not the verdict: a missing/unavailable real-LM backend yields
  `status = skipped` (or `failed`), and such a candidate is **never** `authoritative_verdict = allow`.
- Historical `bridge-result.json` and `promotion-bundle.json` remain readable and are linked under
  `artifacts`; they are not rewritten to match this prose.

## Acceptance (14A)

- Exactly one intended public flow is named: `tools/run-experiment-lifecycle.py`.
- Every script is classified public / internal / historical / test-only.
- No behavior changed in this subphase; this is documentation + a composing entrypoint.
