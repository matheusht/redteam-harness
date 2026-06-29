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
  weak:
    - "serializers or ORMs expose model fields by default"
    - "client code hides fields in the UI while the API still returns them"
    - "request bodies include admin, role, owner, billing, status, internal, or metadata fields"
  negative:
    - "the serializer filters guarded fields server-side by role before response"
    - "the write path allowlists mutable properties and ignores/rejects guarded fields"
    - "an echoed guarded field is not persisted or used by authorization/business logic"
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

## Do not overclaim
- Whole-object JSON is activation, not confirmation.
- Echoed request JSON is not mass assignment.
- Name the exact property-level boundary crossed, or keep the result `needs_review`.
