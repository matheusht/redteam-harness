## GEPA promotion: cand-baseline

- Campaign: `gepa-real-2026-06-27`
- Single mutated component: see `evals/gepa-shadow/campaigns/gepa-real-2026-06-27/candidates/cand-baseline/candidate.diff` (candidate manifest `evals/gepa-shadow/campaigns/gepa-real-2026-06-27/candidates/cand-baseline/candidate-manifest.json`)
- Authoritative verdict (measured materialization): `probe`
- Shadow/replay-adjusted verdict: `probe`
- False-discovery passed: True
- Redaction: clean

This candidate is NOT promotable (archived only). Do not apply the diff or merge.

Checklist (humans must tick the HUMAN items):
- [x] Single mutated component identified: skills/techniques/output-anchored-review/
- [x] No immutable file touched (contract gate allowed the candidate)
- [x] Measured boundary authoritative: isolated `git apply --index` + measured tree + trusted conformance == allow
- [x] False-discovery invalid_accept_rate == 0
- [x] Replay-stable: primary + 2 fresh-session replays reproduced
- [x] Diff hash matches candidate_hash
- [x] Redaction clean: no secret shapes in diff or evidence bundle
- [ ] HUMAN: read the diff; the change is benign and in scope
- [ ] HUMAN: the evidence bundle justification holds
- [ ] HUMAN: approve Plane-1 promotion via this PR (no direct-to-main, no manual copy)
