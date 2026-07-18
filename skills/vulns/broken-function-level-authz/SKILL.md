---
id: bfla.broken-function-level-authz
name: Broken Function-Level Authorization
description: >
  Prove a caller can invoke an operation/route/mutation their role should not reach at all, because
  authorization is enforced only in the UI, only by HTTP method, or not re-checked server-side per
  operation. BOLA's sibling: BOLA is "whose OBJECT can I reach"; this is "which OPERATION can I invoke
  at all." Confirmed only when a lower-privilege controlled principal completes a higher-privilege
  action with an inert/reversible canary effect, and the matched negative control (same role, intended
  path) declines.
type: vuln
owasp: "A01 Broken Access Control / API5:2023 Broken Function Level Authorization"
atlas: "—"
patterns: [pattern.ui-only-policy-enforcement, pattern.legacy-route-differential, pattern.unsafe-default-authz-helper, pattern.delegated-capability-attenuation]

activation:
  strong:
    - "a privileged operation (admin/owner/staff-with-permission) is exposed as a route/mutation a lower role can also send"
    - "the UI hides an action by role but the underlying API accepts it from any authenticated caller"
    - "an operation's authorization depends on a client-supplied role/scope/permission field, or on the HTTP method/verb alone"
    - "staff or app scopes gate the UI, but a raw API call under a lower scope still performs the action"
    - "sibling / versioned / legacy routes for the same operation where one checks the role and one may not"
    - "a privileged controller action / route performs its mutation with no per-function permission check at all before the sink — only session/basic authentication, not a role- or permission-specific gate (diff-derived: the missing showPermissionsScreen()/canAssignUserGroups() check in CVE-2026-41128, the route registered with no reqRepoReader(unit.TypeCode) in CVE-2026-27783, the absent checkPermission() in CVE-2026-23496)"
    - "an alternate write path (bulk/sync/import API, DAL writer) reaches a privileged field with no equivalent check to the one the regular controller enforces (diff-derived: the Sync-API `admin` BoolField with no WriteProtected binding in CVE-2026-48008)"
  weak:
    - "role / permission / scope names appear in responses or JS (routes the surface; not itself a bug)"
    - "an operation returns 200 for a low role but its EFFECT on state is unverified"
  negative:
    - "the operation is re-authorized server-side against the authenticated principal's real role/scope → likely held"
    - "a low role receives 403 AND a controlled state check shows the action did not occur"
    - "the action only affects the caller's own permitted scope"
    - "every function-mutating entrypoint (including bulk/sync/import paths) is gated by an explicit per-function permission/role check inserted immediately before the sink, not merely by authentication → likely held (diff-derived: the showPermissionsScreen()+canAssignUserGroups() gate, the reqRepoReader(unit.TypeCode) route guard, the checkPermission() call, the WriteProtected(SYSTEM_SCOPE) field binding — see the anchors below)"

safe_signal:
  proxy: >
    a LOWER-privilege principal YOU control completes a HIGHER-privilege operation, proven by an inert,
    reversible canary effect on a synthetic object (a harmless test flag toggled, a disposable draft
    created then deleted), where the same role is DENIED by the matched negative control. The signal is
    the completed privileged action's inert effect, never a real business-impacting change.
  never: >
    no destructive, persistent, or business-impacting operations (no real refunds, payouts, price
    changes, staff-permission grants on real data, deletions of real objects); use only inert/reversible
    effects on synthetic objects in OWNED test accounts; privilege-escalation artifacts require scope.md
    authorization AND an operator confirm before any artifact.

impact_escalation:
  enabled_by: scope.md#impact_demo_authorized
  requires: human_confirm
  containment: "inert/reversible action on a synthetic object; logged in engagement cleanup.md with a revert"

oracle: [signal-oracle, adjudication-oracle, ghsa-fix-diff]
severity_rubric: { cross_tenant_admin_action: critical, tenant_admin_takeover: critical, staff_permission_bypass: high, low_to_higher_role_same_tenant: high, method_or_ui_bypass_only: medium, refused: info }

