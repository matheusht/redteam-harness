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
  weak:
    - "role-only middleware (isAdmin / hasRole) applied to a route that also accepts a cross-principal selector — role gates WHAT you are, not WHOSE data"
    - "a guard that resolves the caller's own tenant/company but never compares it to the path/body id"
  negative:
    - "the helper makes binding MANDATORY (no role-only path) or the {id}-segment check is centralized in middleware so a route cannot omit it → defense holds, record as held"
    - "every call site passes the binding (sweep shows no omissions) → held; the helper is merely verbose, not unsafe"
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

## Do not overclaim
- An optional-bind signature is a STRONG activation, not a confirmed finding — prove a live call site with
  the sibling control.
- "Many routes use the unsafe helper" is a hypothesis about blast radius; only routes with a passing live
  oracle (or an unbound write proven + reverted) are confirmed.
