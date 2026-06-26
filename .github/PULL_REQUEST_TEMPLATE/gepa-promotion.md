<!--
Named PR template for promoting a GEPA shadow candidate into Plane 1.
Open a PR with ?template=gepa-promotion.md, or paste this and fill it from the candidate's
promotion-bundle (tools/render-promotion-bundle.py output). Promotion is PR-only: no direct-to-main,
no manual copy into skills/techniques/. A candidate is mergeable ONLY if its promotion bundle is
PROMOTABLE (replay-adjusted verdict = allow AND redaction clean).
-->

## GEPA candidate promotion

- **Candidate id:** `cand-...`
- **Campaign id:** `gepa-shadow-...`
- **Single mutated component:** `skills/techniques/.../` (exactly one — the PR must name it)
- **Promotion bundle:** `evals/gepa-shadow/campaigns/<id>/candidates/<id>/promotion/promotion-bundle.md`

### Gates (from the bundle — must all pass)
- [ ] Replay-adjusted verdict is `allow` (Phase 3 keep/discard ∧ Phase 4 replay)
- [ ] False-discovery invalid_accept_rate == 0
- [ ] Replay-stable: primary + 2 fresh-session replays reproduced
- [ ] Redaction clean: no secret shapes in the diff or evidence bundle
- [ ] Diff hash matches `candidate_hash`
- [ ] Scope fence held: no evaluator / oracle / gold / casebook / budget / schema file touched

### Human review
- [ ] I read the candidate diff; the change is benign and in scope
- [ ] The evidence-bundle justification holds
- [ ] Exactly one component is mutated by this PR
- [ ] I approve Plane-1 promotion (no direct-to-main; no manual copy into `skills/techniques/`)

> Probed or blocked candidates are archived, not promoted. Do not open this PR for them.
