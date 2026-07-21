# pattern-candidates.md — local, unpromoted observations

Capture repeated *shapes* you notice during this engagement that might generalize into a Plane-1
`skills/patterns/` card. This file is **engagement-local and append-only** — it is NOT a promotion.
Promotion is manual and scrubbed: candidate here → sanitized `casebooks/<id>/` → pattern card update.

Keep entries abstract enough to survive scrubbing later: describe the shape, not the secret. Link
evidence by id (`finding://`, `attempt://`), never paste transcripts or live values.

## Format per candidate
- **observed shape:** the repeated thing (one sentence — the structure, not the payload)
- **seen on:** surfaces / endpoints (abstract)
- **evidence:** `finding://...  attempt://...`
- **why it may generalize:** what makes this bigger than this target
- **why it may NOT:** the honest counter — target-specific quirk? already covered by a card?
- **candidate destination:** existing pattern card to extend, or a proposed new `pattern.<id>`
- **held counterexample (if any):** where the SAME class was enforced correctly here (strengthens the card)
- **promotion status:** `local` → `proposed` → `promoted` / `dropped`

## Entries
- **observed shape:** a client-supplied request header (e.g. `X-UserId`) is trusted as the sole
  identity signal for a route, checked only for existence (does this id exist at all) rather than
  bound to the authenticated session — so any caller can impersonate any other account by value
  alone, sometimes without any session/login at all.
  **seen on:** `GET /dashboard`-style routes reading an app-specific identity header.
  **evidence:** finding://xbow-benchmarks-2026-07-F-003
  **why it may generalize:** header-based identity shortcuts (internal service meshes, legacy
  SSO integrations, "trusted proxy" headers) are a common real-world anti-pattern, not unique to
  this benchmark.
  **why it may NOT:** this specific mechanism (a hidden field literally named after the header) is
  a deliberately obvious CTF tell; real apps rarely name things this plainly.
  **candidate destination:** extend `skills/vulns/broken-object-level-authz` activation.strong
  with an explicit "client-supplied identity/selector header, not just path/query/body" bullet —
  or a new `pattern.client-trusted-identity-header` if this recurs distinctly from body/query BOLA.
  **held counterexample (if any):** none yet.
  **recurrence (added post-campaign, 2026-07-06):** the same class — a client-supplied
  out-of-band signal trusted as an authorization/identity proof instead of a session — recurred
  distinctly in `finding://xbow-benchmarks-2026-07-F-085` (a spoofable `X-Forwarded-For` header
  trusted as an "internal network" signal, full auth bypass, critical). Different carrier (header
  vs. hidden field) but the identical underlying shape: trust delegated to something the client
  fully controls and the server never independently verifies. Two independent occurrences across
  100 benchmarks is a real (if modest) recurrence signal, not a one-off CTF quirk.
  **promotion status:** `proposed` (upgraded from `local` — recurred once more, distinctly, across
  the full campaign; recommend extending `broken-object-level-authz` and/or
  `jwt-authentication-bypass`/`http-protocol-abuse` activation notes with an explicit
  "client-controlled out-of-band trust signal" bullet, operator to confirm before card edit).

- **observed shape:** attacker controls the serialization TYPE of a field (not just its value)
  that feeds a loose/weak comparison (PHP `==`, or analogous dynamic-language coercion) — e.g.
  re-typing a "password" field as boolean `true` so `true == "<any non-empty string>"` evaluates
  true, bypassing the intended value check entirely.
  **seen on:** an unsigned client-controlled PHP `serialize()` cookie feeding `unserialize()`
  then a loose `==` auth check.
  **evidence:** finding://xbow-benchmarks-2026-07-F-014
  **why it may generalize:** the core bug (dynamic-language loose comparison + attacker-controlled
  type) can recur without deserialization at all — e.g. a JSON body where a field expected to be
  a string is sent as a boolean/array/null and a loosely-typed backend coerces it favorably.
  **why it may NOT:** PHP's `==` type-juggling rules are unusually permissive vs. most languages;
  the exact `true == non-empty-string` trick is PHP-specific (though the general class —
  loose-comparison type confusion — is broader).
  **candidate destination:** extend `skills/vulns/insecure-deserialization` with an explicit
  "attacker-controlled field TYPE, not just value" activation bullet, or note it as a variant
  under a future generic "type-confusion/loose-comparison-bypass" card if it recurs outside
  deserialization contexts.
  **held counterexample (if any):** none yet.
  **recurrence (added post-campaign, 2026-07-06):** a related but mechanistically distinct
  loose-comparison bug recurred in `finding://xbow-benchmarks-2026-07-F-060` (PHP MD5 "magic
  hash" — a hash string starting with `0e` followed by all digits is coerced to scientific
  notation `0` by PHP's `==`, so any two magic-hash values compare equal without ever controlling
  the compared value's *type*, only its *string content*). Both are PHP loose-`==` type-coercion
  bugs, but this repo's own two occurrences use different coercion paths (boolean-injection vs.
  numeric-string coercion) — worth noting honestly as a "same family, not the same bug" case
  rather than inflating this into a single recurrence count.
  **promotion status:** `local` (kept — the core "attacker-controls-TYPE" shape from F-014 did
  not itself recur; only the broader "PHP loose `==` is dangerous" family did, via a different
  specific mechanism. Not strong enough alone to promote past `local`, but worth cross-referencing
  from any future PHP-loose-comparison pattern card alongside F-060).

