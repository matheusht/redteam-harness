# fixtures/routing-activation.fixtures.md — recon → pattern-card activation (sanitized)

Purpose: give the **routing layer** (`engine/routing.md`) something real-shaped to calibrate against.
Derived abstractly from the `case-2026-06-b2b-agentic-chat` casebook — no client secrets, only the observation →
activation mappings and the expected oracle verdicts. A routing pass is correct when each observation
below activates the listed card(s) at the listed strength, and the oracle would reach the listed
verdict.

> Chain-of-custody: real values stay in Plane 3. This fixture is shape-level only.

## Activation cases — these observations SHOULD activate (strong)
| Observation (abstract) | Expected card | Strength |
| --- | --- | --- |
| request carries an owner/user id that selects whose data is read | `pattern.client-supplied-selector-authz` | strong |
| two mounted versions of one endpoint (v1/v2) | `pattern.legacy-route-differential` | strong |
| guard present in newer handler, absent in sibling | `pattern.legacy-route-differential` + `pattern.client-supplied-selector-authz` | strong |
| UI-restricted model id travels in the request body (modelAi) | `pattern.ui-only-policy-enforcement` | strong |
| client sends a mandatory-tools list | `pattern.ui-only-policy-enforcement` | strong |
| model output through a markdown/diagram renderer | `pattern.transitive-sanitizer-reliance` | weak |

## Negative cases — these SHOULD activate as `negative` (held defense, not a finding)
| Observation | Expected card | Why it's negative |
| --- | --- | --- |
| a model filter applied unconditionally to every request | `pattern.ui-only-policy-enforcement` | the correct shape — coerces server-side; record as held + positive control |
| owner resolved from the authenticated principal, not a request field | `pattern.client-supplied-selector-authz` | the correct counterpart; held |

## Expected oracle verdicts (the FP-discipline anchor)
A routing/oracle pass calibrated against this casebook must reach:
- owner-id-on-legacy-route → **confirmed** cross-tenant read ONLY with: canary present, no-owner/self
  controls declined, validating-sibling 403 as positive control, fresh-session replay.
- out-of-allowlist model from an ordinary seat → **confirmed** ONLY when metadata shows the disallowed
  model *answered* (not echoed).
- forced deactivated tool → **confirmed** ONLY when the tool *emitted events* (not merely listed).
- diagram/markdown script payload → **refuted** when reflected-but-inert (no execution canary fired).
  Reflection alone must NEVER reach `confirmed`. This is the load-bearing negative.

**Calibration pass = the routing step activates every "should" card at the right strength, flags the
negatives as held, and the oracle refuses to confirm the echo/reflection cases.** If it confirms the
inert diagram payload or a 200/echo without canary/execution proof, fix routing+oracle before trusting
a live verdict.
