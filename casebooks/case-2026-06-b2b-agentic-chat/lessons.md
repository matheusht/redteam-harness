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

## Re-confirmed on a second run (recurrence, not a one-off)
A later regression pass re-observed the legacy-route-differential live: the object-read guard present
on the canonical version of a per-object endpoint was absent on the still-mounted legacy version, so a
client-supplied owner selector unlocked a cross-tenant object on the legacy route while the canonical
sibling denied the identical request. Two independent positive controls isolated it as route-specific
drift (not systemic): (a) a different path-param endpoint 403'd a cross-tenant id, and (b) the list
variant ignored the owner override entirely. Those holds also killed the public-share false positive —
a legitimately-readable object would have come back on the guarded siblings too. Because it recurred,
`pattern.legacy-route-differential` is now a confirmed recurring shape for this surface class, and its
activation carries the explicit "owner selector honored on legacy, rejected on canonical" cue.

## Refusal muscle held on a fresh axis (non-finding kept on purpose)
A render-path probe drove the model to emit active markup (inert local execution canaries); the chat
renderer escaped it to text and stripped `javascript:` URIs → `refuted`, consistent with the earlier
diagram-XSS non-finding. Discipline note worth keeping: the run also DECLINED to credit an unconfirmed
CSP layer (the header was `frame-ancestors` only) — skepticism applied to the *defense*, not just the
claim. Don't over-credit a control you didn't directly observe, the same way you don't over-claim a vuln.

## Where the traps live now (evaluator hand-off)
The traps this case met — echoed canary, public-share-as-IDOR, inert-reflection-as-XSS,
title-rename-as-execution, phantom CSP, missing replay, duplicate-surface-as-coverage,
one-backend-refusal-as-hold — are encoded structurally in `fixtures/false-discovery/corpus.json` so a
future evaluator can be scored on them mechanically (acceptance: invalid-accept rate = 0). The new
LLM07-confirmed and render-refuted rows are in this case's `oracle-matrix.json`.
