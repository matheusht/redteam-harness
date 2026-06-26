# Promotion bundle — cand-task-reframing-001

**Status: NOT PROMOTABLE — archived only**  ·  verdict (replay-adjusted): `probe`  ·  campaign `gepa-shadow-2026-06-26`

This bundle promotes nothing. Promotion is a human action via a reviewed PR on an isolated branch; the diff is NOT applied here and nothing is written under `skills/`.

## Mutated component (single)
`evals/gepa-shadow/campaigns/gepa-shadow-2026-06-26/candidates/cand-task-reframing-001/candidate-manifest.json` → see `diff`. The PR must identify exactly one mutated component.

## Mechanical results
- false-discovery: invalid_accept_rate=0.000 (passed=True)
- cost: incumbent {'model_calls': 0, 'target_calls': 5} vs candidate {'model_calls': 0, 'target_calls': 5} (Δ 0.0%)
- redaction: clean

## Review checklist
- [x] Single mutated component identified: skills/techniques/task-reframing/
- [x] No immutable file touched (scope fence held at the contract gate)
- [x] False-discovery invalid_accept_rate == 0
- [x] Replay-stable: primary + 2 fresh-session replays reproduced
- [x] Diff hash matches candidate_hash
- [x] Redaction clean: no secret shapes in diff or evidence bundle
- [ ] HUMAN: read the diff; the change is benign and in scope
- [ ] HUMAN: the evidence bundle justification holds
- [ ] HUMAN: approve Plane-1 promotion via this PR (no direct-to-main, no manual copy)

## Artifacts
- candidate manifest: `evals/gepa-shadow/campaigns/gepa-shadow-2026-06-26/candidates/cand-task-reframing-001/candidate-manifest.json`
- campaign manifest: `evals/gepa-shadow/campaigns/gepa-shadow-2026-06-26/campaign-manifest.json`
- diff: `evals/gepa-shadow/campaigns/gepa-shadow-2026-06-26/candidates/cand-task-reframing-001/candidate.diff`
- scores: `evals/gepa-shadow/campaigns/gepa-shadow-2026-06-26/report.json`
- replays: ['evals/gepa-shadow/campaigns/gepa-shadow-2026-06-26/candidates/cand-task-reframing-001/replays/replay-summary.json']
