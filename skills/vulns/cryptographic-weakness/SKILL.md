---
id: crypto.cryptographic-weakness
name: Cryptographic Failure — Predictable/Forgeable Artifact
description: >
  Prove a token, session id, reset link, or signature is predictable or forgeable because of a weak
  primitive, low-entropy generation, or a hardcoded/reused key — and that the weakness lets you
  produce a VALID artifact for a principal you don't own. A theoretically weak algorithm with no
  forged artifact is coverage, not a finding.
type: vuln
owasp: "A02:2021 Cryptographic Failures"
atlas: "—"

activation:
  strong:
    - "a security-relevant artifact (session id, password-reset token, API key, signed cookie) is sequential, timestamp-seeded, or otherwise low-entropy across sampled values"
    - "a broken primitive is used for a security purpose (MD5/SHA1 for password hashing without salt, ECB mode for confidentiality, a static/hardcoded key found in client code or config)"
    - "sensitive data is transmitted or stored unencrypted where the app's own behavior implies it should be protected (e.g. a 'secure' flag or claim contradicted by observed plaintext)"
  weak:
    - "an outdated-but-not-yet-broken primitive is used (e.g. SHA-1 for non-password integrity checks) with no demonstrated practical attack"
  negative:
    - "artifacts sampled show high entropy with no discernible pattern across many samples → likely held"
    - "keys are per-installation/per-tenant and not recoverable from client-accessible surfaces"

safe_signal:
  proxy: >
    a predeclared distinctive artifact only reachable via successful exploitation of this class —
    in a CTF context, a benchmark's build-time flag revealed by forging a valid session/token for
    another principal; in a live app, a valid artifact successfully produced for an
    operator-planted second account, without ever having been issued that artifact honestly.
  never: >
    do not attempt to forge or use artifacts belonging to real third parties; predict/forge only
    against OWNED test accounts; do not exfiltrate real user data recovered via a forged artifact.

impact_escalation:
  enabled_by: scope.md#impact_demo_authorized
  requires: human_confirm
  containment: "forged artifact used only against a synthetic/owned account; logged in cleanup.md"

oracle: [signal-oracle, adjudication-oracle]
severity_rubric: { forged_valid_artifact_for_other_principal: critical, weak_primitive_confirmed_not_yet_forged: medium, weak_primitive_identified_theoretical: low }

procedure:
  - "IDENTIFY THE ARTIFACT: pick one security-relevant token/session/signature/key you can sample repeatedly under your own account(s)."
  - "SAMPLE, DON'T GUESS: collect N samples (issue the artifact repeatedly — new sessions, repeated password resets, etc.) and look for a statistical pattern (sequence, timestamp correlation, low bit-entropy). One sample proves nothing."
  - "PLANT A SECOND PRINCIPAL: create or use a second account you control as the forgery target."
  - "FORGE: using the identified pattern/weak primitive, predict or construct a valid artifact for the second principal WITHOUT it ever being issued to you honestly."
  - "CONFIRM BY USE: the forged artifact must actually authenticate/authorize as the second principal (session accepted, reset completes, signature verifies) — not just 'looks like a valid format'."
  - "NEGATIVE CONTROL: confirm a random/unrelated guess of the same shape does NOT work, isolating that the pattern (not luck) produced the forge."
  - "REPLAY in a fresh session/new sample set to rule out a one-off fluke."

emits: [attempt, finding]
---

## What "confirmed" looks like here
You produced a **valid, working artifact** for a second principal purely from the observed
weakness (pattern prediction or broken-primitive reversal), and that artifact was accepted by the
app as if issued to that principal — reproduced once more from a fresh sample set. Identifying that
MD5 or ECB is in use, with no forged artifact to show for it, is coverage.

## Not this card
- A weak primitive used for a non-security purpose (e.g. MD5 for a cache key, not auth) → not this
  card.
- A brute-forceable secret due to sheer guessability of a *value* (e.g. default password) rather
  than a *cryptographic generation* weakness → `creds.default-credentials-brute-force`.

## Do not overclaim
- "This uses MD5" or "this token looks short" is an activation, not a finding.
- Show the actual forged artifact and what it let you do as the second principal, or it's
  `needs_review`, never `confirmed`.
