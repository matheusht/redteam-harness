---
id: jwt.jwt-authentication-bypass
name: JWT Authentication Bypass
description: >
  Prove a JWT-based auth check can be bypassed or forged — alg=none, HS256/RS256 key confusion, a
  weak/guessable HMAC secret, missing signature verification, missing exp/iss/aud validation, or a
  kid-header injection — granting access the caller should not have.
type: vuln
owasp: "A07:2021 Identification and Authentication Failures"
atlas: "—"
patterns: []

activation:
  strong:
    - "a JWT is accepted with alg set to none or a downgraded algorithm"
    - "a JWT signed with an asymmetric algorithm (RS256) is accepted when re-signed as HS256 using the public key as the HMAC secret"
    - "the server does not validate exp, iss, or aud claims that the app logic depends on"
    - "the kid header is used to select a key/file path without validation (injection surface)"
    - "the HMAC-secret key-type check is a naive substring denylist (e.g. scanning for `-----BEGIN PUBLIC KEY-----`/`ssh-rsa` literals) rather than real key-format detection, so a PEM/SSH variant it doesn't enumerate slips through and gets accepted as an HMAC secret (diff-derived: the removed `invalid_strings` denylist in CVE-2024-33663 (python-jose) and CVE-2022-29217 (pyjwt), the plain-string `publicKeyPemMatcher` in CVE-2023-48223 (fast-jwt) — see the anchors section)"
    - "signature/algorithm verification is optional or silently defaults rather than failing closed — an absent `algorithms` option implicitly allows `alg=none`, or `alg` defaults to `'HS256'` and can be steered by the untrusted header, or the signature-check branch is skipped entirely for a token shape the code didn't anticipate (diff-derived: the removed `options.algorithms = ['none']` fallback in CVE-2022-23540 (node-jsonwebtoken), the optional `alg?` param in CVE-2026-22817 (hono), the `if (signedJWT != null)`-only branch in CVE-2026-29000 (pac4j) — see the anchors section)"
  weak:
    - "the HMAC secret is short or appears to follow a guessable pattern, but brute force hasn't confirmed it yet"
  negative:
    - "signature is verified with a fixed algorithm allowlist, exp/iss/aud are checked, kid is validated against a fixed keyset → likely held"
    - "asymmetric keys are rejected as HMAC secrets via real format detection (e.g. `is_pem_format()`/`is_ssh_key()`, or a header-regex covering all PEM variants) rather than a substring denylist, and algorithm/signature checks fail closed — an explicit `alg` is required and bound against the header (`header.alg !== alg`), unsigned tokens are rejected, and signature verification is mandatory whenever configured → likely held (diff-derived: the `is_pem_format`/`is_ssh_key` safe-API swap in CVE-2024-33663 and CVE-2022-29217, the mandatory-`alg` + mismatch check in CVE-2026-22817, the fail-closed unsigned-token rejection in CVE-2022-23540, the required-`SignedJWT` guard in CVE-2026-29000)"

safe_signal:
  proxy: >
    a predeclared distinctive artifact only reachable by successfully presenting a forged/bypassed
    token — e.g. a benchmark's flag, or a planted canary resource reachable only under a forged
    identity in an OWNED test account. Never forge a token into a real other-user's live session.
  never: >
    do not forge access to a real third-party identity; secret brute-forcing stays within the
    scope-approved rate/time budget; cross-tenant reach requires scope.md authorization plus
    operator confirm before any artifact.

impact_escalation:
  enabled_by: scope.md#impact_demo_authorized
  requires: human_confirm
  containment: "forged identity limited to owned/synthetic accounts; logged in cleanup.md"

oracle: [signal-oracle, adjudication-oracle, ghsa-fix-diff]
severity_rubric: { full_auth_bypass_arbitrary_identity: critical, privilege_claim_tampering: high, weak_secret_not_yet_bypassed: medium }

procedure:
  - "DECODE FIRST: inspect header and claims of a legitimate token — no attack needed to read a JWT's own content."
  - "TEST ALG VARIANTS: try alg=none and, if RS256 is used, HS256-with-public-key-as-secret, against a token for an OWNED test account only."
  - "CHECK CLAIM VALIDATION: tamper exp/iss/aud/sub on an owned token and see if the server still accepts it or trusts the tampered claim."
  - "CONFIRM VIA CANARY: the forged/tampered token must grant access to a planted canary resource tied to a second principal you control, not merely decode without error."
  - "BRUTE-FORCE ONLY WITHIN BUDGET: if testing secret strength, stay within the scope-approved rate/time limit; do not run an unbounded offline crack against production infrastructure."
  - "REPLAY in a fresh session; never escalate into a real other-user's live session."