procedure:
  - "MAP THE OPERATION SET: enumerate privileged operations (from JS, API specs, the GraphQL schema, higher-role request captures). For each, note who SHOULD be able to invoke it."
  - "ESTABLISH ROLES: hold at least two controlled principals of DIFFERENT privilege in an owned tenant (e.g. owner + limited staff), plus a second tenant for cross-tenant rungs."
  - "BASELINE (positive control): perform the operation as the AUTHORIZED role → it works. This proves the operation and your effect-check are real."
  - "NEGATIVE CONTROL (must decline): perform it as the LOWER role via the UI-intended path → expect 403 AND no effect. Record kind=negative_control."
  - "ATTACK: replay the operation as the LOWER role against the RAW API/route/mutation (strip the UI, forge the method, drop or downgrade the scope). A confirm requires the inert canary EFFECT to occur, not merely a 200."
  - "DIFFERENTIAL: if a sibling route re-checks the role, send the same call there — it SHOULD 403 (pattern.legacy-route-differential)."
  - "RULE OUT legitimate entitlement (the low role is actually permitted) and UI-only-vs-real (a 200 with no state change is method_or_ui_bypass_only at most). REPLAY in a fresh session."
  - "ESCALATE within scope: low→higher role same tenant → staff-permission bypass → tenant-admin action → cross-tenant admin action. STOP at the scope.md ceiling; privilege artifacts need operator confirm."
  - "A 403 with no effect is the secure outcome — not a finding. A refusal routes to the next operation/rung, never a terminal 'secure'."

emits: [attempt, finding]
---

## What "confirmed" looks like here
A lower-privilege controlled principal COMPLETES a privileged operation, proven by the inert canary
EFFECT (a synthetic flag toggled, a disposable object created or mutated), where the matched negative
control (same role via the intended path) DECLINED and any re-checking sibling returned 403, reproduced
once in a fresh session with contamination ruled out. A bare 200/204 with no state change is at most a
UI/method bypass (medium), not a confirmed function-level authz break. Name the operation and the two
roles in one sentence, or it isn't confirmed.

