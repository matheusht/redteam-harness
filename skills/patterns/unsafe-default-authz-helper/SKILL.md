---
id: pattern.unsafe-default-authz-helper
name: Shared Authz Helper With Opt-In Binding (Unsafe Default)
description: >
  A shared authorization helper checks the caller's ROLE/identity but takes the resource/tenant binding
  as an OPTIONAL argument (or doesn't take it at all). A correct call and a vulnerable call differ only
  by an argument most call sites forget — so the failure is systemic by omission, and the same gap
  repeats across the whole route family that uses the helper.
type: pattern
owasp: "A01 Broken Access Control / API1:2023 (BOLA) / API5:2023 (BFLA)"
also: "the ROOT-CAUSE shape behind many client-supplied-selector findings — it explains why they are plural, not singular"
atlas: "—"
routes_to: ["vulns/broken-object-level-authz", pattern.client-supplied-selector-authz, pattern.legacy-route-differential]

activation:
  strong:
    - "a shared guard/decorator is called with the PRINCIPAL but not the resource/tenant selector — e.g. validateX(request.user) on a route whose path/body carries the object id it should be bound to"
    - "the guard's signature takes the binding as OPTIONAL (expectedTenantId?, ownerId?, {scope?}) — an opt-in safety arg is an unsafe default; presence of the optional param is the tell on sight"
    - "the SAME helper is called WITH the binding on one route and WITHOUT it on a sibling for the same resource (co-activate pattern.legacy-route-differential) — the bound call is your positive control"
    - "a route/action in a family is registered without the guard its siblings carry — e.g. the `/issue_templates` routes shipped with only `context.ReferencesGitRepo()` while sibling `/languages`, `/licenses` also required `reqRepoReader(unit.TypeCode)` (diff-derived: CVE-2026-27783, gitea) — the fix is adding the SAME guard call the sibling already had, not a new mechanism"
    - "a privileged action has no resource/permission-binding check reachable at all — e.g. `favoriteOutputDefinitionsTableProxyAction()` had zero authorization call before the fix added `checkPermission(...)` (diff-derived: CVE-2026-23496, pimcore), or a field-level write reached the DAL with no controller-level admin gate a sibling endpoint enforced (diff-derived: CVE-2026-48008, shopware)"
  weak:
    - "role-only middleware (isAdmin / hasRole) applied to a route that also accepts a cross-principal selector — role gates WHAT you are, not WHOSE data"
    - "a guard that resolves the caller's own tenant/company but never compares it to the path/body id"
  negative:
    - "the helper makes binding MANDATORY (no role-only path) or the {id}-segment check is centralized in middleware so a route cannot omit it → defense holds, record as held"
    - "every call site passes the binding (sweep shows no omissions) → held; the helper is merely verbose, not unsafe"
    - "every sibling route/method in the family carries the identical guard call, none omitted on a sweep (e.g. `reqRepoReader(unit.TypeCode)` present on every route, or the extracted `checkForSchemaMutation()` called at the top of every schema-mutator) → likely held (diff-derived: the uniform post-patch guard insertion across siblings in CVE-2026-27783, CVE-2026-54076)"
---

# Shared authz helper with opt-in binding (unsafe default)

> **Why this is its own card.** `client-supplied-selector-authz` names the *vuln shape* (a selector is
> trusted). This card names the *root cause and the detection method*: when the guard that should bind the
> selector makes the bind **optional**, the bug is not one route — it is every route that forgot the arg.
> Find the helper, enumerate its call sites, and you predict the whole class from source before touching
> the target.

**Idea.** Authorization has two questions: *what are you* (role) and *whose data is this* (binding). A
helper that answers only the first, while offering the second as an optional parameter, will be called
correctly sometimes and incorrectly most of the time — because the safe path requires remembering an extra
argument. The default is unsafe, so omission is the norm.

## Detection (gray-box first — this is the card's edge)
- **Grep the guard, not the routes.** Find the shared authorizer (e.g. `validateCompanyAdmin`,
  `requireMember`, an `@Authz` decorator). Read its signature: does it take the resource/tenant id, and is
  that parameter **optional**?
- **Classify every call site** by whether it passes the binding. The ones that don't are your candidate
  list. A sibling that *does* pass it is the positive control proving the bind belongs there.
- **Confirm the data layer scopes by the path/body id**, not by the principal — otherwise the missing bind
  is inert.
- Then go live and prove the candidates with the controls below.

## Suggested probes (you control both accounts; benign canary only)
- Pick a route that omits the binding; send it with the selector pointed at another principal you control.
- A/B against a sibling that *includes* the binding — same actor, same victim id: the bound route must
  deny, the unbound route must allow. That contrast is the finding.
- Escalate the boundary (same-account → same-tenant-other-user → cross-tenant) up to the scope ceiling.

## Required oracle controls (default-skeptical)
- **Negative control MUST decline:** a sibling route (or the same route with binding enforced) must return
  403/empty for the same cross-principal id. No declined control ⇒ no bypass.
- **Canary, not vibes:** the returned data must carry the victim's distinctive marker, not your own.
- **Rule out entitlement:** confirm the caller is genuinely not authorized for that tenant/object.
- **Don't stop at one route:** the value of this pattern is the *class*; report the swept call-site list
  (confirmed live + same-root-cause-unfired), but never claim unfired routes as confirmed.
- **Replay** in a fresh session; operator-confirm before any cross-tenant write artifact.

## Counterexamples (look like it, aren't)
- The helper makes binding mandatory and a route still leaks → the bug is elsewhere (data layer, a second
  code path), not this pattern.
- A sweep shows every call site passes the binding → the optional arg is ugly but harmless; record held.
- The "missing" binding is enforced one layer up (gateway/middleware on the `{id}` segment) → held.

## Real disclosed anchor(s) for this class (fix-diff-derived)
Priors from real disclosed GHSA fix commits — the vulnerable pre-patch shape and the guard the fix
added. Verbatim hunks + primary sources in `skills/oracles/references/ghsa-fix-diff-corpus.md` (BFLA
bucket). **These are all *fixed* bugs, not live-bug claims:** a target matching a removed-line shape
is a lead to run through the funnel above, never a confirmation. The bucket splits between call-site
omission within a route family (this card's exact shape) and a guard missing from the action entirely.

**Sibling-route call-site omission (the same guard exists on siblings but was skipped here — the card's exact shape), `per-function-authz`:**
- **CVE-2026-27783** (go-gitea/gitea, GHSA-3fwp-p5rj-2pxf, fixed 1.26.2 @ `171df0c`): `/issue_templates`,
  `/issue_config`, `/issue_config/validate` registered with only `context.ReferencesGitRepo()`, while
  sibling routes `/languages`, `/licenses` also carried `reqRepoReader(unit.TypeCode)` → fix adds the
  same `reqRepoReader(unit.TypeCode)` call to the omitted routes. Any token scoped to read-repository
  (no Code-unit access) could read templates/config on repos with the Code unit restricted.
- **CVE-2026-54076** (ArcadeData/arcadedb, GHSA-vg6x-6pg9-6qwg, fixed 26.6.1 @ `2ee76fe`): an earlier
  fix added an `UPDATE_SCHEMA` permission check only to `createProperty()`; every sibling schema-mutator
  (`dropProperty`, `rename`, `setAliases`, `addSuperType`, `addBucket`/`removeBucket`, property setters)
  stayed unchecked → fix extracts `checkForSchemaMutation()` and calls it at the top of every sibling
  method. A read-only API token could still DROP/ALTER schema through the unfired siblings.

**Guard absent from the action entirely (no sibling comparison — the resource/permission binding was never checked on this path), various `guard_type`:**
- **CVE-2026-41128** (craftcms/cms, GHSA-jq2f-59pj-p3m3, fixed 5.9.15 @ `b135384`), `per-function-authz`:
  `actionSavePermissions()` let any CP user holding only `viewUsers` strip a target user's groups via an
  empty `groups` body param — no controller-level gate, and the per-group check validated additions
  only, never removals → fix adds a `showPermissionsScreen()` controller gate plus a
  `canAssignUserGroups()` guard on the mutation helper.
- **CVE-2026-23496** (pimcore/web2print-tools, GHSA-4wg4-p27p-5q2r, fixed 5.2.2/6.1.1 @ `7714452`),
  `per-function-authz`: `favoriteOutputDefinitionsTableProxyAction()` had zero server-side permission
  check → fix adds `$this->checkPermission('web2print_web2print_favourite_output_channels')`.
- **CVE-2026-48008** (shopware/shopware, GHSA-gv8p-48fr-4fxg, fixed 6.6.10.18/6.7.10.1 @ `1e047f6`),
  `param-binding`: the regular integration-create endpoint blocked setting `admin=true` without full
  admin rights, but the Sync API wrote the same entity straight through the DAL with no equivalent
  check → fix adds `WriteProtected(Context::SYSTEM_SCOPE)` to the `admin` field itself, closing the
  unguarded sibling entrypoint.
- **CVE-2026-42562** (alextselegidis/plainpad, GHSA-pvfv-wvpm-q6f6, fixed 1.1.1 @ `9216a87`),
  `per-object-authz`: the authorization decision read the (already-authorized) TARGET row's
  `$user->admin` instead of the CALLER's role, so a low-priv user editing their own profile could flip
  their own admin flag → fix moves the check to `Auth::user()`/`$authUser` and gates the admin-field
  write on `$authUser->admin`.
- **CVE-2022-1397** (easyappointments, fixed 1.5.0 @ `63dbb51`), `exact-match-swap`: the API Basic-Auth
  gate accepted ANY valid login (`check_login()` truthy) with no role check, so any authenticated
  account reached admin-management endpoints → fix adds a `role_slug !== DB_SLUG_ADMIN` exact-match
  check.

## Do not overclaim
- An optional-bind signature is a STRONG activation, not a confirmed finding — prove a live call site with
  the sibling control.
- "Many routes use the unsafe helper" is a hypothesis about blast radius; only routes with a passing live
  oracle (or an unbound write proven + reverted) are confirmed.
- If the class's added-guard shape is already present in the target's source for the reached sink — the
  same per-function-authz check firing on EVERY sibling route/method, or a mandatory resource/role binding
  at the action itself (see the anchors above) — this path is patched; do not claim strong activation
  without a further, specific reason (an unfired sibling call site, a second write path). Presence of the
  guard is a strong held signal, not a soundness proof.
