---
id: bola.broken-object-level-authz
name: Broken Object-Level Authorization
description: >
  Prove an app serves one principal's object to another by trusting a client-supplied identifier
  (object / owner / tenant id) without re-resolving authorization from the authenticated caller.
  The BOLA/IDOR objective — confirmed only with a benign planted canary that crossed a boundary.
type: vuln
owasp: "A01 Broken Access Control (BOLA) / API1:2023"
atlas: "—"
patterns: [pattern.client-supplied-selector-authz, pattern.legacy-route-differential, pattern.ui-only-policy-enforcement]

activation:
  strong:
    - "a request carries an object/owner/tenant/account id the caller could change (path, query, or body)"
    - "versioned or sibling routes for the same resource where one validates the id and one may not"
    - "ids of other principals are reachable (share links, exports, sequential/guessable ids, prior responses)"
  weak:
    - "generic id fields (id, ref, key) that resolve a resource without an obvious ownership check"
  negative:
    - "ownership is resolved from the authenticated session, not from any request field → likely held"
    - "the id only selects among the caller's own objects"

safe_signal:
  proxy: >
    a benign, distinctive canary that YOU planted in a resource owned by ANOTHER principal you control
    is returned to a caller who should not have access — proving the object/owner/tenant boundary was
    crossed. The signal is the planted canary, never real third-party data.
  never: >
    do not read, store, or exfiltrate real third-party data; use only planted canaries in OWNED test
    accounts; cross-tenant reach requires scope.md authorization AND an operator confirm before any artifact.

impact_escalation:
  enabled_by: scope.md#impact_demo_authorized
  requires: human_confirm
  containment: "synthetic canary only; logged in engagement cleanup.md with a revert"

oracle: [signal-oracle, adjudication-oracle]
severity_rubric: { cross_tenant_read: critical, cross_user_same_tenant: high, same_user_other_object: medium, refused: info }

procedure:
  - "MAP THE SELECTOR: identify every request field that names an object/owner/tenant. For each, ask who validates it server-side (route the shape via pattern.client-supplied-selector-authz)."
  - "PLANT A CANARY: in a resource owned by a SECOND principal you control, place a distinctive benign marker. Never use a real third party."
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
boundary (object / owner / tenant), where the **matched negative control declined** and a validating
sibling (if any) returned 403, reproduced once in a fresh session with contamination ruled out. A 200
full of the caller's *own* data is not BOLA. A 404 on the cross-principal id is the secure outcome.

## Boundaries (escalate in order; each rung gated on the prior + scope.md)
1. **same user, other object** — your own account, a resource id you shouldn't reach → medium.
2. **same tenant, other user** — a second account in your company → high.
3. **cross-tenant** — a principal in another company → critical; **operator confirm before any artifact**.

## Controls are the whole proof (see adjudication-oracle)
- **Negative:** selector absent / = self must NOT return the other object.
- **Positive / differential:** the validating sibling route returns 403 for the same id.
- **Canary:** the returned data carries the *victim's* planted marker, not yours.
Without all three, it's `needs_review`, never `confirmed`.

## Not this card
- A selector that only picks among the caller's own objects → no cross-principal reach.
- Function/endpoint-level access (you can call an admin route at all) is **BOLA's sibling, not this
  card** — that's broken *function*-level authz; note it, route it, don't conflate it here.

## Do not overclaim
- "It returned 200" proves nothing until the canary shows it returned **someone else's** object.
- Name the exact boundary crossed in one sentence, or it isn't confirmed.
