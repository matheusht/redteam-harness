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
    - "the verifier decodes with a permissive default algorithm set or treats `alg` as optional/defaulted rather than pinning and binding it to the header — the key-type-confusion variant (a substring denylist for `-----BEGIN PUBLIC KEY-----`/`ssh-rsa` in HMACKey key-checks) and the header-selects-algorithm variant (`alg?: SignatureAlgorithm` left optional) both let an attacker forge a signature the verifier accepts (diff-derived: CVE-2024-33663, CVE-2022-29217, CVE-2023-48223, CVE-2026-22817 — see the anchors section)"
    - "the signature-verification branch is gated only on token shape rather than failing closed when no matching signature config is found — e.g. an unsigned token silently defaults `algorithms = ['none']`, or a signature check is skipped entirely `if (signedJWT != null)` fails for a wrapped/alternate token shape (diff-derived: CVE-2022-23540, CVE-2026-29000)"
  weak:
    - "JWTs are decoded client-side or passed between services with no observed audience/issuer check"
    - "multiple services share signing keys, and routes differ in expected audience or tenant scope"
    - "error messages distinguish malformed signature from claim mismatch, suggesting claim checks may be partial"
  negative:
    - "the verifier pins issuer, audience, algorithm, key id/key type, expiry, and subject/tenant binding before granting privilege"
    - "a wrong-audience or wrong-algorithm token is denied by the patched/verifying control"
    - "the verifier rejects asymmetric/PEM/SSH-formatted keys as HMAC secrets via a safe-API type check (not a substring denylist), requires an explicit `alg` bound to the header, and fails closed (throws/returns an error) rather than defaulting when no signature configuration matches → likely held (diff-derived: the `is_pem_format()`/`is_ssh_key()` swap in CVE-2024-33663/CVE-2022-29217, the `header.alg !== alg` binding check in CVE-2026-22817, the `signatureConfigurations` fail-closed check in CVE-2026-29000)"
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

## Real disclosed anchor(s) for this class (fix-diff-derived)
Priors/taxonomy from real disclosed GHSA fix commits — the vulnerable pre-patch shape and the guard
the fix added. Verbatim hunks + primary sources in `skills/oracles/references/ghsa-fix-diff-corpus.md`
(JWT / token validation flaws bucket); consult via the `ghsa-fix-diff` oracle. **These are all *fixed*
bugs, not live-bug claims:** a target matching a removed-line shape is a lead to run through the
funnel above, never a confirmation. This card's own claim-binding activation signals (audience/issuer/
tenant/algorithm unbound) are broader than these anchors — the anchors ground the algorithm-confusion
and fail-open-signature sub-slice specifically. The bucket splits two ways.

**Asymmetric-key-as-HMAC-secret confusion (denylist → safe-API/canonicalization):**
- **CVE-2024-33663** (python-jose, GHSA-6c5p-j8vq-pqhj, fixed 3.4.0 @ `12f30c8c`): substring denylist
  for PEM/`ssh-rsa` markers in `HMACKey.__init__` → `is_pem_format()`/`is_ssh_key()` safe-API check.
  Reachable via `jwt.decode()` when the caller passes no explicit algorithms allow-list and the
  attacker sets header `alg=HS256`. `denylist-to-safe-api`.
- **CVE-2022-29217** (PyJWT, GHSA-ffqj-6fqr-9h24, fixed 2.4.0 @ `9c528670`): the same denylist pattern
  in `HMACAlgorithm.prepare_key()` → the same `is_pem_format`/`is_ssh_key` swap. Reachable when the
  caller decodes with `get_default_algorithms()`. `denylist-to-safe-api`.
- **CVE-2023-48223** (fast-jwt, GHSA-c2ff-88x2-x9pg, fixed 3.3.2 @ `15a6e92c`): a plain-string
  PEM-header matcher (`.includes()`) missed the PKCS#1 `RSA PUBLIC KEY` header variant → regex
  canonicalization (`/^-----BEGIN( RSA)? PUBLIC KEY-----/`). `canonicalization`.

**Fail-open algorithm/signature binding (bind to header, fail closed):**
- **CVE-2026-22817** (hono, GHSA-f67f-6cw9-8mq4, fixed 4.11.4 @ `cc0aa7ae`): `alg` left optional
  (defaulted to `'HS256'`), letting the untrusted JWT header's own `alg` select the verification
  algorithm whenever the resolved JWK omitted one → `alg` made mandatory plus a `header.alg !== alg`
  binding check throwing `JwtAlgorithmMismatch`. `param-binding`.
- **CVE-2022-23540** (node-jsonwebtoken, GHSA-qwph-4952-7xr6, fixed 9.0.0 @ `83450307`): an unsigned
  token with no `algorithms` option silently set `options.algorithms = ['none']` → the verifier now
  returns an error requiring explicit `"none"` opt-in to accept unsigned tokens. `other`.
- **CVE-2026-29000** (pac4j, GHSA-pm7g-w2cf-q238, fixed 4.5.9 @ `d9c57aa6`): the signature-check branch
  was entered only `if (signedJWT != null)`, so a JWE wrapping an unsigned `PlainJWT` skipped signature
  verification entirely → a fail-closed `if (!signatureConfigurations.isEmpty())` check now requires a
  `SignedJWT` whenever a signature configuration is defined. `other`.

## Do not overclaim
- "Signature valid" is not "authorized."
- "Token decoded" is not a bypass.
- Name the exact claim the verifier failed to bind, or keep the result `needs_review`.
- If the class's added-guard shape is already present in the target's verifier for the reached path —
  asymmetric/PEM/SSH keys rejected via a safe-API check rather than a substring denylist, `alg`
  mandatory and bound to the header (not caller/attacker-selectable), and the signature branch failing
  closed when no configuration matches — this path is patched; do not claim strong activation without
  a further, specific reason. Presence of the guard is a strong held signal, not a soundness proof.
