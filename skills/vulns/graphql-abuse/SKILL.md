---
id: gql.graphql-abuse
name: GraphQL Authorization & Exposure Abuse
description: >
  Prove a GraphQL API lets a caller reach fields, objects, or relations across an authorization
  boundary that a REST equivalent would block — via unguarded resolvers, missing field-level authz,
  or query shape (nesting/batching/aliasing) that hides many small requests inside one. Confirmed
  only with a benign planted canary that crossed the boundary, never real cross-principal data.
type: vuln
owasp: "API Security Top 10 (GraphQL-specific): excessive data exposure, missing depth/complexity limiting, broken object-level authz via resolvers"
atlas: "—"
patterns: [pattern.client-supplied-selector-authz]

activation:
  strong:
    - "introspection is enabled in a non-dev environment, exposing the full schema/types/relations"
    - "a query can traverse from an owned object to a related object (nested field, connection, edge) without the resolver re-checking ownership on the traversal"
    - "no query depth, complexity, or batch-size limiting — deeply nested or aliased/batched queries are accepted uncapped"
    - "a sensitive field is returned alongside public fields on the same type with no field-level authz"
  weak:
    - "introspection is disabled but the schema is guessable/leaked via error messages or client bundles"
    - "depth/complexity limits exist but are high enough that practical abuse may still fit under them"
  negative:
    - "resolvers re-resolve ownership from the authenticated session on every hop of a traversal, not just the root query → likely held"
    - "field-level authz is enforced per-field regardless of query shape"

safe_signal:
  proxy: >
    a predeclared distinctive artifact only reachable via successful exploitation of this class —
    a benchmark's build-time flag in a CTF context, or an operator-planted canary placed in a
    resource owned by a SECOND principal you control, returned via a resolver/traversal/batch that
    should not have reached it.
  never: >
    do not read, store, or exfiltrate real third-party data; use only planted canaries in OWNED test
    accounts; cross-tenant reach requires scope.md authorization AND an operator confirm before any artifact.

impact_escalation:
  enabled_by: scope.md#impact_demo_authorized
  requires: human_confirm
  containment: "synthetic canary only; logged in engagement cleanup.md with a revert"

oracle: [signal-oracle, adjudication-oracle]
severity_rubric: { cross_principal_data_via_resolver: critical, introspection_plus_sensitive_field_exposure: high, unbounded_query_dos_potential_no_data_exposure: medium }

procedure:
  - "INTROSPECT (passive): pull the schema via introspection if enabled; otherwise infer types/relations from client bundles or error messages. This is recon, not an attack."
  - "MAP RESOLVERS: for each type/relation that can traverse to another principal's data (nested field, connection, edge), ask who re-checks ownership at that hop — not just at the root query."
  - "PLANT A CANARY: in a resource owned by a SECOND principal you control, place a distinctive benign marker."
  - "NEGATIVE CONTROLS (must decline): the same traversal/query shape requesting only the caller's own data must not return the canary; a direct REST/root-level equivalent (if one exists) that correctly 403s is your differential positive control."
  - "ATTACK: construct the traversal, batch, or aliased query that reaches the second principal's canary through the resolver graph rather than a direct object-id swap."
  - "TEST BATCHING/ALIASING SEPARATELY: submit many small sub-queries hidden inside one request (aliases, batched operations) and check whether per-field authz is still enforced on each, or only on the outer request."
  - "ESCALATE THE BOUNDARY within scope: same-user-other-object → same-tenant-other-user → cross-tenant. STOP at the scope.md ceiling; cross-tenant artifacts need operator confirm."
  - "RULE OUT legitimate entitlement and contamination; REPLAY in a fresh session."

emits: [attempt, finding]
---

## What "confirmed" looks like here
A query, traversal, or batched/aliased request returns the **planted canary** from a resource owned
by another principal, where the equivalent direct/root-level request (if one exists) correctly
declined, reproduced once in a fresh session with contamination ruled out. A schema you can
introspect is not a finding. A query that only ever resolves the caller's own objects is not this
card.

## Not this card
- Introspection being enabled with no subsequent cross-principal data reach → note as
  `information-disclosure`/coverage, not GraphQL abuse.
- A direct object-id swap on a single flat query with no resolver traversal involved →
  `bola.broken-object-level-authz`, not this card.
- Missing depth/complexity limiting with no confirmed data exposure → held/needs-review, a DoS
  concern to route elsewhere, not a data-boundary finding here.

## Do not overclaim
- "Introspection is on" proves nothing until a traversal/batch actually returns another
  principal's planted canary.
- Name the exact resolver/field/hop where authz was missing, or it isn't confirmed.
