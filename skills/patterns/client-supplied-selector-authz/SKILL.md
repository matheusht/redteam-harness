---
id: pattern.client-supplied-selector-authz
name: Client-Supplied Selector Trusted For Authorization
description: >
  A request carries a client-supplied identifier that selects WHOSE data or permissions apply
  (owner / user / account / tenant / org id), and the server trusts it instead of re-resolving
  authorization from the authenticated principal. The IDOR/BOLA shape.
type: pattern
owasp: "A01 Broken Access Control (BOLA) / API1:2023"
also: "LLM06 Excessive Agency when the selector reaches an agent tool"
atlas: "—"   # web/API authz pattern; no direct ATLAS technique
routes_to: ["vulns/broken-object-level-authz", "vulns/llm06-excessive-agency"]

activation:
  strong:
    - "a request field that NAMES A SELECTOR of whose data/permissions apply is PRESENT in the path, query, header, or body (ownerId, userId, accountId, tenantId, companyId, x-user-id, org id) — presence alone is strong; you do NOT need to have already shown it differs from the principal"
    - "the same endpoint behaves differently with the selector present vs absent (present → it scopes the read to that id; absent → it falls back to the caller)"
    - "a sibling/newer version of the same endpoint DOES validate the selector (its mere existence says the team knows it needs validating — see pattern.legacy-route-differential)"
    - "a client-supplied object key (uid, state, rssid, collection_name) is passed straight into a lookup, save, or delete call with no swap to the authenticated session identity and no owner/org-scoped WHERE clause — the raw pre-patch shape (diff-derived: the unguarded `$_REQUEST['uid']` in CVE-2026-33702, the `aget_user_by_uuid(state)` lookup in CVE-2025-69207, the id-only `get_record('id' => $rssid)` in CVE-2025-3636 — see the anchors section)"
  weak:
    - "an id that looks like another principal's is visible to the client at all (URL path, query string, header value, share link, export, prior response) — a leak-vector that makes the selector reachable"
    - "integer, sequential, or low-entropy ids appear in routable selectors; enumeration is an activation signal, not a finding"
    - "the field is named generically (id, ref) but resolves a cross-principal resource"
  negative:
    - "the selector is re-resolved server-side against the authenticated principal before use (the guard is present) → defense holds, record as held"
    - "the selector only chooses among the caller's OWN resources (no cross-principal reach)"
    - "the id is public or ignored, and changing it does not alter which principal's object/effect is returned"
    - "the object lookup swaps the client-supplied key for the authenticated session identity (`api_get_user_id()`, `request.user.object`) or scopes the query/delete by owner/org (`userid =`, `OrgID != c.OrgID`) before use → likely held (diff-derived: the identity swap in CVE-2026-33702, the `OrgID` check in CVE-2024-1313, the owner-scoped `get_record_select` in CVE-2025-3636)"
---

# Client-supplied selector trusted for authorization

> **Activation vs adjudication (load-bearing).** Activation keys on the selector field being *present*
> and *functioning* as a chooser of whose data/permissions apply — that is **strong**, on sight.
> Whether it actually differs from the principal, or is safely re-resolved server-side, is the
> **adjudication** question (held vs exploited), decided later with controls — NOT a precondition for
> a strong activation. Guilty until the server is shown to re-resolve it.

**Idea.** The server lets the client say *whose* data to act on, then acts on it without proving the
caller is allowed to. The authenticated principal is the source of truth for authorization; the
moment a request field overrides *whose* permissions apply, ask who validates it.

**ID opacity is not a defense.** UUIDs, hashes, opaque slugs, and signed-looking ids reduce guessing
but do not prove authorization. Treat low-entropy or enumerable ids as a reachability boost; treat
opaque ids as still requiring server-side ownership resolution.

## Suggested probes (you control both accounts; benign canary only)
- **Point the selector at another principal you control** and send an otherwise-authorized request.
  Plant a distinctive benign canary in the victim resource first so a 200 unambiguously means the
  victim's content crossed the boundary.
- **A/B the selector**: same request with the selector (a) absent, (b) = self, (c) = another
  principal. (a)/(b) are the negative controls; (c) is the attack.
- **Escalate the boundary**: same-account → same-tenant-other-user → cross-tenant. Stop at the scope
  ceiling in `scope.md`.
- **Diff against the validating sibling** if one exists — that sibling is your positive control that
  the guard *can* exist here.

## Required oracle controls (adjudication is default-skeptical)
- **Negative control MUST decline:** the no-selector / self-selector request must NOT return the
  cross-principal resource. Without a declined control there is no bypass.
