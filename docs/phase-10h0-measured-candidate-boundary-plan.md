# Phase 10H0 — Authoritative measured candidate boundary

**Status:** proposed implementation plan\
**Expected duration:** 1–3 focused hours\
**Depends on:** Decisions 0002–0004, Phases 9–10G\
**Does not authorize:** real-model qualification, live engagements, evaluator co-evolution,
automatic promotion, or an autonomous controller

## Outcome

Replace patch-description authority with measured repository state.

`check-campaign` remains a pure, fast preflight for hashes, manifests, budgets, and obvious policy
violations. A candidate receives no final authorization until its patch is applied to an isolated
worktree and the resulting Git tree is measured.

This is the first concrete consolidation required by Decision 0004:

```text
preflight
  → isolated materialization
  → measured changed tree
  → policy comparison
  → trusted conformance
  → authoritative allow | block
```

Do not introduce a new framework, service, role hierarchy, or generic case abstraction.

## Phase 0 — Adopt the governing decision

Decision 0004 was reviewed and approved in discussion. Before implementation:

1. Change Decision 0004 from `draft for review` to `accepted`.
2. Mark Decision 0003 `superseded by Decision 0004`; retain it as historical provenance and add a
   forward pointer.
3. Update the decision index.
4. Replace current roadmap references that treat Decision 0003 as the live autonomy policy.
5. Keep Decision 0002 as GEPA scope/capability history.

Commit this documentation change separately from the implementation.

## Phase 1 — Define the contract before editing code

Document one authoritative materialization result:

```json
{
  "preflight": "pass | block",
  "apply": "pass | block",
  "base_tree": "sha256/tree id",
  "candidate_tree": "sha256/tree id",
  "declared_paths": [],
  "actual_paths": [],
  "paths_match": true,
  "allowlist_passed": true,
  "baseline_unchanged": true,
  "conformance_passed": true,
  "verdict": "allow | block",
  "reasons": []
}
```

Rules:

- Preflight `pass` is never equivalent to final `allow`.
- Apply and measurement occur in a clean detached worktree at committed `HEAD`.
- The candidate may never control the evaluator, checker, command, root, or comparison.
- Failures are fail-closed and recorded with explicit reasons.
- Existing manifests remain canonical declarations; Git state is canonical truth.

## Phase 2 — Materialize and measure

Extend the existing candidate-application machinery rather than adding another lifecycle tool.

Preferred mechanism:

```text
git worktree add --detach <tmp> HEAD
git apply --index <candidate.diff>
git diff --cached --name-only -z --no-renames HEAD
git write-tree
```

Measure:

- base tree id;
- candidate tree id;
- actual changed path set from the staged index;
- post-apply file type/mode for the declared technique component.

Policy:

- `actual_paths == declared touched_files`;
- every actual path is within the single mutation target and mutable allowlist;
- no actual path is immutable;
- baseline candidates require `candidate_tree == base_tree`;
- non-baseline candidates require at least one actual path and a changed tree;
- technique-card candidates must leave the declared `SKILL.md` as a regular file;
- trusted conformance is materialized from committed `HEAD`, never from candidate-controlled bytes;
- cleanup runs on success, block, exception, and timeout.

The existing patch parser may remain temporarily as preflight defense-in-depth. Do not delete it until
parity and adversarial tests prove the measured boundary catches every current rejection.

## Phase 3 — Make measurement authoritative

Audit all callers of `check-campaign.gate`, candidate application, scoring, behavioral evaluation,
replay, and promotion rendering.

Classify each use:

- **preflight-only:** may reject early, cannot authorize;
- **authoritative:** must consume the measured materialization result before `allow`, behavioral
  scoring, replay eligibility, or promotion eligibility.

At minimum:

- candidate-applied evaluation uses the shared measured result;
- behavioral evaluation uses the same result rather than reimplementing apply/gating;
- promotion cannot become eligible without a pinned successful materialization result;
- shadow-only reports label preflight success honestly and do not imply materialized authorization.

Avoid a broad rewrite. Extract only the smallest shared function/result required to remove duplicate
authority.

## Adversarial feedback loop

For each invariant:

```text
reproduce failure
  → add a failing fixture
  → implement smallest general fix
  → run targeted test
  → run full evaluator tests
  → inspect emitted result/artifacts
  → continue only when green
```

Required fixtures:

- declared card but actual evaluator/checker edit;
- mode-only patch;
- binary patch;
- rename and copy;
- symlink or non-regular post-state;
- new file and deletion;
- non-empty baseline;
- declared/actual mismatch;
- malformed or non-applying patch;
- immutable or out-of-allowlist path;
- candidate attempt to modify the conformance checker;
- cleanup after apply and measurement failure.

Never weaken an expected result to make a candidate pass. If an evaluator fixture is genuinely wrong,
change it separately, rebuild the incumbent, and preserve the prior revision.

After the same external blocker occurs three times, record it and finish all independent work. Do not
invent a successful result.

## Acceptance criteria

- No caller treats preflight success as final authorization.
- Final `allow` requires isolated apply, measured tree, exact path equality, allowlist compliance,
  baseline policy, and trusted conformance.
- Git state—not patch syntax—is authoritative.
- All existing valid campaign candidates retain their expected disposition.
- Every existing and new adversarial candidate blocks for the correct measured reason.
- Candidate, behavioral, replay, and promotion artifacts pin or reference the measured result.
- No candidate-controlled checker can grade the candidate.
- No worktrees, staged changes, or scratch directories leak.
- `autonomous_gap_closure_count` remains `0`; this phase adds trust, not autonomous learning.
- Full conformance and all tool self-tests pass.
- `git diff --check` is clean.
- Unrelated working-tree changes remain untouched.
- Roadmap, Decisions 0003/0004, evaluator README, and implementation notes agree.

## Commit policy

Prefer two commits:

1. `docs(decisions): adopt epistemic autonomy and complexity budget`
2. `refactor(eval): make materialized candidate state authoritative`

Do not rewrite the four existing Phase 10F–10G commits. Do not push unless explicitly requested.

## Explicitly deferred

- Real-LM behavioral qualification.
- Full lifecycle/front-door consolidation.
- Sealed holdout service.
- Novel GEPA candidate generation.
- Autonomous scheduling/controller.
- Live target execution or Zone-2 actions.

The next goal after this phase is real-LM qualification. After that, complete the broader lifecycle
consolidation before adding the autonomous campaign controller.
