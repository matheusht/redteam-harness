# Promotion notes — case-2026-06-ai-webapp-builder

What this engagement promotes into Plane-1, what is proposed but gated, what stays local, and the
sanitization sign-off.

## Reinforces existing pattern cards (no new card needed)
| Pattern card | Reinforced by | Held counterexample carried |
| --- | --- | --- |
| `pattern.client-supplied-selector-authz` | F1 (public-bucket read by sequential id), F2 (body-supplied project id write-IDOR) | the app's own org-scoped API denies the same foreign id |
| `pattern.indirect-prompt-injection` | F3 (uploaded doc obeyed as instruction), F4 (injection drives the code-gen tool) | the email-only org-invite token gate that blocks silent A->B delivery |
| `pattern.ssrf-server-side-fetch` | C-ssrf-custom-domain, as a REFUTATION | DNS-only, no HTTP fetch, ownership-CNAME gate — the non-finding this card exists to catch |

F1/F2 are a second-target-class recurrence of the client-supplied-selector shape (the b2b case was the
first). That recurrence is worth folding into that card's "recurring shape" note.

## Proposed NEW pattern card (operator-gated — NOT auto-created)
`postgrest-anon-data-exposure` — seeded by F6/F7/F8. No card exists yet; referenced in the casebook as
`candidate:postgrest-anon-data-exposure` (no `pattern.` prefix, so conformance does not try to resolve it).
The shape, if promoted:

- **Trigger:** the app ships a Supabase/PostgREST anon key to the browser.
- **Activations:** (a) a table returns rows to anon while siblings return empty -> permissive/`USING (true)`
  RLS policy; (b) a SECURITY DEFINER RPC callable by anon -> default privileges grant EXECUTE to anon,
  and a `REVOKE ... FROM PUBLIC` does NOT undo it; (c) an RPC that takes a user/org id arg with no in-body
  `auth.uid()` check -> returns arbitrary users' data (this leg overlaps `pattern.client-supplied-selector-authz`).
- **Held counterexamples baked in:** sibling tables with correct RLS; an anon-granted RPC that guards in-body.
- **Routing cue to encode:** a REVOKE-FROM-PUBLIC-only fix is a red flag, not a green check.
- **routes_to:** would route to the `broken-object-level-authz` vuln card (currently a stub) — same open
  question as the b2b case: the OWASP-LLM/web-authz vuln cards are mostly stubs, so building
  `broken-object-level-authz` as a first-class vuln card is the natural next slice before this pattern
  card lands. Flagged for the pattern-candidates flow; needs operator review + a scrubbed sign-off, per
  the harness rule that pattern promotion is manual.

Two lower-value shapes were observed but are NOT proposed as cards (recorded in lessons only): the
secure-sibling postMessage handler (F9, a differential tell already covered by existing diff discipline)
and the managed-auth config items (F10 reset enumeration, F11 refresh-token rotation) which are GoTrue
configuration, not a code/routing shape.

## Stayed engagement-local (NOT promoted)
- The platform/client name, the Supabase project ref and anon key, all live project/user/org/thread ids,
  invite tokens, canary literals, internal hostnames and IPs.
- The exact `file:line` root causes and concrete remediation (migrations, handler edits, GoTrue env) live
  in the engagement's `linear-issues.md` / `REPORT.md` in Plane 3, not in the portable harness.
- The lower-severity findings (F5 internal host, F9 postMessage origin, F10 reset enumeration, F11 refresh
  rotation, F12 source map) — kept in the engagement report; only their routing/FP lessons abstract up here.

## Sanitization sign-off
Operator-scrubbed 2026-07. This casebook contains abstract shapes, API/field-level detail, and oracle
reasoning only. No secret crosses the Plane-1 boundary. Re-review before this casebook is ever shared
outside the operator's own harness.