- **Canary, not vibes:** confirm the returned data carries the *victim's* planted canary, not your
  own. A 200 full of your own data is not IDOR.
- **404 ≠ allow:** a missing-object 404 on the cross-principal id is the secure outcome, not a finding.
- **Rule out legitimate entitlement:** if your account is actually authorized for that resource
  (admin, shared), it is not a bypass — prove the boundary the selector crossed.
- **Replay** in a fresh session; for cross-tenant, operator-confirm before any impact artifact.

## Real disclosed anchor(s) for this class (fix-diff-derived)
Priors/taxonomy from real disclosed GHSA fix commits — the vulnerable pre-patch shape and the guard
the fix added. Verbatim hunks + primary sources in `skills/oracles/references/ghsa-fix-diff-corpus.md`
(IDOR / BOLA bucket); consult via the `ghsa-fix-diff` oracle. **These are all *fixed* bugs, not
live-bug claims:** a target matching a removed-line shape is a lead to run through the funnel above,
never a confirmation. The class splits by guard shape: owner/org-scoped lookup vs. identity swap.

**Owner/org-scoped object lookup (`per-object-authz`):**
- **CVE-2024-1313** (grafana, GHSA-67rv-qpw2-6qrr, fixed 9.5.18/10.0.13/10.1.9/10.2.6/10.3.5 @
  `f4c5a60`): `DELETE /api/snapshots/:key` looked up a dashboard snapshot by key only → added
  `queryResult.OrgID != c.OrgID` check before delete. Authenticated cross-org destructive action.
- **CVE-2025-3636** (moodle, GHSA-chmf-m33p-ph8m, fixed 4.1.19/4.3.13/4.4.9/4.5.5 @ `0bd9720`):
  RSS-feed `viewfeed.php` fetched the feed record by `rssid` alone → owner-scoped
  `get_record_select('id = :id AND userid = :userid ...')`. Authenticated, guessable-id read.

**Client-supplied key swapped for session identity (`exact-match-swap`):**
- **CVE-2025-69207** (khoj, GHSA-6whj-7qmg-86qj, fixed 2.0.0-beta.23 @ `1b7ccd1`): Notion OAuth
  callback used the attacker-controlled `state` query param as the target user's UUID via
  `aget_user_by_uuid(state)` → swapped to `request.user.object` (session identity) plus a
  `state == user.uuid` check. Hijacks another user's Notion integration.
- **CVE-2026-33702** (chamilo, GHSA-3rv7-9fhx-j654, fixed 1.11.38/2.0.0-RC.3 @ `6331d05`):
  Learning-Path progress save read the target `uid` straight from `$_REQUEST` → swapped to
  `api_get_user_id()`. Authenticated write (overwrites another user's LP progress).
- **CVE-2026-29071** (open-webui, GHSA-w9f8-gxf9-rhvw, fixed 0.8.6 @ `9c9a18d`) — **CONTESTED**
  (illustrative): client-supplied `collection_name(s)` reached the vector store with no ownership
  check → `_validate_collection_access()` guard scoping `user-memory-*`/`file-*` names to the
  caller. `per-object-authz`.
- **GHSA-cj8f-h888-m57m** (LinkAce, fixed 2.5.6 @ `2c121b4`) — **CONTESTED** (illustrative):
  update-ability policies checked resource visibility, never ownership, and API controllers never
  called `authorize()` at all → ownership check (`$link->user->is($user)`) plus added
  `$this->authorize('update', $link)` calls. Mixes `exact-match-swap` + per-function-authz.

## Counterexamples (look like it, aren't)
- The newer route that re-validates the selector returns 403 → the guard works there; the finding (if
  any) is the *route differential*, not the selector itself.
- A selector that picks among the caller's own items (e.g. which of *my* chats) → no cross-principal
  reach, no BOLA.
- A public id, profile handle, or share token is reflected or accepted but does not change the
  cross-principal object/effect → activation may be real, confirmation is refuted.

## Do not overclaim
- "It returned 200" proves nothing until the canary shows it returned **someone else's** resource.
- Reading your own data through a differently-named field is not IDOR.
- Name the exact boundary crossed (object / user / tenant) in one sentence, or it isn't confirmed.
- If the class's added-guard shape is already present in the target's source for the reached sink —
  the client-supplied key swapped for the authenticated session identity, or an owner/org-scoped
  WHERE clause on the object lookup (see the anchors above) — this path is patched; do not claim
  strong activation without a further, specific reason. Presence of the guard is a strong held
  signal, not a soundness proof.