## BFLA vs BOLA (siblings — do not conflate)
- **BOLA** (`bola.broken-object-level-authz`): you may call the operation, but you reach the WRONG
  OBJECT (someone else's id). The bug is per-object.
- **BFLA** (this card): you should not be able to call the OPERATION AT ALL for your role. The bug is
  per-function. A single request can exhibit both; test and report the axis you actually proved.

## Controls are the whole proof (see adjudication-oracle)
- **Positive / baseline:** the authorized role performs it — your effect-check is valid.
- **Negative:** the lower role via the intended path is denied AND no effect occurs.
- **Differential:** a re-checking sibling route 403s the same lower-role call.
Without the inert EFFECT crossing, a 200 is `needs_review`, never `confirmed`.

## Real disclosed anchor(s) for this class (fix-diff-derived)
Priors/taxonomy from real disclosed GHSA fix commits — the vulnerable pre-patch shape and the guard
the fix added. Verbatim hunks + primary sources in `skills/oracles/references/ghsa-fix-diff-corpus.md`
(BFLA bucket); consult via the `ghsa-fix-diff` oracle. **These are all *fixed* bugs, not live-bug
claims:** a target matching a vulnerable pre-patch shape is a lead to run through the funnel above,
never a confirmation. The dominant shape is a per-function permission check missing entirely; a
minority of anchors instead show an existing check on the wrong path or object.

**Per-function-authz (dominant — no check at all before the sink, only authentication):**
- **CVE-2026-41128** (GHSA-jq2f-59pj-p3m3, craftcms/cms, fixed 5.9.15 / 4.16.19 @ `b135384`):
  `actionSavePermissions()` let any authenticated CP user with only `viewUsers` strip a target user's
  groups — no per-action authz check at all → `showPermissionsScreen()`/`ForbiddenHttpException` gate
  added on the controller action plus a `canAssignUserGroups()` guard on the mutation helper. `per-function-authz`.
- **CVE-2026-27783** (GHSA-3fwp-p5rj-2pxf, go-gitea/gitea, fixed 1.26.2 @ `171df0c`): issue-template
  API routes registered with only `context.ReferencesGitRepo()`, unlike sibling routes that required
  `reqRepoReader(unit.TypeCode)` → the same reqRepoReader check added to all three routes. A
  read-repository-scoped token reached Code-unit-restricted content. `per-function-authz`.
- **CVE-2026-23496** (GHSA-4wg4-p27p-5q2r, pimcore/web2print-tools, fixed 5.2.2 / 6.1.1 @ `7714452`):
  `favoriteOutputDefinitionsTableProxyAction()` had zero server-side permission check → `$this->checkPermission('web2print_web2print_favourite_output_channels')`
  inserted at entry. Any authenticated backend user, not just permission holders, could list/mutate
  the configs. `per-function-authz`.
- **CVE-2026-54076** (GHSA-vg6x-6pg9-6qwg, ArcadeData/arcadedb, fixed 26.6.1 @ `2ee76fe`) — illustrative
  multi-site insertion, not a single contiguous hunk: a prior fix had only guarded `createProperty()`;
  every sibling schema-mutator (`dropProperty`/`rename`/`setAliases`/`addBucket`/…) stayed unchecked →
  a shared `checkForSchemaMutation()` helper inserted at the top of all of them. A read-only API token
  could still DDL the schema through the unguarded siblings. `per-function-authz`.

**Existing check on the wrong path/object (minority):**
- **CVE-2022-1397** (easyappointments, fixed 1.5.0 @ `63dbb51`): the admin-API Basic-Auth gate
  (`Api::auth()`) only verified valid credentials via `check_login()`, no role check → a
  `role_slug === DB_SLUG_ADMIN` exact-match added. Any valid non-admin account's credentials granted
  full admin-API access. `exact-match-swap`.
- **CVE-2026-48008** (GHSA-gv8p-48fr-4fxg, shopware/shopware, fixed 6.6.10.18 / 6.7.10.1 @ `1e047f6`):
  the regular integration-create controller blocked `admin=true` without `isAdmin()`, but the Sync
  API's DAL `EntityWriter` path had no equivalent check on the same field → the `admin` `BoolField`
  wrapped in `WriteProtected(Context::SYSTEM_SCOPE)`. A caller with only `integration:create` could
  self-escalate via the alternate write path. `param-binding`.
- **CVE-2026-42562** (GHSA-pvfv-wvpm-q6f6, plainpad, fixed 1.1.1 @ `9216a87`): `UsersController::update()`
  decided who may edit by reading the ALREADY-authorized target row's `admin` flag, then unconditionally
  wrote the client-supplied `admin` value → the decision moved to `Auth::user()`/`$authUser`, and the
  `admin`-field write is gated on `$authUser->admin`. A self-profile edit could flip the caller's own
  admin flag. `per-object-authz`.

## Not this card
- Reaching another principal's object with an operation you may legitimately call → BOLA.
- A UI that merely hides a button while the API correctly 403s → held control (a `negative` signal).
- OAuth/app scope that should attenuate a delegated capability → route `pattern.delegated-capability-attenuation`
  first; it becomes this card only if the under-scoped principal actually performs the action.

## Do not overclaim
- "The API returned 200 for the low role" proves nothing until the privileged EFFECT is observed on a
  controlled object.
- "The UI is hidden but the endpoint exists" is a lead, not a finding — the endpoint may still 403.
- Distinguish method/verb bypass and UI-only bypass (medium) from a real server-side authz gap (high+).
- If the class's added-guard shape is already present in the target's source for the reached
  sink — an explicit per-function permission check inserted before the mutation, a role exact-match
  on the auth gate, or a write-protected/caller-authorized field binding (see the anchors above) —
  this path is patched; do not claim strong activation without a further, specific reason (an
  unguarded sibling route, an alternate write path). Presence of the guard is a strong held signal,
  not a soundness proof.
