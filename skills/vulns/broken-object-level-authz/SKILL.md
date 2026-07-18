---
id: bola.broken-object-level-authz
name: Broken Object-Level Authorization
description: >
  Prove an app serves one principal's object to another by trusting a client-supplied identifier
  (object / owner / tenant id) without re-resolving authorization from the authenticated caller.
  The BOLA/IDOR objective — confirmed only with a benign planted canary or inert canary effect that
  crossed a boundary.
type: vuln
owasp: "A01 Broken Access Control (BOLA) / API1:2023"
atlas: "—"
patterns: [pattern.client-supplied-selector-authz, pattern.legacy-route-differential, pattern.ui-only-policy-enforcement]

activation:
  strong:
    - "a request carries an object/owner/tenant/account id the caller could change (path, query, header, or body)"
    - "a mutating request carries a client-supplied selector and can produce an inert, reversible effect on a resource owned by another controlled principal"
    - "versioned or sibling routes for the same resource where one validates the id and one may not"
    - "ids of other principals are reachable (share links, exports, sequential/guessable ids, prior responses)"
    - "an object is fetched by id/key alone with no owner/org comparison in the query itself, or a client-supplied field (state param, uid, id) is used directly as the lookup key/identity instead of the authenticated session's own id (diff-derived: the id-only `get_record(['id' => $rssid])` in CVE-2025-3636, the missing `OrgID != c.OrgID` check in CVE-2024-1313, the `aget_user_by_uuid(state)` swap in CVE-2025-69207, the raw `$_REQUEST['uid']` passthrough in CVE-2026-33702 — see the anchors section)"
  weak:
    - "generic id fields (id, ref, key) that resolve a resource without an obvious ownership check"
    - "integer/sequential ids are enumerable; this helps route the card but does not itself prove access"
  negative:
    - "ownership is resolved from the authenticated session, not from any request field → likely held"
    - "the id only selects among the caller's own objects"
    - "changing the id yields only a generic success/200 with no victim canary read and no inert effect on the victim canary object"
    - "the object lookup is scoped by owner/OrgID in the query itself, or any client-supplied key is swapped for the authenticated session identity before use → likely held (diff-derived: the owner-scoped `get_record_select` in CVE-2025-3636, the `OrgID != c.OrgID` check in CVE-2024-1313, the `request.user.object` swap in CVE-2025-69207, the `api_get_user_id()` swap in CVE-2026-33702)"

safe_signal:
  proxy: >
    a benign, distinctive canary that YOU planted in a resource owned by ANOTHER principal you control
    is returned to a caller who should not have access, OR an inert/reversible effect YOU planted for
    testing lands on that other controlled principal's canary object — proving the object/owner/tenant
    boundary was crossed. The signal is the planted canary or inert effect, never real third-party data.
  never: >
    do not read, store, or exfiltrate real third-party data; use only planted canaries in OWNED test
    accounts; do not perform destructive, persistent, or business-impacting mutations; cross-tenant reach
    and any non-inert mutation require scope.md authorization AND an operator confirm before any artifact.

impact_escalation:
  enabled_by: scope.md#impact_demo_authorized
  requires: human_confirm
  containment: "synthetic canary only; logged in engagement cleanup.md with a revert"

oracle: [signal-oracle, adjudication-oracle, ghsa-fix-diff]
severity_rubric: { cross_tenant_read: critical, cross_user_same_tenant: high, same_user_other_object: medium, refused: info }

procedure:
  - "MAP THE SELECTOR: identify every request field that names an object/owner/tenant. For each, ask who validates it server-side (route the shape via pattern.client-supplied-selector-authz)."
  - "PLANT A CANARY: in a resource owned by a SECOND principal you control, place a distinctive benign marker. Never use a real third party."
  - "FOR MUTATIONS: use only an inert, reversible canary effect (for example a harmless test flag on a synthetic object). A bare 200/204 is only `needs_review` until the foreign canary object shows the effect."
  - "NEGATIVE CONTROLS (must decline): same request with the selector (a) absent and (b) = self. Neither may return the other principal's object. Record kind=negative_control."
  - "DIFFERENTIAL POSITIVE CONTROL: if a validating sibling route exists, send the same id there — it SHOULD 403. That proves the guard can exist and isolates the unguarded route (pattern.legacy-route-differential)."
  - "ATTACK: set the selector to the second principal's id on the suspect route. A confirm requires the response to carry the PLANTED canary, not your own data and not a generic 404."
  - "ESCALATE THE BOUNDARY within scope: same-user-other-object → same-tenant-other-user → cross-tenant. STOP at the scope.md ceiling; cross-tenant artifacts need operator confirm."
  - "RULE OUT legitimate entitlement (admin/shared) and contamination; REPLAY in a fresh session."
  - "A 404 or a declined control is the secure outcome — not a finding. A refusal is an input to the next boundary rung, never a terminal 'secure'."

emits: [attempt, finding]
---

