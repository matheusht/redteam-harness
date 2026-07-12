# engine/gates.md — human-in-the-loop gates

The harness runs autonomously *between* gates; the human supplies steering + authorization *at*
them. The agents supply tireless execution, validation, and bookkeeping.

## 1. Scope gate (blocking)
`engagements/<target>/scope.md` must be **filled and signed** before the loop runs: surfaces, the
benign safe-objective set, the escalation ceiling, **impact-demo authorization (y/n)**, accounts/
fixtures, operator sign-off. **No scope file, no run.**

## 2. Environment fidelity and safety preflight (blocking)
Before attempts, run `python3 tools/run-engagement.py preflight` for the demonstrated local mode
(`git`, `package`, or `local_runtime`). A usable preflight binds the signed scope hash, expected and
observed target identity, runtime digest, exact non-executed reproduction argv, cleanup state, an
explicit operator-redaction attestation, and non-secret account labels. `blocked` or `needs_review` does not become active. Activating a different
target identity prevents later attempts from citing the stale preflight.

The advisory Zone value is only `clear_local`, `review_required`, or `unknown`; it is never
authorization. A `review_required` artifact instead needs a fresh signed-operator confirmation bound
to exactly one future artifact id, the active environment and scope, a still-open structured cleanup
obligation, and an expiry no more than 30 minutes after confirmation. Preflight never creates Zone-2 bytes, executes the reproduction argv, contacts a live
target, or stores credential values. Known secret-shaped content is rejected, and operator redaction
remains mandatory because a clean pattern scan is not proof of absence.

## 3. Decision gates
Structured questions at escalation boundaries (focus areas, account setup, sensitive-artifact
handling). Asked, not assumed.

## 4. Impact-escalation confirm (blocking, Zone-2 only)
Before creating **any** real PoC artifact (worm/exfil chain/etc.):
1. `scope.md#impact_demo_authorized` must be true (category authorized), AND
2. a **live human confirmation** is obtained at the moment — the loop **pauses and asks**; it never
   creates a harmful artifact autonomously, even when the category is authorized, AND
3. the artifact is contained (inert where possible) and logged in `cleanup.md`.

## 5. Review gate
Operator reviews assembled findings before any escalation up the severity ladder
(self → stored/persistent → cross-user), each rung gated on the prior rung actually succeeding —
no wasted runs, no unauthorized reach.

## 6. Cleanup gate
Every artifact the harness created (test chat, shared object, uploaded fixture, planted canary) is
recorded in `cleanup.md` with its revert action and status. Unresolved cleanup **blocks pattern
promotion**. Redact secrets always.

## 7. Memory disposition and closure gate
Every completed or blocked engagement records exactly one operator-reviewed `promote`, `defer`, or
`no_novel_lesson` disposition with typed provenance and sanitization metadata. Every retained text field in a
`promote` proposal is checked against operator-enumerated target terms, referenced IDs, endpoints,
commands, and recipe shapes; the operator also attests source comparison and abstraction review. Positive controls,
refutations, reward-hacked proof shapes, and environment failures may be lessons; promotion is never
forced. `record-memory` changes only engagement-local immutable records. Even `promote` cannot write
`skills/`, casebooks, or other Plane-1 memory; that requires a later scrubbed human-reviewed PR.

`close` is operator-only and requires terminal coverage, a structured cleanup disposition for every
obligation, no pending review, accepted/submitted current-revision reports for filed findings, and
the committed memory disposition. Narrative edits cannot satisfy these gates. Operator identity is anchored in the trusted local OS,
signed scope, and engagement filesystem; repository hash chains are tamper-evident commitments, not
cryptographic authentication against total host/filesystem compromise.