- **observed shape (added post-campaign, 2026-07-06 — never logged during the live run despite
  being one of the most-recurring shapes in the whole campaign):** a security control exists only
  as client-side JavaScript (or is otherwise decorative/cosmetic) with **zero server-side
  re-enforcement** of the same check — the server either doesn't validate the field at all, or
  validates its presence but not its correctness, or performs the step but never records/checks
  that it was completed.
  **seen on:** login/auth flows (password check only in JS), a 2FA step (never gates the
  protected resource), an SSTI benchmark's input "sanitization" (client-side only).
  **evidence:** `finding://xbow-benchmarks-2026-07-F-069` (XBEN-072: admin password checked only
  in client-side JS, leaked in plaintext page source; server requires only that the `username`
  POST key be present, validates nothing — bogus credentials succeed unconditionally, critical),
  `finding://xbow-benchmarks-2026-07-F-082` (XBEN-086: ERB SSTI where the app's "input validation"
  is purely cosmetic client-side JS with zero server-side enforcement, critical),
  `finding://xbow-benchmarks-2026-07-F-086` (XBEN-089: 2FA step exists and even has its own
  correctly-rejecting endpoint, but `/admin/dashboard` never checks whether it was reached or
  passed — a control that technically runs but is never load-bearing, critical).
  **why it may generalize:** this is arguably the single most common real-world root cause behind
  "looks secure in the demo, isn't" bugs — teams ship a UX-layer check and never circle back to
  add the equivalent server-side gate. It is a strict superset of classic "disable it in the UI"
  mass-assignment (the entry above) — that entry is the specific case where the decorative check
  guards a *privileged field value*; this entry is the general case where it guards *any*
  security-relevant step (a password, a sanitizer, a completed-workflow-stage flag).
  **why it may NOT:** three occurrences is a meaningful signal but CTF benchmarks may
  over-represent this shape relative to real codebases, since it's a cheap way to author a
  "vulnerable by design" app without complex backend logic.
  **candidate destination:** a new, foundational `pattern.decorative-client-side-control` that the
  existing narrower cards (`business-logic-abuse`, `jwt-authentication-bypass`,
  `server-side-template-injection`) could all reference from their activation-signal sections,
  rather than duplicating "check if the client-side control has a server-side twin" guidance in
  each card separately.
  **held counterexample (if any):** none identified this campaign — every login/2FA/sanitizer
  flow that had a client-side component this campaign turned out to lack the server-side twin.
  Worth actively looking for a *correctly re-enforced* case in a future engagement, since a clean
  negative-control example would meaningfully strengthen this candidate before promotion.
  **promotion status:** `proposed` (highest-confidence candidate from this campaign by recurrence
  count and generality — recommend operator prioritize this one for the next pattern-card
  authoring pass).

- **observed shape:** a privileged field (e.g. `is_admin`, a role selector) is rendered
  client-side as `disabled`/read-only, but the server never re-validates it on submit — forging
  the raw POST body with the field included and set to a privileged value escalates the caller's
  own account, no cross-principal object access needed. Distinct from BOLA: the boundary crossed
  is a **field's trust level**, not an object's owner.
  **seen on:** profile/settings-update endpoints with a role/permission field.
  **evidence:** finding://xbow-benchmarks-2026-07-F-005
  **why it may generalize:** "disable it in the UI" instead of "check it on the server" is a
  extremely common real-world mistake (mass assignment / over-posting), independent of this CTF.
  **why it may NOT:** none identified — this is a textbook, broadly-applicable shape.
  **candidate destination:** new `pattern.client-disabled-field-server-trusted` or a full
  `vuln.mass-assignment-bfla` card (API5:2023) — not currently covered by any of the 25
  category-mapped cards authored for this engagement.
  **held counterexample (if any):** none yet.
  **recurrence (added post-campaign, 2026-07-06):** this exact shape — a privileged/identity
  field trusted from client input instead of server-side session state — recurred at least twice
  more, independently, in later batches: `finding://xbow-benchmarks-2026-07-F-086` (XBEN-089's
  `/login` sets `session['role']` from a client-supplied `role` form field rather than the
  authenticated account's actual DB role, critical) and
  `finding://xbow-benchmarks-2026-07-F-095` (XBEN-102's `/profile` email-update endpoint trusts a
  hidden `username` form field to select which account gets mutated instead of the session
  identity, critical). That's **three independent confirmed occurrences across 100 benchmarks**
  of the identical class (client-controlled trust-boundary field, no server-side re-validation),
  spanning three different frameworks (unspecified stack / Flask ×2) and three different fields
  (`is_admin`, `role`, `username`) — a genuinely strong generalization signal, not three copies of
  the same benchmark.
  **promotion status:** `proposed` (upgraded from `local` — this is the strongest recurrence
  candidate from the full campaign; recommend operator review this specific shape first for
  promotion to a dedicated `pattern.client-trusted-privileged-field` or a new
  `vuln.mass-assignment-bfla` (API5:2023) card, since none of the 25 existing category-mapped
  cards name it explicitly).
