# Promotion notes — case-2026-06-b2b-agentic-chat-api

## What this case promoted
- **New pattern card:** `pattern.unsafe-default-authz-helper` (Shared Authz Helper With Opt-In Binding).
  This case is its founding evidence. Distinct from `client-supplied-selector-authz` (the vuln shape) by
  naming the **root cause + gray-box detection method**: find the guard, read its signature for an optional
  bind param, classify call sites. Routes to `vulns/broken-object-level-authz` and co-activates
  `client-supplied-selector-authz` + `legacy-route-differential`.
- **Re-confirmed** `client-supplied-selector-authz` at family scale (not a single route), strengthening it.

## Why a new card rather than a note on the existing one
The existing card activates on the *selector being present*. It does not tell you to pivot to the **guard's
signature** or to enumerate call sites — the move that turned one route into a swept class here. That
detection technique is reusable across any framework with a shared authorizer, so it earns its own card.

## Scrubbing attestation
Operator-scrubbed 2026-06. Removed: all company/user/team ids, tenant display names, hostnames, emails,
passwords, bearer tokens, the canary literal. Kept: abstract route-family shape, the opt-in-binding
signature shape, abstract verdicts/controls. No payloads, no live secrets. Conformance secret-scan clean.

## Open follow-ups (not promoted — pending a future focused pass)
- Cross-tenant **mutation depth**: member-team reassignment (PATCH) and role changes were source-suspected
  but parked for operator review before live exercise. If confirmed, they reinforce the same pattern at the
  write tier; no new card expected.
- A backend service-to-service surface (separate from this SPA-facing API) was recon'd and parked
  out-of-scope; if later exercised it likely re-instances `unsafe-default-authz-helper` independently.
