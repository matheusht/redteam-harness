# Promotion notes — case-2026-07-waf-content-filter-bypass

What this engagement promotes into Plane-1, what is proposed but gated, what stays local, and the
sanitization sign-off.

## Reinforces existing pattern/vuln cards (no new card needed)
| Card | Reinforced by | Held counterexample carried |
| --- | --- | --- |
| `upload.arbitrary-file-upload` | F1 (alternate PHP tag form bypasses content filter), F2 (shell-exec operator syntax bypasses filter) | extension allowlist plus two independent filename-anomaly rules; a gateway-level route allowlist that helped validate the reachability search's negative result |
| `xss.cross-site-scripting` | C-xss-search-breakout, as a REFUTATION | a custom escaping scheme that both substitutes the quote and doubles a raw backslash, surviving ten distinct encoding techniques |
| `sqli.sql-injection` | C-sqli-tracking-lookup, as a REFUTATION | a true/false boolean differential against a self-owned real record showing zero effect on query logic |
| `patht.path-traversal-lfi` | C-lang-param-traversal, as a REFUTATION | a positive allowlist enforced ahead of the app, identical rejection for garbage and for a crafted traversal payload |
| `pattern.client-supplied-selector-authz` | recon signal only (the tracking-number lookup field) — no authorization finding pursued, since cross-user reach was out of scope this engagement; kept as an activation signal for a future authenticated/cross-account session | n/a this engagement |

## Proposed NEW pattern card (operator-gated — NOT auto-created)
`keyword-blocklist-syntax-equivalence-gap` — seeded by F2 and by the refuted-but-instructive `&&`
WAF-keyword bypass on the SQLi lead (C-sqli-tracking-lookup). No card exists yet; referenced in the
casebook as `candidate:keyword-blocklist-syntax-equivalence-gap` (no `pattern.` prefix, so
conformance does not try to resolve it). The shape, if promoted:

- **Trigger:** a filter/WAF/detector enumerates a blocklist of specific keywords, function-call
  shapes, or operator forms believed to represent a dangerous capability.
- **Activation:** test a semantically-equivalent construct that reaches the same capability using a
  DIFFERENT syntax carrying none of the blocked vocabulary (a different tag-opening form; an
  operator-based execution primitive instead of a named function call; an alternate boolean-logic
  operator symbol instead of a blocked keyword).
- **Recurred twice in one engagement**, on two structurally unrelated surfaces (a PHP upload content
  filter, and a SQL-injection WAF layer) — the strongest kind of signal for promoting a pattern,
  since it wasn't reasoned toward from one incident, it showed up independently twice.
- **Held counterexample to bake in:** a keyword/call-shape bypass being found is NOT itself a finding
  — it still needs either a demonstrated capability effect (F2: a genuinely functional, if
  unreached, command) or a real logic differential against a true positive (the SQLi refutation) to
  land as `confirmed` vs. `refuted`.
- **Routing cue to encode:** whenever a WAF/detector's blocklist is characterized (via error/rule-id
  fingerprinting or direct signature mapping), immediately generate the "same capability, different
  syntax" candidate list as a first-class next probe, not an afterthought.
- **routes_to:** overlaps `upload.arbitrary-file-upload`'s existing "BYPASS ATTEMPTS" procedure step
  and could also apply as a `sqli.sql-injection` / `xss.cross-site-scripting` refinement once those
  cards' bypass-attempt guidance is reviewed. Flagged for the pattern-candidates flow; needs operator
  review + a scrubbed sign-off, per the harness rule that pattern promotion is manual.

One lower-value shape was observed but is NOT proposed as a card (recorded in lessons only): the
distinction between gateway-layer holds (positive allowlist, route allowlist) and app-layer holds,
which is useful engagement discipline but is already implicit in existing oracle/control-recording
practice rather than a new routing shape.

## Stayed engagement-local (NOT promoted)
- The client/program name, the vendor gateway product name, the CMS product name, both real
  hostnames and all subdomains referenced in program materials.
- All internal WAF/gateway rule-id codes and numeric error codes (only the generalizable technique —
  fingerprint a WAF via its rule-id-to-category taxonomy — was kept; the literal codes were not).
- Every uploaded-artifact filename, every canary/marker literal string, and the real self-owned
  tracking-number value obtained via an authorized canary submission.
- The exact reproduction-target domain referenced in the program's own policy text, and its current
  DNS-resolution status.
- The exact `file:line`/remediation detail and the full reachability path-list tried — those live in
  the engagement's own report in Plane 3, not in the portable harness.
- The unresolved live artifacts themselves (stored form submissions, uploaded files) — tracked in the
  engagement's own cleanup ledger, not reproduced here.

## Sanitization sign-off
Operator-scrubbed 2026-07. This casebook contains abstract shapes, filter/signature-class detail, and
oracle reasoning only. No client name, hostname, rule code, canary literal, or live id crosses the
Plane-1 boundary. Re-review before this casebook is ever shared outside the operator's own harness.
