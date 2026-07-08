---
id: creds.default-credentials-brute-force
name: Default Credentials & Unthrottled Authentication
description: >
  Prove a login accepts well-known default/weak credential pairs for a real account, or that
  repeated authentication attempts are not throttled/locked out, or that error messages let you
  enumerate valid usernames. Confirmed only by an actual authenticated session, not the absence of
  an error.
type: vuln
owasp: "A07:2021 Identification and Authentication Failures"
atlas: "—"

activation:
  strong:
    - "a login endpoint exists for a component (admin panel, service account, default install) that plausibly ships with a known default credential pair"
    - "repeated failed login attempts against the same account produce no lockout, delay, or CAPTCHA after a threshold — behavior on attempt N looks identical to attempt 1"
    - "error responses differ between 'user not found' and 'wrong password' (message text, status code, timing), letting usernames be enumerated"
  weak:
    - "a login form exists with no other observed signal yet (not yet tested against defaults or repetition)"
  negative:
    - "default/common credential pairs are rejected and account lockout/backoff engages after a small number of failures → likely held"
    - "error responses are identical regardless of username validity → enumeration held"

safe_signal:
  proxy: >
    a predeclared distinctive artifact only reachable via successful exploitation of this class —
    a benchmark's build-time flag revealed after authenticating, or an operator-confirmed
    authenticated session established against an OWNED/seeded test account using default or
    guessed credentials.
  never: >
    do not run large wordlists or high-volume brute force without explicit scope.md concurrency/
    rate authorization; use a small curated default-credential list; never target real third-party
    accounts.

impact_escalation:
  enabled_by: scope.md#impact_demo_authorized
  requires: human_confirm
  containment: "authenticated session established only against owned/seeded accounts; logged in cleanup.md"

oracle: [signal-oracle, adjudication-oracle]
severity_rubric: { admin_or_privileged_account_default_creds: critical, standard_account_default_creds: high, no_lockout_confirmed_no_successful_login: medium }

procedure:
  - "RECON THE LOGIN SURFACE: identify the endpoint, the account classes it serves (admin/service/user), and whether the app/stack has known default credentials documented upstream."
  - "TRY A SMALL CURATED LIST: a bounded set of well-known default pairs (admin/admin, admin/password, service-account defaults for the identified stack) — not an unbounded wordlist."
  - "CONFIRM VIA SESSION: success means an actual authenticated session/token is established and usable, not merely 'no error was shown'."
  - "TEST LOCKOUT SEPARATELY: send a bounded series of failed attempts against ONE account and compare attempt-1 behavior to attempt-N (timing, message, status) — absence of any change across the series indicates no throttling. Do not scale this into a real brute force without scope authorization."
  - "TEST ENUMERATION SEPARATELY: compare responses for a known-valid username vs a clearly invalid one, holding the password constant, looking for any differential (text, code, timing)."
  - "NEGATIVE CONTROL: an unrelated/random credential pair must fail, isolating that the specific default pair (not a broken login entirely) is what succeeded."
  - "REPLAY the successful login in a fresh session to rule out a fluke."

emits: [attempt, finding]
---

## What "confirmed" looks like here
A curated default-credential pair produced a **real authenticated session** for an actual account,
reproduced once more in a fresh session — or a bounded repeated-attempt series showed no
lockout/throttling change from attempt 1 to attempt N, or a response differential reliably
distinguished valid from invalid usernames. "The login form doesn't show a captcha" alone is not a
finding.

## Not this card
- A forged or predicted session/token derived from a cryptographic weakness rather than a guessed
  credential value → `crypto.cryptographic-weakness`.
- An IDOR/BOLA reached after a legitimate login → `bola.broken-object-level-authz`, not this card.

## Do not overclaim
- "The account exists" or "the form has no rate-limit UI" is an activation, not a finding.
- Show the established session and what it authenticated as, or the lockout-absence delta across a
  bounded attempt series, or it's `needs_review`, never `confirmed`.