emits: [attempt, finding]
---

## What "confirmed" looks like here
A forged or tampered token is accepted by the server and grants access to a planted canary
resource belonging to a second principal you control, reproduced once, with the legitimate
signature-verification path shown to reject an equivalently tampered token from a matched control.

## Real disclosed anchor(s) for this class (fix-diff-derived)
Priors/taxonomy from real disclosed GHSA fix commits — the vulnerable pre-patch shape and the guard
the fix added. Verbatim hunks + primary sources in `skills/oracles/references/ghsa-fix-diff-corpus.md`
(JWT / token validation flaws bucket); consult via the `ghsa-fix-diff` oracle. **These are all *fixed*
bugs, not live-bug claims:** a target matching a removed-line shape is a lead to run through the
funnel above, never a confirmation. The class splits by failure mode.

**Asymmetric key accepted as an HMAC secret (algorithm confusion — sign HS256 with the server's own
public/RSA key):**
- **CVE-2024-33663** (python-jose, fixed 3.4.0 @ `12f30c8`): a substring denylist
  (`-----BEGIN PUBLIC KEY-----`, `ssh-rsa`, ...) that misses PEM/OpenSSH format variants →
  `is_pem_format()`/`is_ssh_key()` real key-format detection. Reachable whenever `jwt.decode()` is
  called without an explicit algorithms allow-list. `denylist-to-safe-api`.
- **CVE-2022-29217** (pyjwt, fixed 2.4.0 @ `9c52867`): the same substring-denylist gap in
  `HMACAlgorithm.prepare_key()` → the same `is_pem_format()`/`is_ssh_key()` swap. Reachable via
  `jwt.algorithms.get_default_algorithms()`. `denylist-to-safe-api`.
- **CVE-2023-48223** (fast-jwt, fixed 3.3.2 @ `15a6e92`): a plain-string PEM matcher missing the
  PKCS#1 `-----BEGIN RSA PUBLIC KEY-----` header variant → a regex covering both header forms.
  `canonicalization`.

**Signature/algorithm check made optional or fail-open (unsigned or attacker-steered alg accepted):**
- **CVE-2022-23540** (node-jsonwebtoken, fixed 9.0.0 @ `8345030`): an unsigned token with no
  `algorithms` option silently set `algorithms = ['none']` and verified → returns a
  `JsonWebTokenError` instead of accepting. `other`.
- **CVE-2026-22817** (hono, fixed 4.11.4 @ `cc0aa7a`): `alg` was optional (defaulting to `'HS256'`)
  and, via JWK/JWKS verification, could be selected by the untrusted header → `alg` is now mandatory
  and bound with a `header.alg !== alg` mismatch check. `param-binding`.
- **CVE-2026-29000** (pac4j, fixed 4.5.9 @ `d9c57aa`): the signature-check branch only ran
  `if (signedJWT != null)`, so a JWE wrapping an unsigned `PlainJWT` skipped verification entirely
  → a `SignedJWT` is now required whenever signature configurations are defined. `other`.

## Not this card
- A token that merely decodes without error (all JWTs are readable without a secret) → not a
  finding by itself; the payload must grant unauthorized access.
- Session/cookie-based auth flaws with no JWT involved → route to the appropriate authn card, not
  this one.

## Do not overclaim
- "The library supports alg=none" is a capability note, not a finding, until the server actually
  accepts a forged token.
- A short-looking secret that hasn't actually been cracked within budget is `medium` at most, never
  claimed as a full bypass.
- If the class's added-guard shape is already present in the target's source for the reached sink —
  real key-format detection (`is_pem_format`/`is_ssh_key` or an equivalent PEM/SSH matcher) guarding
  the HMAC-secret path, or a mandatory/bound `alg` check plus fail-closed rejection of unsigned or
  unverifiable tokens (see the anchors above) — this path is patched; do not claim strong activation
  without a further, specific reason. Presence of the guard is a strong held signal, not a soundness
  proof.
