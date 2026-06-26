# Lessons — rotation-case-01-web-api (portable, scrubbed)

A deliberately non-Adapta case used to **rotate** the routing qualification eval, so a QUALIFIED verdict
means the router generalizes rather than memorizing one engagement. Seeded from public web-archetype
shapes (csivitu/ctf-challenges, MIT) — inspiration only, nothing vendored.

## Same cards, a different surface
The billing/profile API exercises the SAME two pattern cards as Adapta on an unrelated surface:
- a client-supplied **invoice id** → `pattern.client-supplied-selector-authz` (the IDOR/BOLA shape),
- a SQL **string-builder** sink and a **render** sink → `pattern.transitive-sanitizer-reliance`,
  one as a *strong* unsafe sink (string-built SQL / raw-HTML allowance), one as a *weak* render
  (auto-escaping template). The strong-vs-weak split is the load-bearing routing calibration.

## Every positive carries a held/refuted sibling
The case is balanced on purpose (CTFs are not): IDOR vs session-resolved owner; string-built SQL vs
parameterized; raw-HTML render vs auto-escaped render. The held siblings are the positive controls —
they prove the platform *can* enforce, so the gap is specific.

## The deliberate coverage gap (SSRF)
The avatar-import row (server fetches a client-supplied URL) is **SSRF**, which **no current pattern
card covers**. The correct behaviour is to flag a coverage gap and route to human review — NOT to
force-fit an authz or injection card. If the router confidently force-fits a card here, that is itself
a finding about the router. Candidate follow-up: a dedicated SSRF pattern card (out of scope for this rotation).
