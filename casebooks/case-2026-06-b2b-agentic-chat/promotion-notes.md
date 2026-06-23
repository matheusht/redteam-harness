# Promotion notes — case-2026-06-b2b-agentic-chat

What this engagement promoted into Plane-1 (pattern cards), what stayed local, and the sanitization
sign-off.

## Promoted to `skills/patterns/`
This casebook is the seed for four new pattern cards (created with it):

| Pattern card | Seeded by | Held counterexample baked in |
| --- | --- | --- |
| `pattern.client-supplied-selector-authz` | F2 | owner-scoped export held |
| `pattern.legacy-route-differential` | F2's v1/v2 guard delta | validating sibling route = positive control |
| `pattern.ui-only-policy-enforcement` | F0, F1 | unconditional model filter + image-model validation held |
| `pattern.transitive-sanitizer-reliance` | refuted diagram XSS | the inert-reflection refutation IS the card's reason to exist |

The held defenses are deliberately written into each card's `negative` activation signals and
counterexamples — the casebook proves the team has the right pattern, so the cards teach the harness to
recognize the *correct* shape and not cry wolf.

## Stayed engagement-local (NOT promoted)
- All live ids, the canary string, tokens, passwords, signed URLs, screenshots → Plane 3 only.
- Exact file:line root causes and the concrete remediation steps → live in the engagement's
  `remediations.md` / Linear issues, not in the portable harness.
- Anything that would identify the client beyond `target_class`.

## Sanitization sign-off
Operator-scrubbed 2026-06. This casebook contains API field names, route-version shape, abstract
outcomes, and oracle reasoning only. No secret survives the Plane-1 boundary. Re-review before this
casebook is ever shared outside the operator's own harness.

## Open promotion question
The pattern cards `routes_to` vuln cards that are mostly **stubs** (`broken-object-level-authz`,
`injection`, `llm06-excessive-agency`). F2/F0/F1 are web/API authz at heart, which the harness's
OWASP-LLM corpus doesn't yet cover as first-class vuln cards. Flagged in `pattern-candidates` flow and
in implementation-notes — building those vuln cards is the natural next slice.
