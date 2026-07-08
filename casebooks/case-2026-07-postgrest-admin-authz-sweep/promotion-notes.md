# Promotion notes — case-2026-07-postgrest-admin-authz-sweep

What this engagement promotes into Plane-1, what is proposed but gated, what stays local, and the
sanitization sign-off.

## Reinforces existing pattern cards (no new card needed)
| Pattern card | Reinforced by | Held counterexample carried |
| --- | --- | --- |
| `pattern.ui-only-policy-enforcement` | client-side admin-route guard + client-side role display, contrasted against the server-side `is_admin`-style check that actually matters | the header-trust "vary" signal, refuted as a browser-confound, not a real trust-header bypass |
| `pattern.client-supplied-selector-authz` | client-supplied owner/tenant filters on direct PostgREST reads; a `p_user_id`-style RPC argument | RLS held broadly across the schema; coupon/pricing server-side recomputation; self-referral guard |

## Proposed NEW pattern card (operator-gated — NOT auto-created)
`rpc-family-guard-contrast` — seeded by F-001. No card exists yet; referenced in the casebook as
`candidate:rpc-family-guard-contrast` (no `pattern.` prefix, so conformance does not try to resolve it).
The shape, if promoted:

- **Trigger:** a large, homogeneous, same-prefixed family of privileged functions/routes exists
  (admin RPCs, GraphQL resolvers sharing a directive, gRPC methods behind a common interceptor, REST
  admin routes behind a shared middleware/decorator).
- **Technique:** enumerate the FULL family via schema/OpenAPI introspection (not just what the client
  organically calls), fire every member from an under-privileged session, and diff the denial signature.
  The member that returns data instead of matching the family's common refusal is the missing-guard
  finding — the family's own uniformity supplies both the negative control (siblings deny) and the
  positive control (the guard convention demonstrably works elsewhere).
- **Extension:** the same technique applies to a mutating sub-family via error-differential probing
  (call with a well-formed nonexistent target id so no action can complete; a role/permission error
  means the guard fires before data validation).
- **routes_to:** would extend `skills/vulns/broken-object-level-authz` (function-level / BFLA
  family-contrast technique) rather than needing its own vuln card — the underlying vulnerability class
  (API5 BFLA) already has a home; what's new is the *discovery technique*, not the vulnerability shape.
  Flagged for the pattern-candidates flow; needs operator review + a scrubbed sign-off, per the harness
  rule that pattern promotion is manual.

`decoupled-entitlement-gate` — seeded by F-002 (needs_review, not confirmed). Proposed as an EXTENSION
of `pattern.ui-only-policy-enforcement` rather than a new card: "an authz-adjacent advisory RPC exists
but is not invoked server-side by the resource-serving endpoint" is a specific, common instance of the
existing card's "policy enforced only in the client" idea, just with the policy check itself exposed as
a callable endpoint instead of purely client-side logic. Recommend folding this activation clause into
the existing card rather than minting a new one. Stays `candidate:` until an operator reviews; not
promoted on the strength of a `needs_review` finding alone.

## Stayed engagement-local (NOT promoted)
- The real company/brand name and parent organization, the production hostname and API/DB gateway
  subdomains, a sibling-brand referral domain, every real email address encountered, the real referral
  code, the anon key and session JWTs, and edge/CDN request ids.
- The exact RPC/table names, param signatures, and file:line remediation guidance live in the
  engagement's own findings/evidence files in Plane 3, not in the portable harness. One RPC name that
  embedded a brand-derived abbreviation was generalized to a description rather than carried verbatim.
- F-002 (decoupled entitlement gate) stays `needs_review` local pending a non-entitled test account; it
  is NOT counted as a confirmed finding in `case.yml` and should not be cited as one until an operator
  closes it out either way.
- The untested storage/realtime surface (infra outage throughout the engagement) and the untested
  signup mass-assignment question (blocked by a working bot gate) are recorded as coverage gaps in
  `hypotheses.yml`/`oracle-matrix.json`, not as held defenses — do not read their absence from
  `case.yml`'s `held_defenses` as a claim that they were tested and found safe.

## Sanitization sign-off
Operator-scrubbed 2026-07. This casebook contains abstract shapes, API/field-level detail, and oracle
reasoning only. No secret, real hostname, real email, token, or live id crosses the Plane-1 boundary.
Re-review before this casebook is ever shared outside the operator's own harness.
