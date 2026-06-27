# Phase 12-13 — Constrained GEPA v2 and behavioral bridge

**Status:** proposed long-running implementation plan\
**Expected duration:** 3-6 focused hours if local Ollama/GEPA setup is available; stop honestly on
external backend blockers.\
**Depends on:** Decisions 0002 and 0004, Phase 10H0, Phase 10I, Phase 11, and the current
`gepa-real-2026-06-27` evidence.\
**Does not authorize:** live engagements, Zone-2 PoCs, evaluator/oracle/scorer/gold/casebook/budget
mutation, sealed holdout access, automatic promotion, or direct Plane-1 edits.

## Purpose

Phase 11 proved that a real GEPA optimizer can enter the loop and fail safely: the unconstrained
proposer drifted off-scope, and measured materialization blocked it.

Phase 12-13 should not broaden the project. It should tighten the learning loop:

```text
GEPA proposes in-scope technique variant
  -> isolated materialization
  -> if materialization blocks: authoritative block
  -> if materialization allows: real-LM behavioral evaluation
  -> replay / bundle / archive
```

The goal is not to force a win. The goal is to make a win impossible to fake.

## Phase 12 — Constrained GEPA v2

### Objective

Make GEPA produce in-scope, schema-valid technique-card variants, or fail honestly with evidence.

### Design constraints

1. GEPA may mutate exactly one declared technique component per candidate.
2. GEPA must not create or edit evaluator, scorer, oracle, gold, casebook, budget, route qualification,
   sealed, CI, or schema files.
3. Use a real in-scope seed instead of an empty new-card seed.
4. The objective must be scope-anchored to this harness:
   - LLM-application red-team technique cards;
   - benign safe-signal objectives;
   - oracle controls;
   - contamination rule-out;
   - replay discipline;
   - no payload library;
   - no exploit-dev / pwn / malware / credential content.
5. Candidate front matter must be structurally valid before any behavioral claim is considered.
6. An off-scope but structurally valid card is still a failed candidate. Do not call it a gap closure.

### Suggested implementation surface

- `tools/run-gepa-real.py`
- campaign manifest under `evals/gepa-shadow/campaigns/gepa-constrained-v2-<date>/`
- candidate artifacts under that campaign's `candidates/`
- existing `apply-candidate-eval.materialize_candidate`
- existing promotion-bundle renderer

### Candidate tracks

Prefer a narrow initial campaign:

1. **Technique variant track:** mutate one existing technique card, preferably `skills/techniques/task-reframing/SKILL.md`
   or `skills/techniques/decomposition/SKILL.md`.
2. **Optional new-card track:** only if it uses an in-scope seed/template and strict front-matter requirements.

Do not run many candidates. A small number with good evidence is better than a wide noisy search.

### Feedback loop

For each constraint:

1. Add/identify a failing example from Phase 11 or a new adversarial fixture.
2. Implement the smallest constraint that blocks or redirects that failure.
3. Run the GEPA campaign.
4. Materialize every candidate.
5. Inspect whether failures are correctly labeled:
   - `block` for off-scope, malformed, immutable-touching, or non-conformant candidates;
   - `probe` for clean but behaviorally neutral candidates;
   - `allow` only if later behavioral evaluation proves improvement.

### Acceptance criteria

- GEPA artifacts clearly identify model/backend, seed, objective, mutated component, and candidate hash.
- At least one of these is true:
  - GEPA produces an in-scope, schema-valid, materialization-allow candidate; or
  - GEPA fails honestly, with every candidate blocked/probed for explicit measured reasons.
- No off-scope candidate is promoted, counted as learning, or treated as a discovered gap.
- `autonomous_gap_closure_count` remains `0` unless the strict Decision-0004 criteria are actually met.

### Hard stop

If GEPA cannot be installed/configured, or the local LM is unavailable, record an immutable skipped/failed
artifact and stop. Do not substitute deterministic or simulator success for a real GEPA run.

## Phase 13 — GEPA to real-LM behavioral bridge

### Objective

