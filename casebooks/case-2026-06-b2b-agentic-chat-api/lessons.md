# Lessons — case-2026-06-b2b-agentic-chat-api

Continuation of `case-2026-06-b2b-agentic-chat` on the same target_class, pivoted to the admin REST API.
The prior case confirmed `client-supplied-selector-authz` once (F2, a single chat-read route). This pass
showed the *same shape was systemic* and named why.

## 1. Role and tenancy are two different questions — fixing one hides the other
The guard answered "are you an admin (of your own company)?" and never "is this companyId yours?". So:
- A **non-admin** was correctly blocked on admin routes (role gate held) — which made the API *look* safe.
- An **admin** sailed straight across the tenant boundary on those same routes.
The non-admin 403s are a trap: they make you conclude "authz works." Always test the boundary with a
principal that *passes* the role gate, or you only measure the gate you weren't worried about.

## 2. An optional safety argument is an unsafe default
`validateCompanyAdmin(user, { expectedCompanyId? })`. The safe call and the vulnerable call differ by one
optional arg. Humans omit optional args. So the bug isn't a route — it's every route that forgot it. This is
the `unsafe-default-authz-helper` pattern: **grep the guard, read its signature, classify its call sites.**
The source sweep predicted the live results before a single request.

## 3. The held route is the oracle, not just a nice-to-have
One family (`company-settings`) bound the id correctly and returned 403 cross-tenant. That single correct
sibling did double duty: (a) it proved the bind *belongs* on the others (the team knows the pattern), and
(b) it was the **negative control** that turned "200" into "confirmed BOLA" instead of "maybe shared data."
Find the route that does it right; it is both your tell and your control.

## 4. Two tiers of the same disease
- **Opt-in bind forgotten** (role checked, tenant not) → cross-tenant for anyone who passes the role gate.
- **No authz at all** (authn-only route) → cross-tenant for *any* seat, read and write.
The second is worse and easy to miss because it has no guard call to grep — you find it by listing routes
that *lack* the guard, not routes that misuse it.

## 5. Cheapest decisive proof for a write: create-your-own-canary then revert
Don't mutate existing records to prove a write boundary. Create a labeled throwaway object in the victim
tenant, confirm it landed (count delta + presence), delete it, confirm gone. Whole thing is one atomic
sequence so nothing is stranded, and the count delta is a clean canary.

## 6. False-positive discipline carried over
`C-xtenant-dashboard-by-nonadmin` *looked* like it should leak (the teams route did), but the role gate
refuted it. Recording the refutation keeps the next engagement from over-claiming "everything is BOLA"
when only the unbound subset is.
