# Lessons — case-2026-06-ai-webapp-builder (portable, scrubbed)

Generalized routing and false-positive lessons from a Supabase-backed AI web-app builder. No client
verbatim, no secrets, no file:line (those stay in Plane 3).

## The anon key is public — RLS and RPC grants are the whole game
This class of app ships a Supabase anon key to every browser. That key is not the vulnerability; treating
it as if it were a secret is the mistake, and treating it as if it were harmless is the other mistake. The
real authorization lives in RLS policies and function grants, so recon must probe *every* table for RLS
and *every* RPC for anon-callability. The three biggest findings here (F6/F7/F8) were all one root class:
the anon key reaching data it should not, because a policy or a grant was wrong. When you see a browser-
shipped PostgREST key, that whole surface is guilty until each table and function is shown to gate anon.

## "RLS enabled" is not "RLS enforcing"
F6's table had RLS enabled and a policy — the policy was `USING (true)`. Permissive policies OR together,
so one open policy makes the table read-open regardless of the strict ones next to it. Lesson: don't stop
at "RLS is on." Read the SELECT policy. The tell that it's a bug and not a design choice is the sibling
tables: they returned empty to the same anon key. Empty siblings are the positive control that the data
was meant to be gated.

## Trust the live 200 over the reassuring diff
F7 is the sharpest lesson. A source read showed the function did `REVOKE ALL ... FROM PUBLIC` and granted
only `service_role` — which *looks* locked down. The live black-box call still returned PII to anon. The
two disagreed, and the honest move was to re-verify rather than let the clean-looking diff overturn a
confirmed live result. The explanation: Supabase default privileges (`ALTER DEFAULT PRIVILEGES ... GRANT
EXECUTE ON FUNCTIONS TO anon, authenticated`) grant those roles *explicitly*, and `REVOKE FROM PUBLIC`
does not touch an explicit grant. So a SECURITY DEFINER function is anon-callable unless it either revokes
from anon/authenticated by name or guards in its own body. Routing cue: a REVOKE-FROM-PUBLIC-only "fix" is
a red flag, not a green check. Oracle discipline: when a diff says "safe" and the target says "open," the
target wins until you can name the mechanism that reconciles them.

## The safe sibling shows the right shape
A lookup RPC on the same target was also anon-granted, but it rejects anon in the function body (logged-in
check plus a backoffice-membership check). That held control is the counterexample that makes F7/F8
obviously wrong: the codebase already knows how to guard a SECURITY DEFINER function, it just didn't do it
on these. Always find the sibling that does it right — it is both the fix template and the proof the team
had the pattern.

## Client-supplied object id, no ownership re-resolution (second target class)
F1/F2 are the same anti-pattern as the earlier b2b case, now on a different platform: a request field (a
project id, a numeric screenshot id) selects the object, and the server trusts it without re-resolving the
principal's ownership. Read side: a public bucket keyed on a sequential id, unauthenticated and enumerable.
Write side: a POST that lands in another tenant's project. The positive control is the app's own org-scoped
API, which denies the same id — so the gap is specific to the raw storage/handler path, not systemic. This
is a recurrence of `pattern.client-supplied-selector-authz` across target classes, which strengthens it.

## Injection sink is not cross-user reach
F4 confirmed the injection *executes* (a tool effect, marker written into generated code — not a chat
echo). The instinct is to call that a cross-user compromise. It isn't, yet: the only channel to put A's
content in front of B was an org invite whose accept token is unguessable and email-only, with no IDOR.
So the sink is real but undeliverable to a victim without their consent. Discipline: separate "the payload
executed" from "it reached a victim." A confirmed sink plus a robust delivery gate is a High confused-
deputy issue, not a cross-user Critical. The email-only token is a held control that *caps* severity, and
we recorded it as such rather than hand-waving toward the ceiling.

## Echo is not execution; DNS is not a fetch
Two false-positive traps, one discipline (require the effect, not the appearance):
- **Injection (F3/F4):** the payload appearing in output is reflection; the confirm was the tool *acting*
  (marker written into generated code), with a clean-doc negative control.
- **SSRF (refuted):** the custom-domain feature accepting a metadata IP literal *looks* like SSRF, but the
  OAST oracle saw DNS lookups only and zero HTTP fetch — provisioning is gated behind an ownership-CNAME
  the attacker can't set. Accepting an IP is a cosmetic validation gap, not a fetch primitive. Require an
  HTTP callback before claiming SSRF; DNS resolution during domain verification is expected. Kept as the
  `pattern.ssrf-server-side-fetch` refutation so the harness remembers what a non-finding looks like here.

## Routing rule distilled
> A browser-shipped PostgREST anon key makes every table and every SECURITY DEFINER RPC a suspect until
> each is shown to gate anon (restrictive RLS, or a revoke-from-anon, or an in-body auth.uid() check). A
> REVOKE-FROM-PUBLIC-only fix does not gate anon. Confirm exposure with a live anon call, and reconcile it
> against source before trusting either. For the agent surface: a confirmed injection sink is not a cross-
> user compromise until a silent delivery channel to a victim is also shown.
