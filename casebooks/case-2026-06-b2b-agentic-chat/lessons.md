# Lessons — case-2026-06-b2b-agentic-chat (portable, scrubbed)

Generalized routing and false-positive lessons. No client verbatim, no secrets.

## The three confirmed findings were one anti-pattern
A client-supplied selector (an owner id, a model id, a tool list) was trusted by the server without
re-resolving the authenticated principal's authorization. Three surfaces, one shape. When recon shows
*any* request field that decides **whose data / which policy / what capability** applies, route to
`pattern.client-supplied-selector-authz` or `pattern.ui-only-policy-enforcement` immediately.

## The held defenses are the strongest tell
The team enforced the *same* class correctly in three places (unconditional model filter, image-model
validation, owner-scoped export). That correctness is a routing signal, not noise: when one sibling of
a control validates and another doesn't, the gap is the finding. Always diff the secure sibling
against the suspect one — the secure one is your positive control that the guard belongs there.
(`pattern.legacy-route-differential` is built around exactly this.)

## Fail-open hides behind "it's validated"
F0's check existed — it just ran against an allowlist that was only *loaded* for one user class, so it
was `undefined` for everyone else and skipped. Lesson: "there is a validation function" is not "the
validation runs for this principal." Find the user class where the policy object isn't populated and
test there. A check that fails open on a missing policy is a no-op for most users.

## Echo is not execution — twice over
Two separate FP traps share one discipline:
- **Capability (F0/F1):** the server echoing your requested model/tool is not proof it honored it.
  Require evidence the capability *ran* — the model answered, the tool emitted events.
- **Injection (refuted diagram XSS):** the payload appearing in page source is reflection, not XSS.
  Require an **execution** signal — an inert benign canary that fires only if it executes. The diagram
  candidate reflected but stayed inert; the honest verdict was `refuted`. Keep it as the example of a
  non-finding so the harness remembers what *not* to claim.

## Routing rule distilled
> A client-supplied field that selects identity, policy, or capability is guilty until the server is
> shown to re-resolve it from the authenticated principal. Confirm with a canary (whose data crossed)
> or an execution signal (the capability ran) — never with a 200 or an echo.
