# Lessons — case-2026-07-postgrest-admin-authz-sweep (portable, scrubbed)

Generalized routing and false-positive lessons from a Supabase-backed betting/trading SaaS with a very
large PostgREST surface (~57 tables, ~97 RPCs). No client verbatim, no secrets, no file:line (those stay
in Plane 3). The headline result: a huge, apparently vibe-coded RPC pile was, on rigorous per-function
testing, **mostly correctly gated** — the value here is as much in the disciplined "mostly held" verdict
as in the one real finding.

## The family-contrast oracle: uniformity is the tell
The single highest-value technique this engagement produced. When a backend ships a large, homogeneous,
same-prefixed family of privileged functions (here, ~30 `admin_*` RPCs), don't adjudicate each call in
isolation — enumerate the FULL catalog (authed OpenAPI/schema introspection, not just what the client
organically calls), fire every member from an under-privileged session, and diff the *denial signature*
across the family. The member that doesn't match the family's common refusal is the lead. This is cheaper
and stronger than judging any single call on its own, because the family itself supplies the negative AND
positive control: ~30 siblings denying identically is exactly what makes the one outlier legible as a
missing-guard bug rather than a design choice. Generalizes to any guard-by-convention API surface:
GraphQL resolvers, gRPC methods, framework-decorated REST admin routes, RPC naming conventions.

## A confirmed BFLA sink is not automatically a cross-user Critical
F-001's mechanism is proven end-to-end (any non-admin gets PII + a correlation graph for an email under
their control), but the tester's own account had zero cross-user correlation hits (a clean account), so
the aggregate cross-user leakage couldn't be shown via self-query alone. Escalating to a real third
party requires a genuinely registered, consented identifier under review-gate — and even then, "the
identifier turned out unregistered" is itself a usable result (it independently reproduces the
existence-oracle leg cross-account) without ever touching real third-party PII. Discipline: separate
"the sink executes and returns real data" from "we retrieved a specific non-consenting victim's data" —
the first is confirmable safely on your own account, the second needs an explicit, scoped grant.

## Existence oracles hide inside PII-return functions
A function that returns a populated row for a real subject and an empty result for a fabricated one is,
independent of whatever PII it also leaks, an account-enumeration primitive. Record both properties
separately — the enumeration leg is confirmable with zero PII exposure (fabricated inputs only) and can
be demonstrated cross-account without ever touching a real victim's data, which is exactly what happened
here when the operator-supplied identifier turned out not to exist.

## A "vary" signal from a browser-driven recon pass needs a non-browser replay before it's trusted
The client-trust-header lead (a response that seemed to depend on a client-suppliable tier/environment
header) looked like a textbook forgeable-trust-header bypass. It didn't survive a replay with a direct,
non-browser client: the header value was byte-identical to baseline and the response was identical too.
The lesson isn't "headers are never a vector" — it's that a browser-mediated first pass can itself
introduce a confound (CORS behavior, browser-injected headers, caching) that produces a signal with no
live counterpart. Any header/response "vary" observed through a browser needs a direct-client replay
before it graduates past `weak`.

## RLS held broadly here — record the negative result with the same rigor as a positive one
Every user-scoped table on this schema, tested with the client-side filter dropped or pointed at a
foreign id, returned exactly the caller's own row (or nothing). In a sibling engagement (a different
target class, same Supabase/PostgREST shape) this exact test found a `USING (true)` permissive policy on
one table. Here it didn't. Both outcomes are worth recording with equal rigor: RLS-holds-broadly is not
"nothing happened," it's a proven negative that tells the routing brain this shape is guilty-until-shown,
not guilty-by-default — and the two engagements together are the corpus that shows both outcomes exist in
the wild for the identical activation signal.

## Error-differential probing is how you test a mutating RPC's guard without ever mutating
For the money-moving admin RPCs (approve/payout/delete/toggle), the safe technique is: call with a
well-formed but NONEXISTENT target id, so no action can complete by construction, and read which error
comes back. A role/permission error means the guard fires before data validation (held). A not-found/
no-op means data validation fired first and the guard is still unproven — that ambiguity would need a
different probe. Confirm via pre/post state reads that nothing changed. This is the general pattern for
adjudicating "is this write path gated" under a no-mutation-allowed scope ceiling.

## A decoupled entitlement check is a real shape even when you can't prove the bypass
The paywall lesson here mirrors the injection-sink-vs-delivery lesson from other engagements: the
mechanism (an advisory, client-callable entitlement RPC that the data-serving RPCs never invoke
internally) is a genuine architectural smell worth recording even though the decisive negative control —
replaying from a non-entitled account — couldn't be run (no such account existed, and a bot gate blocked
creating one). Record the mechanism as `needs_review`, not `confirmed` and not dropped. A paid account
returning full data is the *expected* baseline, not evidence of anything.

## Routing rule distilled
> A large, same-prefixed family of privileged functions is guilty-until-shown ONE FUNCTION AT A TIME —
> enumerate the full catalog, fire every member from an under-privileged session, and diff the denial
> signature; the outlier is the lead, and the family's own uniformity is the control. A confirmed sink
> capped by a clean/unregistered test account is `needs_review`, not `confirmed`-at-ceiling and not
> dropped. Any "vary" signal captured through a browser needs a non-browser replay before it counts.
