# Promotion notes — case-2026-07-xbow-ctf-calibration

What this engagement promotes into Plane-1, what is proposed but operator-gated, what already
happened (the 16 new vuln cards authored as part of this engagement itself), what stays
engagement-local, and the sanitization sign-off.

## Reinforces existing pattern cards (no new pattern card needed for these)
| Pattern card | Reinforced by | Held counterexample / new note carried |
| --- | --- | --- |
| `pattern.client-supplied-selector-authz` | 7+ of 100 findings (order/archive/job/draft/ObjectId IDOR), plus 2 findings where the selector was carried in a header rather than body/query | out-of-range/unrelated ids consistently return `not_found`/empty — the recurring negative control across the whole cluster. **Extend activation.strong** to explicitly name headers (custom identity header, X-Forwarded-For) as a selector carrier, not just body/query — one of the two header cases bypassed session/login entirely, which is closer to broken authentication than pure BOLA. |
| `pattern.ui-only-policy-enforcement` | 3 of 100 findings (client-JS-only password check, client-JS-only SSTI sanitizer, a 2FA step that runs but is never load-bearing) | this card was authored against LLM-app tool/model-selector bypasses; this campaign is the first evidence it generalizes cleanly to plain web auth/2FA/sanitizer flows with zero LLM surface. **Recommend adding a line noting the cross-domain confirmation.** |
| `pattern.transitive-sanitizer-reliance` | the 23-benchmark XSS filter-bypass cluster, every case requiring the app's own execution oracle (a headless-browser check observing a real alert/confirm/prompt) rather than reflection | no held counterexample beyond the card's own existing negative-control language; this is a strong volume confirmation of the "reflection is not confirmation" rule at 23 independent instances. |
| `pattern.ssrf-server-side-fetch` | 3 confirmed live-fetch findings; 1 REFUTED chain (XBEN-092) where the bridge and both downstream sinks were live but the outbound body was a hardcoded, non-attacker-controlled literal | the XBEN-092 refutation is a clean new counterexample for this card: reachability of a bridge is not the same claim as attacker-data traversal through it. **Recommend adding this as an explicit counterexample** in the card's negative/held-defense language. |

## Proposed NEW pattern card (operator-gated — NOT auto-created)
`client-trusted-privileged-field` (mass-assignment / BFLA, API5:2023) — seeded by 4 independent
findings (XBEN-005, XBEN-052, XBEN-089, XBEN-102) across 3 different frameworks and 3 different field
names (`is_admin`, `role`, `username`). No card exists yet; referenced in this casebook as
`candidate:client-trusted-privileged-field` (no `pattern.` prefix, so conformance does not try to
resolve it). The shape, if promoted:

- **Trigger:** a privileged/identity field is rendered disabled, read-only, or hidden in the client
  UI (a role selector, an admin flag, an identity field), but the field's NAME still exists in the
  form/DOM.
- **Activation:** forging the raw request with that field present and set to a privileged/target
  value is accepted with no server-side re-validation.
- **Distinguishing test vs. BOLA:** the escalation happens on the CALLER's own object/session, not a
  cross-principal object reach — if the target is a different principal's object, route to
  `pattern.client-supplied-selector-authz` instead.
- **Held counterexample to look for in a future engagement:** a server-side re-derivation of the
  field from the authenticated principal's own DB record, ignoring the client-supplied value entirely
  — none observed this campaign; worth actively seeking to strengthen the card before promotion.
- **Routing cue to encode:** "disabled/read-only in the UI" is a **weak** activation signal on its
  own (very common and often correctly re-checked); it becomes **strong** only once the field name is
  confirmed still accepted server-side.
- Recommend operator review before this becomes a first-class `pattern.*` card, per the harness's
  manual-promotion rule.

## NOT promoted (kept engagement-local per the engagement's own honest reassessment)
- **Type-confusion / loose-comparison family** (PHP `==` boolean-injection auth bypass vs. PHP `==`
  numeric-string "magic hash" coercion): only 2 occurrences, and they are the SAME underlying language
  quirk (PHP loose comparison) exploited via 2 *different* mechanisms (attacker controls the
  serialized field's *type* vs. attacker controls a hash *string's content* to coerce to `0`). The
  engagement's own `pattern-candidates.md` correctly declined to promote this past `local` — worth
  cross-referencing both if a PHP-loose-comparison pattern card is ever authored, but not strong
  enough alone yet.
- **TOCTOU race condition (XBEN-088):** genuinely inconclusive after 3 dispatches; kept as an open
  question in `lessons.md`, not promoted as either a confirmed pattern or a refutation. No race-
  condition pattern card exists; if a future engagement produces a confirmed race-condition finding,
  revisit this case's untested source-informed hypothesis as a starting methodology note.

## Already promoted directly during this engagement (not gated by casebook promotion)
Per the engagement's scope (`scope.md`: "Categories without a card... are authored as part of this
engagement rather than skipped"), 16 new `skills/vulns/*` cards were authored at campaign start and
each validated by at least one confirmed finding in this campaign: `sql-injection`,
`cross-site-scripting`, `server-side-template-injection`, `os-command-injection`,
`path-traversal-lfi`, `xxe-injection`, `insecure-deserialization`, `arbitrary-file-upload`,
`information-disclosure`, `business-logic-abuse`, `known-cve-exploitation`,
`jwt-authentication-bypass`, `graphql-abuse`, `cryptographic-weakness`, `default-creds-brute-force`,
`http-protocol-abuse`. Combined with the two pre-existing vuln/pattern cards
(`broken-object-level-authz`, `ssrf-server-side-fetch`), all 25 XBOW tag categories mapped to a card
and every one was exercised at least once. This casebook does not re-propose these — they are
first-class vuln cards already in the repo — but it is the closest thing to a validation report for
each of them (see `oracle-matrix.json` for per-category adjudication).

## Stayed engagement-local (NOT promoted)
- All literal `FLAG{sha256...}` ground-truth strings, exact container ports/hostnames/image tags, and
  the local (gitignored) Dockerfile/compose patches needed to build the upstream clone — none of
  these are portable security content.
- The two real credential values actually recovered mid-campaign (an XBEN-095 admin password via
  blind SQLi, an XBEN-102 test-account password) — never written to any plane per CLAUDE.md's
  redaction policy, from the moment of discovery; a post-campaign grep audit found zero hits.
- Individual finding-level detail for all 100 confirmed findings (severities, exact routes, exact
  payload shapes) — these remain in `engagements/xbow-benchmarks/findings/` and `evidence/` in Plane
  3; only the aggregate pattern-class shapes and oracle reasoning are promoted here.
- The ground-truth-formula reliability methodology note (stale build-guard files causing 2 flag
  mismatches) — banked as a portable oracle-validity lesson in `lessons.md`'s prose, not as a
  structured pattern-card candidate, since it is a harness/tooling risk rather than a target-side
  vulnerability shape.

## Sanitization sign-off
Operator-scrubbed 2026-07. This engagement targets a public, Apache-2.0-licensed benchmark suite run
entirely in a localhost sandbox — benchmark ids/titles are public metadata, not a client name, and are
kept per this casebook set's existing precedent of naming real public technologies. This casebook
contains abstract pattern shapes, aggregate counts, and oracle reasoning only; no literal flag string,
no real credential value, no container/infra plumbing detail crosses the Plane-1 boundary. Re-review
before this casebook is ever shared outside the operator's own harness.
