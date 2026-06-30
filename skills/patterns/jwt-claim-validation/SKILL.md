---
id: pattern.jwt-claim-validation
name: JWT Claim Validation Confusion
description: >
  A verifier accepts a structurally valid or signature-valid token but fails to bind critical claims
  such as audience, issuer, algorithm, tenant, or subject to the receiving service's authorization
  decision. Signature-valid is not enough; the token must be valid for THIS verifier and privilege.
type: pattern
owasp: "API2:2023 Broken Authentication / A01 Broken Access Control"
atlas: "—"
routes_to: ["stub:vulns/jwt-claim-validation"]

activation:
  strong:
    - "tokens minted for one audience/service/client are accepted by another service path with different privileges"
    - "the verifier accepts algorithm-confused tokens (`none`, HS/RS confusion, or algorithm not pinned to key type) in a hermetic or scoped test"
    - "authorization decisions use unbound claims (`aud`, `iss`, `tenant`, `org`, `role`, `sub`) without checking they match the current service and authenticated principal"
  weak:
    - "JWTs are decoded client-side or passed between services with no observed audience/issuer check"
    - "multiple services share signing keys, and routes differ in expected audience or tenant scope"
    - "error messages distinguish malformed signature from claim mismatch, suggesting claim checks may be partial"
  negative:
    - "the verifier pins issuer, audience, algorithm, key id/key type, expiry, and subject/tenant binding before granting privilege"
    - "a wrong-audience or wrong-algorithm token is denied by the patched/verifying control"
---

# JWT claim validation confusion

> **Activation vs adjudication.** A token that parses or verifies cryptographically is only an
> activation signal. Confirmation requires a wrong-audience or wrong-algorithm token to grant a
> distinctive canary privilege, while the patched verifier denies the same token.

**Idea.** JWT bugs often live between "the signature is valid" and "this token is authorized here."
The verifier must bind claims to the receiving service, route, tenant, and principal before privilege
is granted.

## Suggested probes (hermetic or scoped only)
- **Wrong audience:** mint or replay a token valid for service A and present it to service B. The safe
  signal is a synthetic privilege canary only service B should deny.
- **Algorithm confusion:** in a hermetic target, present a wrong-algorithm token and require a
  patched verifier positive control that rejects it.
- **Tenant/subject binding:** change only the claim under test while keeping the rest of the transcript
  controlled. Do not use real user tokens or production secrets.

## Required oracle controls
- **Positive control:** the patched verifier denies the wrong-audience/wrong-algorithm token.
- **Negative control:** a correct-audience token behaves normally without crossing privilege.
- **Distinctive privilege canary:** the unauthorized token must grant a canary privilege or state the
  caller should not receive. A decoded token, valid signature, or role string is not enough.

## Counterexamples
- A token is accepted for parsing but no guarded privilege is granted.
- A shared public key verifies the signature, but audience/issuer/tenant checks deny the request.
- A role claim appears in a response because the client supplied it, with no server-side privilege.

## Do not overclaim
- "Signature valid" is not "authorized."
- "Token decoded" is not a bypass.
- Name the exact claim the verifier failed to bind, or keep the result `needs_review`.
