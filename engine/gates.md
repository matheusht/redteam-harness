# engine/gates.md — human-in-the-loop gates

The harness runs autonomously *between* gates; the human supplies steering + authorization *at*
them. The agents supply tireless execution, validation, and bookkeeping.

## 1. Scope gate (blocking)
`engagements/<target>/scope.md` must be **filled and signed** before the loop runs: surfaces, the
benign safe-objective set, the escalation ceiling, **impact-demo authorization (y/n)**, accounts/
fixtures, operator sign-off. **No scope file, no run.**

## 2. Environment fidelity and safety preflight
`preflight` is a **Notebook** collection operation. The broker records exact source/runtime identity,
non-executed reproduction argv, cleanup state, automated secret-shape coverage, and truthful local
principal/session provenance. It cannot claim operator redaction or authorization. A complete,
credential-free, stable `clear_local` collection may activate automatically. `blocked` does not.
`needs_review` remains inactive until `review-preflight` applies a separate immutable operator review
through an exact digest-bound authority request. Only the newest pending preflight may be reviewed;
the collector record is never rewritten. Review does not authorize Zone-2.

Git collection uses a pinned executable, sanitized configuration, repeated FD-bound identity and
tracked/untracked/ignored secret scans. Package/local target and selected configuration bytes are
identity-bound across scanning. Only secret classes and hashes are retained, never secret values.
A clean shape scan is not proof that no secret exists.

The advisory Zone is only `clear_local`, `review_required`, or `unknown`; it is never authorization.
A Zone-2 artifact requires a fresh signed-operator confirmation bound to one future artifact id,
planned byte digest/size/path, active environment and scope, an open cleanup obligation, and at most a
30-minute expiry. The kernel rechecks all bindings under lock immediately before exclusive creation.

## 3. Operation tiers and asynchronous authority
Every public command and event is fail-closed through `engine/operation-capabilities.json`:

- **Notebook:** the local broker may collect and append truthful records non-interactively.
- **Authority:** the broker first records `pending_authority`; an operator may approve/reject/expire/
  supersede only the exact action digest. Approval is current, lane-bound, executor/session-bound,
  one-use, and never retrospective. Unrelated Notebook lanes continue.
- **Real-world:** fresh live confirmation is still required before capability-bearing bytes or effects.

Use `runtime-identity --role broker` for the OS-principal/POSIX-session provenance values. This is a
truthful local trust boundary, not authentication against another process with total access to the
same user account or filesystem. Agents never become the signed operator.

Required gates are correct behavior, not stalls. Only a Notebook operation blocked contrary to the
frozen capability matrix is an improper stall.

## 4. Impact-escalation confirm (blocking, Zone-2 only)
Before creating **any** real PoC artifact (worm/exfil chain/etc.):
1. `scope.md#impact_demo_authorized` must be true (category authorized), AND
2. a **live human confirmation** is obtained at the moment — the loop **pauses and asks**; it never
   creates a harmful artifact autonomously, even when the category is authorized, AND
3. the artifact is contained (inert where possible) and logged in `cleanup.md`.

## 5. Review and filing gates
`record-review` commits an external independent review and its typed event through one canonical
Notebook boundary. The event truthfully names the broker that committed it and separately binds the
reviewer/run identity in the immutable review. Independence, current subject, controls, replay, and
claim tuple remain reducer-validated. A review cannot file a finding.

`revise-finding` is a separate Authority operation: an approved exact digest lets the broker commit
one contiguous revision, while operator authority, reviewer adjudication, evidence, and filing remain
distinct. Regrade and Pocinator review truth/proof; report acceptance remains another operator-owned
transition. Severity escalation (self → stored/persistent → cross-user) remains rung-by-rung.

## 6. Cleanup gate
Every artifact the harness created (test chat, shared object, uploaded fixture, planted canary) is
recorded in `cleanup.md` with its revert action and status. Unresolved cleanup **blocks pattern
promotion**. Redact secrets always.

## 7. Non-authoritative flow telemetry
`tools/flow_telemetry.py` deterministically exports kernel facts and optional advisory runtime
observations. Generic normalized JSON and sanitized Claude Code metrics are supported. Prompts,
responses, arguments, commands, environment values, file contents, credentials, and target payloads
are forbidden. Missing runtime values remain `null` with measured/record coverage; live exports are
always `flow_telemetry`, never efficacy evidence. Telemetry cannot alter authority, tiering, claim
truth, independence, calibration, routing, severity, reports, or gates. No database, daemon,
scheduler, service, dashboard, live score, cross-runtime average, or optimizer exists.

## 8. Memory disposition and closure gate
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
