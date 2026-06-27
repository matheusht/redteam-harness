## GEPA promotion: cand-gepa-invalid-gold-touch

- Campaign: `gepa-real-2026-06-27`
- Single mutated component: see `evals/gepa-shadow/campaigns/gepa-real-2026-06-27/candidates/cand-gepa-invalid-gold-touch/candidate.diff` (candidate manifest `evals/gepa-shadow/campaigns/gepa-real-2026-06-27/candidates/cand-gepa-invalid-gold-touch/candidate-manifest.json`)
- Authoritative verdict (measured materialization): `block`
- Shadow/replay-adjusted verdict: `block`
- False-discovery passed: True
- Redaction: clean

This candidate is NOT promotable (archived only). Do not apply the diff or merge.

Checklist (humans must tick the HUMAN items):
- [ ] Single mutated component identified: skills/techniques/output-anchored-review/
- [ ] No immutable file touched (contract gate allowed the candidate)
- [ ] Measured boundary authoritative: isolated `git apply --index` + measured tree + trusted conformance == allow
- [x] False-discovery invalid_accept_rate == 0
- [ ] Replay-stable: primary + 2 fresh-session replays reproduced — N/A: candidate blocked at materialization
- [x] Diff hash matches candidate_hash
- [x] Redaction clean: no secret shapes in diff or evidence bundle
- [ ] HUMAN: read the diff; the change is benign and in scope
- [ ] HUMAN: the evidence bundle justification holds
- [ ] HUMAN: approve Plane-1 promotion via this PR (no direct-to-main, no manual copy)
