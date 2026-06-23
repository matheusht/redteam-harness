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
    - "a request param or body field names an owner/user/account/tenant/org id that is NOT the session principal (e.g. ownerId, userId, accountId, tenantId, companyId in the body/query)"
    - "the same endpoint behaves differently with the selector present vs absent (present → it scopes the read to that id; absent → it falls back to the caller)"
    - "a sibling/newer version of the same endpoint DOES validate the selector (its mere existence says the team knows it needs validating — see pattern.legacy-route-differential)"
  weak:
    - "an id that looks like another principal's is visible to the client at all (URL, share link, export, prior response) — a leak-vector that makes the selector reachable"
    - "the field is named generically (id, ref) but resolves a cross-principal resource"
  negative:
    - "the selector is re-resolved server-side against the authenticated principal before use (the guard is present) → defense holds, record as held"
    - "the selector only chooses among the caller's OWN resources (no cross-principal reach)"
---

# Client-supplied selector trusted for authorization

**Idea.** The server lets the client say *whose* data to act on, then acts on it without proving the
caller is allowed to. The authenticated principal is the source of truth for authorization; the
moment a request field overrides *whose* permissions apply, ask who validates it.

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

## Counterexamples (look like it, aren't)
- The newer route that re-validates the selector returns 403 → the guard works there; the finding (if
  any) is the *route differential*, not the selector itself.
- A selector that picks among the caller's own items (e.g. which of *my* chats) → no cross-principal
  reach, no BOLA.

## Do not overclaim
- "It returned 200" proves nothing until the canary shows it returned **someone else's** resource.
- Reading your own data through a differently-named field is not IDOR.
- Name the exact boundary crossed (object / user / tenant) in one sentence, or it isn't confirmed.
