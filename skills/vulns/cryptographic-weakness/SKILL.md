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
    - "a security-relevant boundary/token/id is generated via `Math.random()` (or an equivalent non-CSPRNG) instead of a cryptographic RNG — the classic predictable-multipart-boundary shape (diff-derived: the removed `Math.floor(Math.random() * 10)` hex loop in CVE-2025-7783, the `Math.floor(Math.random() * 1e11)` boundary in CVE-2025-22150 — see the anchors section)"
    - "password/credential storage hashes via a single fast digest (MD5, SHA1, or one-pass SHA-256) with no configurable work factor instead of a proper password KDF (diff-derived: the username-salted MD5 password-encoder in CVE-2020-5229, the PBKDF2 `hasher: SHA1, iterations: 1` defaults in CVE-2023-46233, the single-pass `sha256.convert(password+salt)` in CVE-2024-29886)"
  weak:
    - "an outdated-but-not-yet-broken primitive is used (e.g. SHA-1 for non-password integrity checks) with no demonstrated practical attack"
  negative:
    - "artifacts sampled show high entropy with no discernible pattern across many samples → likely held"
    - "keys are per-installation/per-tenant and not recoverable from client-accessible surfaces"
    - "boundary/token/id generation uses a CSPRNG (`crypto.randomBytes`/`crypto.randomInt`) rather than `Math.random()`, and password storage uses a proper KDF (BCrypt/Argon2id/high-iteration PBKDF2) rather than a bare fast digest → likely held (diff-derived: the `crypto.randomBytes(12)` swap in CVE-2025-7783, the `crypto.randomInt` swap in CVE-2025-22150, the BCrypt-wrapping `CustomPasswordEncoder` in CVE-2020-5229, the `hasher: SHA256, iterations: 250000` defaults in CVE-2023-46233, the Argon2id `PasswordHash` class in CVE-2024-29886)"

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

oracle: [signal-oracle, adjudication-oracle, ghsa-fix-diff]
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

## Real disclosed anchor(s) for this class (fix-diff-derived)
Priors/taxonomy from real disclosed GHSA fix commits — the vulnerable pre-patch shape and the guard
the fix added. Verbatim hunks + primary sources in `skills/oracles/references/ghsa-fix-diff-corpus.md`
(Cryptographic weakness bucket); consult via the `ghsa-fix-diff` oracle. **These are all *fixed*
bugs, not live-bug claims:** a target matching a removed-line shape is a lead to run through the
funnel above, never a confirmation. The class splits by which primitive is being replaced.

**CSPRNG substitution (`Math.random` → cryptographic RNG), `csprng-substitution`:**
- **CVE-2025-7783** (form-data, GHSA-fjxv-7rqg-78g4, fixed 2.5.4 / 3.0.4 / 4.0.4 @ `3d17230`): a
  `Math.floor(Math.random() * 10)` hex-digit loop building the multipart boundary → single
  `crypto.randomBytes(12)` call. Boundary is predictable once a handful of values are observed
  (e.g. via SSRF/webhook echo), enabling injected form fields in requests the victim app builds.
- **CVE-2025-22150** (undici, GHSA-c76h-2ccp-4975, fixed 5.28.5 @ `711e207`): `Math.floor(Math.random()
  * 1e11)` boundary → `crypto.randomInt(0, max)`, falling back to `Math.random()` only if
  `node:crypto` is unavailable. Same boundary-prediction mechanism as CVE-2025-7783, independent
  package/codebase.

**Weak-hash-to-KDF swap (password storage), `kdf-hardening`:**
- **CVE-2020-5229** (opencast, GHSA-h362-m8f2-5x7c, fixed 7.6 / 8.1 @ `32bfbe5`): username-salted MD5
  Spring Security password encoder → BCrypt-wrapping `CustomPasswordEncoder`, with a legacy-hash
  detection/migration path. Every username/password login.
- **CVE-2023-46233** (crypto-js, GHSA-xwcq-pm8m-c4vf, fixed 4.2.0 @ `421dd53`): PBKDF2 defaults
  `hasher: SHA1, iterations: 1` → `hasher: SHA256, iterations: 250000`. Silent weak-default hit by
  any caller not explicitly overriding options — the documented, common call shape.
- **CVE-2024-29886** (serverpod, GHSA-r75m-26cq-mjxc, fixed 1.2.6 @ `a78b9e9`) — **CONTESTED**
  (15+-file migration commit, illustrative only): single-pass `sha256.convert(password+staticSalt)`
  → Argon2id via a new `PasswordHash` class. User creation, password change, and reset flows.
- **CVE-2021-39182** (EnroCrypt, GHSA-35m5-8cvj-8783, fixed 1.1.4 @ `e652d56`): insecure-API removal
  — the public `MD5()` hashing method (bare `hashlib.md5`) deleted outright rather than guarded; no
  replacement guard line, the removal itself is the fix.

## Not this card
- A weak primitive used for a non-security purpose (e.g. MD5 for a cache key, not auth) → not this
  card.
- A brute-forceable secret due to sheer guessability of a *value* (e.g. default password) rather
  than a *cryptographic generation* weakness → `creds.default-credentials-brute-force`.

## Do not overclaim
- "This uses MD5" or "this token looks short" is an activation, not a finding.
- Show the actual forged artifact and what it let you do as the second principal, or it's
  `needs_review`, never `confirmed`.
- If the class's added-guard shape is already present in the target's source for the reached sink —
  a CSPRNG call in place of `Math.random()`, or a proper KDF (BCrypt/Argon2id/high-iteration PBKDF2)
  in place of a bare fast digest (see the anchors above) — this path is patched; do not claim strong
  activation without a further, specific reason. Presence of the guard is a strong held signal, not
  a soundness proof.
