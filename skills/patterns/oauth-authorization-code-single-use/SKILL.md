---
id: pattern.oauth-authorization-code-single-use
name: Authorization Code Single-Use Must Be Atomic
description: >
  An OAuth/OIDC authorization server checks an authorization code's unused
  state and later marks it used through a non-conditional write. Concurrent
  redemptions can both pass the stale read and each receive a token.
type: pattern
owasp: "A07:2021 Identification and Authentication Failures"
also: "CWE-367 Time-of-check Time-of-use Race Condition"
atlas: "—"
routes_to: ["vulns/authentication-bypass"]

activation:
  strong:
    - "authorization-code redemption reads an unused flag before a separate update whose predicate does not require unused state"
    - "the update result or affected-row count is not used to decide whether token issuance may continue"
    - "redemption is a separate find-then-delete pair (a lookup call followed by a distinct delete-by-identifier call) with no atomic claim primitive between them, so a second concurrent request can pass the lookup before the first delete completes (diff-derived: the removed `findVerificationValue` + `deleteVerificationByIdentifier` pair in better-auth GHSA-7w99-5wm4-3g79 — CONTESTED)"
    - "validate, token-creation, and grant/code deletion run as an unlocked sequence with no mutex or transaction spanning the three steps, letting two concurrent exchanges both pass validation before either deletes the grant (diff-derived: the unlocked `_validate()` / `_create_token()` / `_delete_grant()` sequence in sentry GHSA-mgh8-h4xc-pfmj — CONTESTED)"
  weak:
    - "a code record has a used flag but the transaction boundary is unclear"
    - "single-use enforcement is split between service code and a database helper"
  negative:
    - "one conditional atomic consume operation requires used = false and token issuance happens only when exactly one row changes"
    - "a transaction or lock covers both the unused-state decision and irreversible consume operation"
    - "the find-then-delete pair is replaced by a single atomic claim primitive, or the whole validate/issue/delete sequence is wrapped in a lock, so a concurrent second redemption observes null / lock contention instead of forming its own token set → likely held (diff-derived: the `consumeVerificationValue` atomic-claim swap in better-auth GHSA-7w99-5wm4-3g79, the `lock.acquire()` wrap around validate+create_token+delete_grant in sentry GHSA-mgh8-h4xc-pfmj)"

safe_signal:
  proxy: >
    Use a pinned local build, disposable database, synthetic user, and one
    newly issued synthetic code. Send exactly two concurrent token requests,
    then demonstrate that a second sequential request is rejected. Count
    successful responses and real token-issuer calls without using a custom
    code-store emulator or modifying the production redemption path.
  never: >
    Do not race another user's code, send concurrent requests to a deployed
    authorization server, or reuse any non-synthetic authorization code.

impact_escalation:
  enabled_by: scope.md#impact_demo_authorized
  requires: human_confirm
  containment: "local disposable database and synthetic user only; delete temporary test change and record cleanup"

oracle: [signal-oracle, adjudication-oracle, ghsa-fix-diff]
severity_rubric: { synthetic_double_redemption: needs_review, intercepted_code_race_with_cross-user_impact: high, source_only_toctou_without_reproduction: needs_review }

procedure:
  - "Trace the code lookup, unused-state check, consume write, and token issuance in the exact pinned release; record the database predicate and whether its result gates issuance."
  - "Use the real local HTTP router, service, database migrations, and one approved synthetic authorization session. Launch exactly two same-code token requests concurrently."
  - "Make the synthetic token issuer return distinguishable values only to observe independently reached issuance calls; do not replace routing, storage, or state-transition logic."
  - "Run a matched sequential control with a fresh code: first redemption succeeds and the second must return invalid_grant."
  - "Accept a signal only if both concurrent requests succeed and the real issuer is called twice; record database/runtime limitations if one request is serialized or rejected."
  - "Separate a local single-use violation from the independent question of how an attacker obtains a victim code and from confidential-client binding."

falsifiers:
  - "The real concurrent local route returns at most one success without test-injected scheduling or storage behavior."
  - "A conditional consume/lock outside the initially inspected helper prevents a second issuer call."
  - "The observed behavior comes from a test double or routing shortcut rather than the pinned redemption path."
---

## Real disclosed anchor(s) for this class (fix-diff-derived)
Priors/taxonomy from real disclosed GHSA fix commits — the vulnerable pre-patch shape and the guard
the fix added. Verbatim hunks + primary sources in `skills/oracles/references/ghsa-fix-diff-corpus.md`
(OAuth / OIDC flow flaws bucket, auth-code-reuse sub-shape); consult via the `ghsa-fix-diff` oracle.
**These are all *fixed* bugs, not live-bug claims:** a target matching a removed-line shape is a lead
to run through the funnel above, never a confirmation. Both anchors below are **CONTESTED**
(illustrative) — genuine fixes whose anchored hunk depends on a primitive or lock defined outside the
shown diff — cited here only for the single-use/atomic-consume mechanism shape, not as clean promotable
signatures.

**Non-atomic find-then-delete replaced by an atomic claim, `atomic-consume-swap`:**
- **GHSA-7w99-5wm4-3g79** (better-auth, fixed 1.6.11 @ `b4bc65a`): separate `findVerificationValue` +
  `deleteVerificationByIdentifier` calls → single `consumeVerificationValue` atomic claim-and-delete.
  Reachable at `POST /oauth2/token` (authorization_code grant). **CONTESTED** (illustrative): the
  atomicity guarantee lives in `consumeVerificationValue`, which is not present in the shown diff.

**Unlocked validate/issue/delete sequence wrapped in a distributed lock, `redemption-lock-wrap`:**
- **GHSA-mgh8-h4xc-pfmj** (getsentry/sentry, fixed 25.5.0 @ `df0af00`): unlocked `_validate()` /
  `_create_token()` / `_delete_grant()` sequence → the same three calls wrapped in
  `lock.acquire()` keyed on the grant id. Reachable via the Sentry-app OAuth token-exchange path.
  **CONTESTED** (illustrative): the lock key primitive is defined in a different file in the same
  commit, and the actual OAuth-token-endpoint fix path is locked separately.

## Do not overclaim
- If the class's added-guard shape is already present in the target's source for the reached
  redemption path — a single atomic claim/consume primitive, or a lock/transaction spanning the
  validate + issue + delete sequence (see the anchors above) — this path is patched; do not claim
  strong activation without a further, specific reason. Presence of the guard is a strong held
  signal, not a soundness proof.