## What "confirmed" looks like here
A caller receives an object they do not own, proven by the **planted canary** crossing a named
boundary (object / owner / tenant), or an inert canary mutation lands on a foreign controlled object,
where the **matched negative control declined** and a validating sibling (if any) returned 403,
reproduced once in a fresh session with contamination ruled out. A 200 full of the caller's *own* data
or a mutation 200 with no foreign canary effect is not BOLA. A 404 on the cross-principal id is the
secure outcome.

## Boundaries (escalate in order; each rung gated on the prior + scope.md)
1. **same user, other object** — your own account, a resource id you shouldn't reach → medium.
2. **same tenant, other user** — a second account in your company → high.
3. **cross-tenant** — a principal in another company → critical; **operator confirm before any artifact**.

## Controls are the whole proof (see adjudication-oracle)
- **Negative:** selector absent / = self must NOT return the other object.
- **Positive / differential:** the validating sibling route returns 403 for the same id.
- **Canary:** the returned data carries the *victim's* planted marker, not yours.
Without all three, it's `needs_review`, never `confirmed`.

## Real disclosed anchor(s) for this class (fix-diff-derived)
Priors/taxonomy from real disclosed GHSA fix commits — the vulnerable pre-patch shape and the guard
the fix added. Verbatim hunks + primary sources in `skills/oracles/references/ghsa-fix-diff-corpus.md`
(IDOR / BOLA bucket); consult via the `ghsa-fix-diff` oracle. **These are all *fixed* bugs, not
live-bug claims:** a target matching a removed-line shape is a lead to run through the funnel above,
never a confirmation. The bucket splits by guard shape.

**Owner/org-scoped lookup was missing (the fix adds the scope to the query), `per-object-authz`:**
- **CVE-2024-1313** (grafana, GHSA-67rv-qpw2-6qrr, fixed 9.5.18 / 10.0.13 / 10.1.9 / 10.2.6 / 10.3.5
  @ `f4c5a60`): `DELETE /api/snapshots/:key` resolved a snapshot by key alone, no OrgID comparison →
  added `queryResult.OrgID != c.OrgID` check. Any authenticated user, no org membership required.
- **CVE-2025-3636** (moodle, GHSA-chmf-m33p-ph8m, fixed 4.1.19 / 4.3.13 / 4.4.9 / 4.5.5 @ `0bd9720`):
  RSS feed fetched by id-only `get_record`, no ownership/capability check → owner-scoped
  `get_record_select` (`id AND userid`, or `userid OR shared` for the manageanyfeeds capability).
  Any logged-in user, guessable `rssid`.
- **CVE-2026-29071** (open-webui, GHSA-w9f8-gxf9-rhvw, fixed 0.8.6 @ `9c9a18d`) — **CONTESTED**
  (illustrative): retrieval query endpoints trusted a client-supplied `collection_name` with no
  ownership check → `_validate_collection_access()` gate on `user-memory-*`/`file-*` namespaces.
  Authenticated cross-user memory/file read.

**Client-supplied key was trusted as the identity itself (the fix swaps in the session identity),
`exact-match-swap`:**
- **CVE-2025-69207** (khoj, GHSA-6whj-7qmg-86qj, fixed 2.0.0-beta.23 @ `1b7ccd1`): Notion OAuth
  callback used the attacker-controlled `state` query param as the target user's UUID via
  `aget_user_by_uuid(state)` → swapped for `request.user.object` (session identity) plus a
  `state == user.uuid` check. Callback reachable pre-session-bind.
- **CVE-2026-33702** (chamilo, GHSA-3rv7-9fhx-j654, fixed 1.11.38 / 2.0.0-RC.3 @ `6331d05`):
  Learning-Path progress-save read the target `uid` straight from `$_REQUEST` → swapped for
  `api_get_user_id()`. Authenticated write; any enrolled user could overwrite another user's LP
  progress.
- **GHSA-cj8f-h888-m57m** (LinkAce, fixed 2.5.6 @ `2c121b4`) — **CONTESTED** (illustrative):
  Link/List/Tag/Note policies' `update()` ability checked visibility, never ownership, and the API
  controllers never called `authorize()` at all → ownership check (`$link->user->is($user)`) plus
  `authorize('update', ...)` calls added to each controller. Authenticated cross-user overwrite.

## Not this card
- A selector that only picks among the caller's own objects → no cross-principal reach.
- Function/endpoint-level access (you can call an admin route at all) is **BOLA's sibling, not this
  card** — that's broken *function*-level authz; note it, route it, don't conflate it here.

## Do not overclaim
- "It returned 200" proves nothing until the canary shows it returned **someone else's** object.
- "The mutation returned 200/204" proves nothing until the foreign controlled canary object shows the
  inert effect.
- Name the exact boundary crossed in one sentence, or it isn't confirmed.
- If the class's added-guard shape is already present in the target's source for the reached sink —
  the object lookup is scoped by owner/org (`per-object-authz`) or the client-supplied key has been
  swapped for the authenticated session identity (`exact-match-swap`, see the anchors above) — this
  path is patched; do not claim strong activation without a further, specific reason (an unguarded
  sibling route, a reachable pre-guard path). Presence of the guard is a strong held signal, not a
  soundness proof.
