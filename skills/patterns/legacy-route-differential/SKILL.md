---
id: pattern.legacy-route-differential
name: Legacy / Sibling Route Enforces Differently
description: >
  Two versions or variants of the same logical endpoint enforce DIFFERENT authorization or policy.
  A guard added to the canonical route was never back-ported to the older/alternate one, which stays
  mounted and reachable.
type: pattern
owasp: "A01 Broken Access Control / API1:2023"
also: "the delivery mechanism for many client-supplied-selector and ui-only-policy bypasses"
atlas: "—"
routes_to: [pattern.client-supplied-selector-authz, pattern.ui-only-policy-enforcement]

activation:
  strong:
    - "versioned route pairs for the same resource (/v1 vs /v2, /api vs /internal, legacy vs new)"
    - "a guard / validation call present in one handler and absent in its sibling for the same action"
    - "the frontend calls the new route, but the old one is still mounted and responds"
  weak:
    - "method variants on the same path that branch into different handlers (GET vs POST, query vs body)"
    - "a route named with a deprecation hint (legacy, old, compat, v0) that still answers"
  negative:
    - "all variants funnel through the SAME authorization layer → no differential, record as held"
    - "the legacy route is actually removed / 410s / 404s for everyone"
---

# Legacy / sibling route enforces differently

**Idea.** Authorization that lives at the *route perimeter* gets duplicated per version, and one copy
drifts. The new route gets the guard; the old route keeps serving the unguarded path the team thinks
is dead. The bug is the *delta between siblings*, demonstrated with one fixed actor.

## Suggested probes
- **Enumerate the variants**: version suffixes, method pairs, internal/admin twins of a public route.
- **Run one fixed, authorized-looking request against every variant** and diff the authorization
  *outcome* (not the response shape).
- **Carry a selector or policy value across siblings** (compose with `pattern.client-supplied-selector-authz`
  / `pattern.ui-only-policy-enforcement`): the value the secure sibling rejects, try on the legacy one.

## Required oracle controls
- **The canonical sibling is your positive control**: it must DENY the same action — that proves the
  guard exists and the legacy route is the one missing it.
- **Same actor, same intent**: the only variable is the route. If you changed the account or the
  payload too, you haven't isolated the differential.
- **Canary + replay** as for the underlying pattern (selector / policy). Cross-tenant → operator-confirm.

## Counterexamples
- Both routes deny → no differential.
- The legacy route returns a *different format* but the *same authorization decision* → not a finding.
- A 404 on the legacy route is the route being gone, not a bypass.

## Do not overclaim
- A version difference is not a vulnerability; an **authorization-outcome** difference for the same
  actor is. State the delta in one sentence: "route X allows action A for actor P; sibling Y denies it."
