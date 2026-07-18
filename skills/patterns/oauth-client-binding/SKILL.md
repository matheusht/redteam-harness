---
id: pattern.oauth-client-binding
name: Authorization Code Is Not Bound to Its Client
description: >
  An authorization server redeems an OAuth/OIDC authorization code without
  enforcing the code's registered client authentication or an equivalent PKCE
  binding. A party that obtains a valid code can therefore exchange it as the
  approved user without proving possession of the client credential.
type: pattern
owasp: "A07:2021 Identification and Authentication Failures"
also: "CWE-287 Improper Authentication"
atlas: "—"
routes_to: ["vulns/authentication-bypass"]

activation:
  strong:
    - "the token endpoint accepts authorization_code without authenticating a registered confidential client, even though a client secret is issued or advertised"
    - "the authorization code is not bound to client_id at redemption and the associated client does not require PKCE"
    - "a real local end-to-end flow issues tokens after a code-only exchange for a secret-bearing client"
    - "the code-exchange handler redeems a code for any authenticated client without independently comparing the code's issuing client_id to the presenting client (diff-derived: the missing `authReq.GetClientID() != client.client.ClientID` check in CVE-2026-55672 / GHSA-xqxv-4jc2-x56x)"
    - "a public client is auto-approved on repeat authorization via `if skip_authorization? || matching_token?` with no client-confidentiality check, letting a malicious app impersonate a previously-approved public client (diff-derived: CVE-2023-34246 / GHSA-7w2c-w47h-789w)"
  weak:
    - "a client secret is stored but its use at the token endpoint is unclear"
    - "the server supports both public and confidential clients but does not persist authentication method metadata"
  negative:
    - "the token endpoint verifies the registered client secret or a private-key assertion before redemption"
    - "the code's client binding and a mandatory PKCE verifier independently reject a code-only exchange"
    - "the code-exchange path rejects a mismatched client_id via an explicit equality check (`authReq.GetClientID() != client.client.ClientID`), and/or auto-approval requires `pre_auth.client.application.confidential?` in addition to a matching token → likely held (diff-derived: zitadel GHSA-xqxv-4jc2-x56x, doorkeeper GHSA-7w2c-w47h-789w)"

safe_signal:
  proxy: >
    Use only a local, disposable authorization server and synthetic user. Show
    that a code issued to a secret-bearing client is redeemed without that
    secret; include a matched PKCE or authenticated-client control where the
    product supports it.
  never: >
    Do not intercept another user's authorization redirect, register a client
    against a third-party service, or redeem a production authorization code.

impact_escalation:
  enabled_by: scope.md#impact_demo_authorized
  requires: human_confirm
  containment: "local disposable client and synthetic user only; delete temporary state and record cleanup"

oracle: [signal-oracle, adjudication-oracle, ghsa-fix-diff]
severity_rubric: { code_only_synthetic_exchange: needs_review, code_theft_bypasses_confidential_client_proof: high, missing_client_check_without_code-acquisition-path: medium }

procedure:
  - "Classify the client: public, confidential, or unspecified. Read discovery metadata, registration output, and persisted client fields together."
  - "Trace authorization session creation, code issuance, code redemption, client authentication, redirect binding, PKCE verification, and one-time-use update."
  - "Run a local code-only redemption for a secret-bearing client only when scope permits; record whether no client credential was sent."
  - "Use a matched control that shows an invalid or absent PKCE verifier is rejected where PKCE is mandatory, and distinguish that from the confidential-client path."
  - "Separate the authentication defect from code acquisition: interception, redirect-handler compromise, or local-app capture is a distinct impact precondition."
  - "Replay the local flow with fresh code state and preserve only redacted evidence."

emits: [attempt, finding]
---

## What confirms the mechanism

A client that the product treats as secret-bearing can obtain an authorization
code for a synthetic user, then redeem that code at the real local token
endpoint without presenting its client secret and without an equivalent PKCE
proof. The result must be a real issued synthetic token, not merely a missing
branch in source.

## Real disclosed anchor(s) for this class (fix-diff-derived)
Priors/taxonomy from real disclosed GHSA fix commits — the vulnerable pre-patch shape and the guard
the fix added. Verbatim hunks + primary sources in `skills/oracles/references/ghsa-fix-diff-corpus.md`
(OAuth / OIDC flow flaws bucket); consult via the `ghsa-fix-diff` oracle. **These are all *fixed*
bugs, not live-bug claims:** a target matching the missing-check shape below (several of these fixes
add a guard with no line removed — the bug is an absence, not a stray statement) is a lead to run
through the funnel above, never a confirmation.

- **CVE-2026-55672** (zitadel, GHSA-xqxv-4jc2-x56x, fixed 3.4.12 / 4.15.2 @ `0973b074`):
  `codeExchangeV1` redeemed a code for any presenting client with no comparison to the client_id
  that initiated the authorization request → inserted `if authReq.GetClientID() !=
  client.client.ClientID { return ... ErrInvalidClient }` before the existing PKCE/code-challenge
  check. Authenticated code-exchange endpoint (`POST /oauth/v2/token`); companion client_id guards
  added to the refresh and device-code flows in the same commit. `client_id-equality-guard`.
- **CVE-2023-34246** (doorkeeper, GHSA-7w2c-w47h-789w, fixed 5.6.6 @ `313af273`): repeat-authorization
  auto-approval — `if skip_authorization? || matching_token?` — treated any client with a prior
  matching token as re-approvable regardless of client confidentiality → `if skip_authorization? ||
  (matching_token? && pre_auth.client.application.confidential?)`. Per RFC 8252 8.6 a public client's
  identity cannot be assured from client_id alone; reached at `GET/POST /oauth/authorize`, adjacent to
  but distinct from the token-endpoint binding case above. `client-confidentiality-predicate`.

## Do not overclaim

- Authorization codes are themselves bearer values. Missing client
  authentication does not prove that a remote attacker can obtain one.
- A deliberately public client with mandatory PKCE is not a confidential-client
  authentication bypass.
- Duplicate redemption is related but distinct: it needs an atomicity test and
  should not be silently bundled into this finding.
- If the class's added-guard shape is already present in the target's source for the reached sink —
  an explicit client_id equality check at code exchange, or a client-confidentiality predicate gating
  repeat-authorization auto-approval (see the anchors above) — this path is patched; do not claim
  strong activation without a further, specific reason. Presence of the guard is a strong held
  signal, not a soundness proof.
