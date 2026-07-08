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
  weak:
    - "the HMAC secret is short or appears to follow a guessable pattern, but brute force hasn't confirmed it yet"
  negative:
    - "signature is verified with a fixed algorithm allowlist, exp/iss/aud are checked, kid is validated against a fixed keyset → likely held"

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

oracle: [signal-oracle, adjudication-oracle]
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
