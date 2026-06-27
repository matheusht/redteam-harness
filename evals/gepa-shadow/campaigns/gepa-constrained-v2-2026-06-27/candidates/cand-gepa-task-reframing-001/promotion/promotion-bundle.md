# Promotion bundle — cand-gepa-task-reframing-001

**Status: NOT PROMOTABLE — archived only**  ·  **authoritative verdict: `probe`** (stage: `behavioral`)  ·  shadow/replay-adjusted: `probe`  ·  campaign `gepa-constrained-v2-2026-06-27`

This bundle promotes nothing. Promotion is a human action via a reviewed PR on an isolated branch; the diff is NOT applied here and nothing is written under `skills/`.

## Mutated component (single)
`evals/gepa-shadow/campaigns/gepa-constrained-v2-2026-06-27/candidates/cand-gepa-task-reframing-001/candidate-manifest.json` → see `diff`. The PR must identify exactly one mutated component.

## Mechanical results (shadow scoreboard — NOT authoritative when behavioral evidence is present)
- false-discovery: invalid_accept_rate=0.000 (passed=True)
- cost: incumbent {'model_calls': 0, 'target_calls': 5} vs candidate {'model_calls': 0, 'target_calls': 5} (Δ 0.0%)
- redaction: clean

## Behavioral evidence (authoritative — real-LM broker-mediated)
- behavioral verdict: `probe`
- cost (broker-accounted): {'model_calls': 20, 'target_calls': 15}
- false-discovery invalids: []
- coverage delta vs incumbent: []
- replay (strict 3/3): {'incumbent_stable': True, 'candidate_stable': True}
- bridge result: `evals/gepa-shadow/campaigns/gepa-constrained-v2-2026-06-27/candidates/cand-gepa-task-reframing-001/bridge-result.json`
- behavioral run: `evals/gepa-shadow/campaigns/gepa-constrained-v2-2026-06-27/behavioral/runs/model-completed-20260627T192333Z`
- broker events: `evals/gepa-shadow/campaigns/gepa-constrained-v2-2026-06-27/behavioral/runs/model-completed-20260627T192333Z/events.jsonl`

## Review checklist
- [x] Single mutated component identified: skills/techniques/task-reframing/
- [x] No immutable file touched (contract gate allowed the candidate)
- [x] Measured boundary authoritative: isolated `git apply --index` + measured tree + trusted conformance == allow
- [x] False-discovery invalid_accept_rate == 0
- [x] Replay-stable: primary + 2 fresh-session replays reproduced
- [x] Diff hash matches candidate_hash
- [x] Redaction clean: no secret shapes in diff or evidence bundle
- [ ] HUMAN: read the diff; the change is benign and in scope
- [ ] HUMAN: the evidence bundle justification holds
- [ ] HUMAN: approve Plane-1 promotion via this PR (no direct-to-main, no manual copy)

## Artifacts
- candidate manifest: `evals/gepa-shadow/campaigns/gepa-constrained-v2-2026-06-27/candidates/cand-gepa-task-reframing-001/candidate-manifest.json`
- campaign manifest: `evals/gepa-shadow/campaigns/gepa-constrained-v2-2026-06-27/campaign-manifest.json`
- diff: `evals/gepa-shadow/campaigns/gepa-constrained-v2-2026-06-27/candidates/cand-gepa-task-reframing-001/candidate.diff`
- scores: `evals/gepa-shadow/campaigns/gepa-constrained-v2-2026-06-27/report.json`
- replays: ['evals/gepa-shadow/campaigns/gepa-constrained-v2-2026-06-27/candidates/cand-gepa-task-reframing-001/replays/replay-summary.json']
