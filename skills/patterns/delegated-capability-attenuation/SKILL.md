---
id: pattern.delegated-capability-attenuation
name: Delegated Capability Loses Its Restrictions
description: >
  A framework converts an incoming constrained credential into an internal
  service credential, but the derived credential omits the original audience,
  permission, tenant, or operation restrictions. The downstream service then
  treats that derived identity as unrestricted.
type: pattern
owasp: "A01 Broken Access Control"
also: "CWE-269 Improper Privilege Management"
atlas: "—"
routes_to: ["vulns/business-logic-abuse"]

activation:
  strong:
    - "an inbound credential carries an explicit allowlist, scope, audience, tenant, or permission restriction, and an internal token/delegation constructor drops that field"
    - "the receiving service treats absence of the dropped field as unrestricted access, while the direct receiving path rejects the same constrained credential"
    - "a shipped service-to-service client forwards caller credentials through that constructor to a distinct plugin or service"
    - "a token/code exchange step only runs its restriction-verification branch when the original request appears to have set that restriction, so omitting the restriction up front silently skips verification at redemption (diff-derived: the code_challenge-presence-gated PKCE branch removed in GHSA-mrx3-gxjx-hjqj (authentik) and GHSA-qgp8-v765-qxx9 (cloudflare workers-oauth-provider))"
    - "a rejection predicate combines a binding-mismatch check and an independent validity check with AND rather than OR, so a credential failing only one of the two conditions is still accepted (diff-derived: the `ClientID != input.ClientID && ExpiresAt...Before(time.Now())` predicate in GHSA-qh6q-598w-w6m2 (pocket-id))"
  weak:
    - "a token exchange creates a new principal and it is unclear whether the original restrictions are represented elsewhere"
    - "documentation recommends a broader allowlist than an indirect route appears to need"
  negative:
    - "the derived credential carries an equivalent restriction, or the receiving service rechecks the original restriction independently"
    - "the only downstream operation is protected by an independent permission or provenance gate that denies the constrained caller"
    - "the exchange/redemption step verifies the delegated restriction (PKCE challenge, client binding, scope) unconditionally rather than gating verification on whether the original request appeared to set it, and any rejection predicate uses OR so it rejects on any single failing condition → likely held (diff-derived: the unconditional downgrade guard added in GHSA-mrx3-gxjx-hjqj / GHSA-qgp8-v765-qxx9, and the `&&`→`||` predicate fix in GHSA-qh6q-598w-w6m2)"

safe_signal:
  proxy: >
    Use a synthetic restricted credential, a disposable local receiver, and a
    harmless marker read or action. The direct constrained request must be the
    negative control; the delegated request must be the only differing path.
  never: >
    Do not use a real service token, another user's data, a production action,
    or a destructive operation. Do not call a mock or emulator decisive proof
    when the product's real token issuer, verifier, and route can run locally.

impact_escalation:
  enabled_by: scope.md#impact_demo_authorized
  requires: human_confirm
  containment: "local disposable fixture or owned account only; record the derived credential path and clean up all marker data"

oracle: [signal-oracle, adjudication-oracle, ghsa-fix-diff]
severity_rubric: { cross-service-read-of-nonpublic-data: high, cross-service-write: critical, local-mechanism-only: needs_review }

procedure:
  - "Name the original constraint exactly: plugin audience, permission names, tenant, operation attributes, or equivalent."
  - "Trace the conversion end to end: inbound authentication, derivation, token claims or context, downstream authentication, and downstream authorization default."
  - "Run a direct negative control: the constrained credential must fail at the otherwise-targeted receiver."
  - "Use the real token issuer, verifier, and a shipped client or route to test the delegated path with a benign marker."
  - "Separate mechanism proof from deployment impact: configuration prevalence, data sensitivity, and independent downstream controls are distinct questions."
  - "Replay the local proof in a fresh process; retain the artifact and cleanup disposition."

emits: [attempt, finding]
---

## What confirms the mechanism

The same constrained credential is rejected at a target directly, yet a real
product-issued delegated credential reaches that target and is treated as less
restricted. A harmless local marker may prove a shipped downstream operation,
but it does not itself prove production data exposure or a write impact.

## Real disclosed anchor(s) for this class (fix-diff-derived)
Priors/taxonomy from real disclosed GHSA fix commits — the vulnerable pre-patch shape and the guard
the fix added. Verbatim hunks + primary sources in `skills/oracles/references/ghsa-fix-diff-corpus.md`
(OAuth / OIDC flow flaws bucket); consult via the `ghsa-fix-diff` oracle. **These are all *fixed*
bugs, not live-bug claims:** a target matching a removed-line/gated-verification shape below is a
lead to run through the funnel above, never a confirmation. All anchors below are a scope/capability
downgrade at exchange time — the exact shape this card names as "delegated credential loses its
restriction."

**Verification gated on whether the original request appears to have set the restriction (the fix
makes verification unconditional), `unconditional-verification`:**
- **GHSA-mrx3-gxjx-hjqj** (authentik, fixed 2023.8.7 / 2023.10.7 @ `38e04ae1`): the token endpoint
  only entered the PKCE code_verifier↔code_challenge verification branch when the stored
  authorization code had a recorded code_challenge → added `if not code_challenge and
  code_verifier: raise invalid_grant`, rejecting redemption whenever the front-channel restriction
  was stripped instead of silently treating its absence as "PKCE not required." Authenticated
  token endpoint, `POST /application/o/token/` (authorization_code grant).
- **GHSA-qgp8-v765-qxx9** (cloudflare workers-oauth-provider, fixed 0.0.5 @ `09a2adb2`): same
  downgrade shape from a distinct product — PKCE verification ran only when `isPkceEnabled` was
  set at authorization → added a conditional immediately before that block rejecting any
  code_verifier presented for a flow that never enabled PKCE. Token-exchange handler, `POST /token`
  (authorization_code grant).

**Rejection predicate uses the wrong boolean connector (the fix swaps AND→OR so either failing
condition alone rejects), `predicate-connector-fix`:**
- **GHSA-qh6q-598w-w6m2** (pocket-id, fixed v2.4.0 @ `34890235`): the token endpoint rejected an
  authorization code only when `ClientID != input.ClientID && ExpiresAt.Before(now)` — a code
  issued to a different client_id remained redeemable as long as it hadn't expired, i.e. the
  client-binding restriction was dropped whenever the second condition didn't independently hold
  → flipped to `||`. Authenticated OIDC token endpoint, `OidcService.createTokenFromAuthorizationCode`.

## Do not overclaim

- A missing field in a JWT or internal object is only a source signal until the
  receiver's actual authorization behavior is demonstrated.
- A test fixture that substitutes the issuer, verifier, or downstream route is
  not decisive evidence for those substituted components.
- A deployment that intentionally grants both the ingress and downstream
  plugins remains relevant to prevalence, but does not erase a demonstrated
  attenuation failure in a narrower configuration.
- If the class's added-guard shape is already present in the target's source for the reached
  sink — verification of the delegated restriction runs unconditionally rather than being gated on
  whether the original request appeared to set it, or a rejection predicate uses OR across all
  failing conditions (see the anchors above) — this path is patched; do not claim strong activation
  without a further specific reason. Presence of the guard is a strong held signal, not a soundness
  proof.
