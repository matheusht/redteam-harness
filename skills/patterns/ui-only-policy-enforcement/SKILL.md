---
id: pattern.ui-only-policy-enforcement
name: Policy Enforced Only In The Client
description: >
  A policy, allowlist, feature-gate or tool-toggle is enforced only in the UI (the client hides the
  option or sends a constrained value), while the server trusts the client-supplied value without
  re-checking the policy — often failing OPEN when the policy object is absent for that user class.
type: pattern
owasp: "A01 Broken Access Control / A04 Insecure Design"
also: "LLM06 Excessive Agency (a disabled tool re-enabled by the client); LLM-supply policy bypass"
atlas: "—"
routes_to: ["vulns/llm06-excessive-agency", "vulns/broken-object-level-authz"]

activation:
  strong:
    - "the UI restricts a choice (model picker, tool toggle, plan/tier, feature flag) but the chosen value travels in the request body/query (e.g. modelAi, mandatoryTools, tier, featureFlags)"
    - "server-side validation loads the policy only for a SUBSET of users, or skips the check when the policy object is null/undefined (fail-open)"
    - "the value is a capability selector the client could set to something the UI would never offer"
  weak:
    - "client-side-only disabling (greyed-out option, hidden menu) with no observable server echo of a re-check"
    - "a value the server merely reflects back without proof it was policy-checked"
  negative:
    - "the server re-resolves the policy for ALL users and coerces/denies disallowed values (e.g. a filter that is applied unconditionally) → defense holds, record as held"
    - "the gated capability is cosmetic over data/actions the caller may already perform"
---

# Policy enforced only in the client

**Idea.** The UI is the only thing stopping the user from picking the disallowed model, the disabled
tool, the higher tier. The server takes the client's word. The classic failure is *fail-open*: the
policy/allowlist is only *loaded* for some user class, so for everyone else it's `undefined` and the
check is skipped entirely.

## Suggested probes
- **Send a value the UI would never offer**: a model outside the company allowlist, a tool the admin
  deactivated, a higher tier/plan, a flag the client never sets.
- **Map allowed-vs-accepted**: compare the principal's UI-allowed set against what the server actually
  accepts. The gap is the finding surface.
- **Hunt the fail-open path**: find the user class for which the policy object isn't loaded (e.g. a
  non-workspace / non-admin seat) and re-test there — that's where `undefined` slips through.
- Compose with `pattern.legacy-route-differential` (the unguarded route may be the way in).

## Required oracle controls (the echo trap is the whole game here)
- **Frame the bypass correctly** (don't invert it): the UI-allowed value succeeding is the baseline.
  If the disallowed value is **coerced or rejected, that is the defense HOLDING** — record as held,
  not a finding. The **bypass is the opposite**: the disallowed value is *accepted* AND the restricted
  capability *actually executes*.
- **Prove it ACTED, don't trust the echo**: the server echoing your requested model/tool is NOT
  confirmation. Require evidence the restricted capability *executed* — response metadata shows the
  disallowed model actually answered, or the deactivated tool actually emitted tool events.
- **Rule out legitimate entitlement**: confirm your account is genuinely *not* allowed that
  capability, else it's not a bypass.
- **Replay** fresh session.

## Counterexamples (defenses that held — keep as negatives)
- A server-side filter applied **unconditionally** to every request coerces the disallowed value →
  held. (This is the *correct* pattern; its presence next to a failing sibling is the tell.)
- A UI gate over an action the user is already entitled to perform → not a privilege bypass.

## Do not overclaim
- "The response shows my requested model id" is an **echo**, not proof the model ran. Show the
  capability executed.
- A disabled tool that still appears in a list but never fires is not excessive agency — require the
  tool's *effect* (events, output, side effect).
