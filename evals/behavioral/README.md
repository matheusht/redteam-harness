# evals/behavioral/ — blind, broker-mediated, paired behavioral evaluation (Phase 10 / 10F / 10G)

Where technique candidates earn a verdict from **behavior**, not provenance. A card-guided researcher
chooses probes and adjudicates on hermetic episodes, so the technique wording can change outcomes — the
thing Phases 2–9 could not measure (the frozen scorers don't read technique cards). Phase 10F/10G made
this boundary trustworthy.

## The integrity boundary (load-bearing)

```
EVALUATOR process (holds gold, owns the BROKER)        RESEARCHER (blind, mediated)
  episode { signal, contaminated, gold }                view { card, task, schema, budget }
  broker executes probes, logs every event   <-------- requests one action per turn (probe | final)
  broker returns ONLY a mediated response     -------->  adjudicates from RESPONSES; its claims are advisory
  broker adjudicates coverage/FDR from its OWN event log
```

- **The broker is authoritative.** It decides which probes executed, the target responses, the
  controls, the fresh-session replay, the evidence refs, and the model/target call + token + elapsed
  ledger. A `confirmed` counts only when the broker's event log proves every oracle requirement.
  Missing, invented, duplicated, or out-of-budget events block or downgrade — the model cannot
  self-report that a control or replay happened.
- **Capability blindness — a transport boundary, not a security sandbox.** The researcher receives only
  the serialized view + mediated responses; the `model` adapter runs as a subprocess in an empty scratch
  cwd with a scrubbed env, and the action vocabulary has no file-read. This bounds the contract and
  reduces accidental leakage, but a scrubbed env + empty cwd do **not** prevent a hostile process from
  reading absolute filesystem paths or using the network. Before any real-model qualification, run the
  researcher under OS-level isolation or a remote, capability-limited model service with no local
  filesystem access (see Decision 0003). `assert_blind()` remains a defense-in-depth payload check.

## Metric boundary

- **Routing qualification is a MEASURED protected capability** (`run-qualification`), a hard gate — not
  counted as coverage, never hardcoded true.
- **Coverage** = hermetic episodes the broker confirms under the full oracle (positive class, final
  `confirmed`, the required controls actually executed, controls clean, replay stable).
- **False-discovery** = any non-positive episode confirmed — a hard veto.
- **Cost** is broker-accounted. A `fake`/simulator cost win can never authorize promotion.

## Canonical gating + immutable runs (10F)

Every candidate passes the canonical campaign/candidate contract gate (`check-campaign.py`), is applied
in an isolated `git worktree`, and has conformance MEASURED in the patched workspace. Eligibility flags
(`conformance_passed`, `budget_unchanged`, `single_mutation`, `evidence_contract_complete`) and the
protected routing capability are measured, never hardcoded. Each invocation writes an immutable
`runs/<run-id>/{run-manifest.json,report.json,report.md,events.jsonl}` pinning campaign/candidate/card/
episode/scorer/adapter hashes, backend/model/config, seeds, budgets, timestamps, and status. A skipped
or failed run never overwrites a completed one.

Incumbent and candidate run **paired** in a primary + two fresh sessions with recorded anonymized A/B
order; a hermetic `allow` requires strict 3/3 reproduction.

## Episodes

`episodes/{task-reframing,decomposition}.json` — positive / held / refuted / contamination / control.
The `task` is a neutral surface observation (the only scenario text the researcher sees);
`signal_available` / `contaminated` / `class` / `gold_verdict` are evaluator-only. Contamination is the
discriminator: only a researcher that runs the negative control + fresh replay catches it; a card that
drops them (or overclaims) confirms it → FDR → block.

## Tools

- `tools/run-behavioral-eval.py` — the broker + driver. `--backend fake` (default, CI control, cannot
  promote) or `--backend model` (provider-neutral subprocess adapter; unavailable → recorded `skipped`,
  NON-SUCCESS).
- `tools/researcher_adapter.py` — provider-neutral researcher contract: strict action/final schemas,
  bounded malformed-output retries, jailed subprocess, usage accounting, `ModelUnavailable` on no command.
- `tools/fake-researcher-cli.py` — deterministic CLI implementing the wire contract (CI tests the
  subprocess protocol without credentials).
- `tools/build-behavioral-campaign.py` — regenerates the canonical campaign deterministically from HEAD.

```
python3 tools/build-behavioral-campaign.py
python3 tools/run-behavioral-eval.py --campaign evals/behavioral/campaigns/behavioral-canonical-v2-2026-06-27/campaign-manifest.json
python3 tools/run-behavioral-eval.py --self-test
```

## Canonical campaign: `behavioral-canonical-v2-2026-06-27`

Canonical campaign + candidate manifests + real diffs. `fake`-backend run (`runs/fake-completed-*`):
no-op `cand-baseline` → **probe** (a no-op can never `allow`); `cand-efficient-task-reframing` →
**allow** by broker-measured cost cut (non-promotable for the fake backend); `cand-decomposition` →
**probe**; `cand-degraded` (test fixture, promotion-excluded) → **block** (confirms contamination →
FDR); `cand-invalid-immutable` → **block** at the canonical gate (touches frozen gold).

## Phase 10G — real-model qualification status

The adapter contract + deterministic fake adapter + protocol tests are complete. A real blind
qualification run is **BLOCKED/SKIPPED**: no sufficiently isolated LM backend is configured in this
environment. The `runs/model-skipped-*` run records this honestly (status `skipped`, NON-SUCCESS). A
simulator/fake success is **never** presented as real-model qualification, and nothing promotes
automatically.
