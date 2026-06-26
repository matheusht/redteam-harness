# Lessons — rotation-case-02-agentic-tooluse

The second rotation case, AI-agentic/tool-use shaped, built to (a) exercise the new
`pattern.ssrf-server-side-fetch` card on a fresh surface and (b) surface **indirect prompt injection**
as an honest coverage gap, the same way rotation-01 surfaced SSRF before its card existed.

## What it tests
- **Agentic generalization, not memorization.** The router must recognize a client-supplied *capability*
  selector (which tool runs) as the same `client-supplied-selector-authz` shape it learned on web object
  ids — selectors generalize from data to capabilities.
- **The SSRF card, scoped.** An agent fetch tool taking a client-supplied `url` activates
  `pattern.ssrf-server-side-fetch` **strong on sight**, but the card's scope posture routes internal
  destinations to review/held — the confirmed evidence here is only a benign operator-owned external
  canary, never an internal/metadata probe.
- **A new honest gap.** Indirect prompt injection (untrusted retrieved content reaching the instruction
  channel) has **no pattern card**. The correct behaviour is to flag a coverage gap, not force-fit
  `transitive-sanitizer-reliance` or a selector card.

## Held / refuted siblings (the anti-overfit half)
Every positive is paired: principal-derived tool set (held), allowlisted fetch with redirects disabled
(held), auto-escaping output renderer (refuted). The case must not teach "every agent tool is a bug."

## Coverage gap recorded — NOW CLOSED
`ROT2-indirect-injection-gap` surfaced the need for an indirect-prompt-injection pattern card. That card
now exists: `pattern.indirect-prompt-injection` (data-sink vs prompt-channel boundary made explicit). A
blind Sonnet router routes this exact shape to it (strong, no force-fit), so the gap is closed. This
case's frozen gold is left as the historical pre-card record (the same way rotation-01 still records the
SSRF gap); a future rotation-03 is the natural surface to exercise the new card under a gold that expects
it. The rotation did its job: stretched the router until it found a real gap, which a card then closed —
without touching frozen gold to manufacture a pass.