Close the Phase-11 integration gap: a materialized-allow GEPA candidate must be evaluated by the
real-LM behavioral evaluator before any behavioral-learning claim.

### Current gap

`tools/run-gepa-real.py` currently runs:

```text
GEPA generation
  -> shadow score
  -> replay
  -> promotion bundle
```

That is enough for artifact containment, but not enough for behavioral learning.

### Required flow

For each GEPA candidate:

```text
contract preflight
  -> isolated git apply --index
  -> measured materialization
  -> if materialization == block:
       authoritative_verdict = block
       do not run behavioral eval
  -> if materialization == allow:
       run blind broker-mediated real-LM behavioral eval
       require primary + 2 fresh-session replay
       authoritative_verdict = behavioral verdict
```

### Suggested implementation surface

- `tools/run-gepa-real.py`
- `tools/run-behavioral-eval.py` public entrypoint or importable helper
- campaign artifacts under `evals/gepa-shadow/campaigns/gepa-constrained-v2-<date>/`
- promotion bundle schema/report fields

Prefer composition over a new framework. If a helper is needed, extract the smallest function that runs
behavioral evaluation for one materialized candidate and returns a structured result.

### Behavioral bridge requirements

1. Real-LM backend only for behavioral claims.
2. Missing model backend returns skipped/non-success and prevents behavioral-learning claims.
3. Broker events, not model final claims, determine coverage/FDR/cost.
4. Same budget/seed/version across incumbent and candidate.
5. Routing qualification remains a protected capability, not coverage.
6. FDR remains a hard veto.
7. Materialization-blocked candidates do not get replay-stability credit.
8. A simulator/fake run may remain a self-test, but cannot authorize promotion.

### Artifact contract

Each candidate result should expose:

- `shadow_verdict`
- `materialization_verdict`
- `behavioral_verdict` (`null` when materialization blocks)
- `authoritative_verdict`
- `authoritative_stage` (`materialization` or `behavioral`)
- `coverage_delta`
- `fdr_invalids`
- `cost`
- `replay`
- `promotable`
- links to materialization summary, broker events, replay report, and candidate diff

### Acceptance criteria

- A materialization-blocked GEPA candidate has:
  - `authoritative_stage = materialization`;
  - `authoritative_verdict = block`;
  - no behavioral eval claim.
- A materialization-allow GEPA candidate has:
  - a real-LM behavioral run artifact, or an honest skipped/failed artifact;
  - broker-owned event evidence;
  - strict 3/3 replay before any `allow`.
- Promotion bundles lead with the authoritative verdict.
- No candidate is called better from shadow score alone.
- No automatic Plane-1 edit occurs.

### Hard stop

If no GEPA candidate passes materialization, Phase 13 should not fabricate a behavioral run. Stop after
recording that the bridge is implemented but unexercised, or record the bridge as not yet exercised.

If a candidate passes materialization but the real-LM backend is unavailable, record non-success and stop.

## Validation checklist

Run the relevant subset, then the full suite before commit:

- `python3 tools/check-conformance.py`
- `python3 tools/run-gepa-real.py --self-test`
- `python3 tools/render-promotion-bundle.py --self-test`
- `python3 tools/run-behavioral-eval.py --self-test`
- `python3 tools/ollama-researcher-cli.py --self-test`
- hash check for the current canonical behavioral campaign
- `git diff --check`

Also verify:

- no leaked worktrees or jail dirs;
- no raw model command secrets;
- no API keys, auth headers, JWTs, cookies, or target-specific sensitive content;
- unrelated dirty files remain untouched.

## Commit guidance

Prefer small commits:

1. `feat(gepa): constrain GEPA candidate generation to in-scope technique variants`
2. `feat(gepa): route materialized candidates into behavioral evaluation`
3. optional `docs(gepa): record Phase 12-13 outcomes`

Do not push unless explicitly asked.

## Final report template

- commits
- GEPA backend/model used
- candidate table: shadow/materialization/behavioral/authoritative verdicts
- whether the behavioral bridge was exercised
- tests run
- artifacts produced
- complexity added vs deleted
- `autonomous_gap_closure_count`
- blockers
- next recommended phase
