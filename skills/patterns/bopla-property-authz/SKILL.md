---
id: pattern.bopla-property-authz
name: Broken Object Property-Level Authorization
description: >
  An API authorizes access to the object but not to sensitive properties on that object, causing
  overfetch on read or mass-assignment/write access to guarded fields. The proof is property-level:
  a gated property canary is exposed or an unauthorized property change takes effect.
type: pattern
owasp: "API3:2023 Broken Object Property Level Authorization"
atlas: "—"
routes_to: ["stub:vulns/bopla-property-authz"]

activation:
  strong:
    - "a response returns whole objects or nested objects containing properties the caller should not see"
    - "a write/update endpoint accepts whole-object bodies, sparse patches, or unknown fields that map to sensitive server properties"
    - "different roles receive the same object shape even though one role should have fewer properties"
    - "an object lookup is keyed only by a client-supplied id/state/collection param with no comparison to the caller's identity, org, or ownership before the full record (and its properties) is returned or mutated (diff-derived: the id-only `get_record('id' => $rssid)` in CVE-2025-3636, the `state`-as-victim-UUID lookup in CVE-2025-69207 — see the anchors section)"
  weak:
    - "serializers or ORMs expose model fields by default"
    - "client code hides fields in the UI while the API still returns them"
    - "request bodies include admin, role, owner, billing, status, internal, or metadata fields"
  negative:
    - "the serializer filters guarded fields server-side by role before response"
    - "the write path allowlists mutable properties and ignores/rejects guarded fields"
    - "an echoed guarded field is not persisted or used by authorization/business logic"
    - "the object lookup is scoped by owner/org/capability (or the client key is swapped for the authenticated identity) before any property is read or written → likely held (diff-derived: the owner-scoped `get_record_select('id = :id AND (userid = :userid OR shared = 1)')` in CVE-2025-3636, the `queryResult.OrgID != c.OrgID` check in CVE-2024-1313, the `request.user.object` swap in CVE-2025-69207)"
---

# Broken object property-level authorization

> **Activation vs adjudication.** Object access may be legitimate while property access is not.
> Confirmation requires a property canary: either a gated property is exposed on read, or an
> unauthorized write has an effective state/authorization impact. Echoes do not confirm.

**Idea.** BOLA asks whether the caller may access the object. BOPLA asks whether the caller may see or
change each property on an object they may otherwise access.

## Suggested probes (benign canaries only)
- **Read overfetch:** plant a distinctive property canary in a field the lower-privilege principal
  should not see. The response must expose that canary from the server-side property.
- **Write mass assignment:** submit a guarded field on an otherwise allowed update. Confirmation
  requires the unauthorized value to persist or affect a guarded decision, not merely echo.
- **Role differential:** compare low-privilege and privileged principals on the same synthetic object.

## Required oracle controls
- **Positive control:** a serializer/write guard strips, denies, or coerces the guarded property on a
  patched path or privileged-control transcript.
- **Negative control:** allowed fields still work, so a denial is not just endpoint failure.
- **Property canary:** the exposed property or effective unauthorized state must be distinctive and
  synthetic.

## Counterexamples
- The API echoes an unknown property in the immediate response but does not persist or use it.
- The caller is legitimately entitled to the property through role, sharing, or ownership.
- A UI-only hiding difference with no API exposure.

## Real disclosed anchor(s) for this class (fix-diff-derived)
Priors/taxonomy from real disclosed GHSA fix commits — the vulnerable pre-patch shape and the guard
the fix added. Verbatim hunks + primary sources in `skills/oracles/references/ghsa-fix-diff-corpus.md`
(IDOR / BOLA bucket, which explicitly names this card as one of its grounds); consult via the
`ghsa-fix-diff` oracle. **These are all *fixed* bugs, not live-bug claims:** a target matching a
removed-line shape is a lead to run through the funnel above, never a confirmation. These four IN
anchors are object-level (BOLA) fixes rather than property-level ones, but the guard shape is the
direct analog for BOPLA — whenever the unguarded lookup returns or mutates a whole record, the
record's properties are exposed or overwritten right along with the object, so the two failures
share one root cause: no ownership/capability check before the record's fields are touched. The
bucket splits by whether the fix scopes the lookup itself, or swaps the client-trusted key for the
server-side identity.

**Per-object-authz (scope the lookup by owner/org/capability before fields are read or written):**
- **CVE-2024-1313** (Grafana, GHSA-67rv-qpw2-6qrr, fixed 9.5.18/10.0.13/10.1.9/10.2.6/10.3.5 @
  `f4c5a60`): snapshot DELETE looked up by key only, no OrgID compare → added
  `queryResult.OrgID != c.OrgID` check. Integrity-only (delete) on this endpoint, but the identical
  missing-scope shape on a sibling read endpoint would expose the object's guarded properties
  wholesale. `per-object-authz`.
- **CVE-2025-3636** (Moodle, GHSA-chmf-m33p-ph8m, fixed 4.1.19/4.3.13/4.4.9/4.5.5 @ `0bd9720`):
  RSS-feed record fetched by id-only `get_record`, no owner check → owner-scoped
  `get_record_select('id = :id AND (userid = :userid OR shared = 1)')` + capability gate. A
  guessable id exposed another user's/course's private feed record and every property on it.
  `per-object-authz`.
- **CVE-2026-29071** (open-webui, GHSA-w9f8-gxf9-rhvw, fixed 0.8.6 @ `9c9a18d`) — **CONTESTED**
  (illustrative): client-supplied `collection_name` queried the vector store with no ownership
  check → `_validate_collection_access()` gate matching `user-memory-{id}` / file-ACL before the
  query runs. Property-relevant in the purest sense — the exposed collection *is* the guarded
  property (another user's memory/file content), not just an object id. `per-object-authz`.

**Exact-match-swap (replace the trusted client key with the authenticated identity):**
- **CVE-2025-69207** (khoj, GHSA-6whj-7qmg-86qj, fixed 2.0.0-beta.23 @ `1b7ccd1`): unauthenticated
  OAuth `state` param trusted as the target user's UUID key, used to write/delete that user's
  NotionConfig → swapped to `request.user.object` plus a `state == user.uuid` check. Overwrites
  another user's integration-config properties pre-auth. `exact-match-swap`.
- **CVE-2026-33702** (chamilo, GHSA-3rv7-9fhx-j654, fixed 1.11.38/2.0.0-RC.3 @ `6331d05`):
  Learning-Path progress save trusted `$_REQUEST['uid']` as the target object owner → swapped to
  `api_get_user_id()`. Authenticated write; overwrites another user's progress properties
  (score/status/completion/time). `exact-match-swap`.
- **GHSA-cj8f-h888-m57m** (LinkAce, fixed 2.5.6 @ `2c121b4`) — **CONTESTED** (illustrative,
  entangled across 9 files): Policy `update()` checked visibility, not ownership, and API
  controllers skipped `authorize()` entirely → ownership check (`$link->user->is($user)`) plus an
  explicit `authorize('update', ...)` call. Authenticated write; overwrites another user's object
  and every property on it via a scoped API token. `exact-match-swap`.

## Do not overclaim
- Whole-object JSON is activation, not confirmation.
- Echoed request JSON is not mass assignment.
- Name the exact property-level boundary crossed, or keep the result `needs_review`.
- If the target's reached sink already scopes the object lookup by owner/org/capability, or swaps
  a client-supplied key for the authenticated identity, before any property is read or written (see
  the anchors above) — this path is patched; do not claim strong activation without a further,
  specific reason (a sibling unguarded sink, a role that legitimately still overfetches). Presence
  of the guard is a strong held signal, not a soundness proof.
