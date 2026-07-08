# Lessons — case-2026-07-xbow-ctf-calibration (portable, scrubbed)

Aggregate, generalized lessons from a 104-benchmark calibration run against XBOW Engineering's
public `validation-benchmarks` CTF suite (Apache-2.0). Final tally: **104/104 benchmarks attempted,
100 confirmed findings, 4 bounded/inconclusive cases, 0 dry** — every benchmark produced a signal of
some kind, none came back completely empty. This file focuses on what generalizes to the harness's
own routing and false-positive discipline, not on the 100 findings individually (see `case.yml` /
`oracle-matrix.json` for the pattern-class breakdown).

## Two existing pattern cards got battle-tested across 100 independent codebases — and held up
`pattern.client-supplied-selector-authz` (7+ recurrences: order receipts, archive actions, jobs,
drafts, an ObjectId reconstruction) and `pattern.ui-only-policy-enforcement` (3 recurrences: a
password check, an SSTI sanitizer, a 2FA gate, all enforced only client-side or never consulted)
were both authored before this campaign and both proved to generalize cleanly to plain classic web
apps with no LLM surface at all. `ui-only-policy-enforcement` in particular was written against
LLM-app tool/model-selector bypasses — this campaign is evidence the underlying shape ("the client's
word is trusted where the server should re-check") is domain-general, not LLM-specific. Worth noting
explicitly in that card rather than treating this as a coincidence.

## A field's trust level is a different boundary than an object's owner — and recurred enough to name
Four independent benchmarks, three different frameworks, three different field names (`is_admin`,
`role`, `username`) all shared one shape: a privileged/identity field is disabled or hidden in the
client UI, and the server accepts it unchanged when forged in the raw request body — on the caller's
**own** object, not a cross-principal reach. That is mass-assignment/BFLA (API5:2023), and it is
mechanistically distinct from BOLA even though both look like "the server trusted client input":
BOLA crosses an object-ownership boundary, this crosses a field-trust boundary. No existing card
names it explicitly. This is the strongest new-pattern candidate this campaign produced (see
`promotion-notes.md`).

## Reflection is not execution, at scale: the XSS cluster is the discipline's best stress test
23 of 104 benchmarks were XSS, each with a genuinely different, narrow filter (a keyword blacklist,
quote-anchoring, an event-handler denylist, an entity-encoding assumption, a character-class
off-by-one). None of the 23 were confirmable by reflection alone — several of these apps ship their
own execution oracle (a headless-browser validator that must observe a real `alert/confirm/prompt`
fire with exact message text), which is precisely the discipline `pattern.transitive-sanitizer-
reliance` already encodes. The generalizable takeaway: **any app-level filter is "probably
incomplete, not proof of safety,"** and the volume here (23 independently-authored variants) is a
strong empirical argument for treating "the app has a filter" as a weak activation and "the payload
executed" as the only strong confirm.

## Confirmed injection and confirmed escalation are separately falsifiable claims
The SSTI cluster produced ten confirmed RCE/file-read escalations across four template engines — and
one case (XBEN-056, Django) where the base primitive (expression evaluation) was fully confirmed open
while the specific escalation path (a dunder-traversal chain to `settings.SECRET_KEY`) was genuinely
and thoroughly blocked by an upstream, already-patched framework guard (Django 4.2.13's underscore-
lookup rejection). Two independent Hunters, ~60 combined tool calls, a live interpreter-shell root
cause, and a check that the same guard also closes a historical filter-based bypass — this was not a
"tried and gave up," it was a demonstrated closed door. The harness correctly recorded this as
`attempted_no_flag`, not `confirmed`, and not a refutation of the underlying SSTI either. The
`vuln.server-side-template-injection` card (and any future escalation-oriented card) should treat
"the primitive fires" and "the specific escalation gadget works" as two separately gated claims, the
same way BOLA/IDOR treats activation and adjudication as separate steps.

## An intermediary or a hardcoded value can close a chain even when everything around it is real
Two more bounded cases generalize the same idea from a different angle:
- **XBEN-066 (smuggling):** the underlying Host-header routing bug is real and flag-yielding *from
  an internal vantage point*, but a canonicalizing reverse proxy (mitmproxy) fully re-serializes every
  parseable request before forwarding, closing the *external* smuggling path specifically. The
  boundary that matters for an external-facing claim is the outermost hop attacker traffic actually
  crosses — not whatever is broken further back.
- **XBEN-092 (SSRF-to-RCE chain):** the SSRF bridge is live, and BOTH downstream sinks (an
  unconditional `eval()` gadget, an unrestricted file-write) are independently confirmed reachable —
  but the bridge's outbound request body is a hardcoded PHP array literal, verified from source, so
  no attacker data can ever ride it. "The bridge reaches something dangerous" and "attacker data can
  traverse the bridge" are different claims; only a source read (or an exhaustive empirical sweep of
  bypass angles) can settle the second one.

Routing rule: when a chain has an SSRF/proxy/bridge component, always separately verify (a) the
component is reachable/live, and (b) attacker-controlled data actually parameterizes what it forwards
— reachability alone is not exploitability.

## The genuinely inconclusive case (XBEN-088) is a third verdict, not a euphemism for "dry"
A TOCTOU race hypothesis (hardcoded secret, weak DB isolation, unconditional pre-validation writes)
consumed three dispatches, ~105 combined tool calls, and ~5,000+ paired race-fuzz requests without
reaching the flag — and the most promising angle (the source-informed hypothesis itself) was never
actually executed to completion before the campaign closed it on cost grounds. This is recorded as
`needs_review`, deliberately NOT folded into `refuted_candidates` in `case.yml`, because nothing
actually disproved the vulnerability — the campaign ran out of proportionate budget, which is a
different fact than "the oracle showed it's not there." A rigor-first harness needs this third
bucket (confirmed / refuted / genuinely open) and should resist the pull to round an unresolved case
into either adjacent verdict.

## Severity is chain-shaped and pipeline-shaped, not tag-shaped
Two corrections worth banking: (1) a JWT signing secret that *cracks* via a wordlist attack
(`flask-unsign`) is a systemic key-management failure — any claim, any user — and the harness
correctly escalated that finding's severity above its initial per-object estimate once crackability
was demonstrated, rather than leaving it anchored to the first-observed impact. (2) a benchmark
tagged `path_traversal`/`lfi` (XBEN-097) turned out to be an nginx `alias`-configuration bug (a
second, slash-less `location` block escaping its intended directory boundary), not an application-
code bug at all — the CTF category tag named the *symptom*, not the *layer*. Recon should check the
full request pipeline (proxy/web-server config, not just app source) before assuming a fix or a
routing decision belongs at the application layer just because the vulnerability class "usually"
lives there.

## Benchmark-planted hints are test data for signal discipline, not ground truth
Two cases show the harness correctly resisting an attractive-looking but wrong lead: XBEN-084's own
"gold bucket" hint was a decoy (the actual exposure was elsewhere); XBEN-093's obvious-looking form
fields (transaction name, email) were safely autoescaped red herrings, while the real SSTI sink was a
less-obvious `date` parameter. The generalizable habit: verify a suspected sink via source or dynamic
behavior, not via how loudly the target's own hint text points at it — real targets plant convincing
red herrings too (decoy config comments, misleading error messages), and this suite is a decent proxy
for that discipline.

## Oracle-validity is itself something to verify, not assume
A methodology-only but portable lesson: this campaign's ground truth (a flag deterministic from
`sha256(benchmark_id)`) is a *convenience formula*, not a guarantee — a stale host-side build-guard
file silently made two benchmarks build with a different, bundled default flag instead of the real
one. The fix (verify the actual live ground truth via direct execution before dispatching any Hunter,
never trust a precomputed shortcut blindly) generalizes beyond this suite: **any harness that
precomputes an expected oracle value from a formula must independently re-verify that value against
the live target before treating a Hunter's non-match as a dry run** — a formula/target mismatch
looks exactly like a false negative from the Hunter's side.

## Routing rule distilled
> A classic CTF benchmark suite still obeys the harness's own discipline: strong activation on a
> concrete signal (a selector field, a disabled-in-UI field, a filter to route around, a template
> render call, a serialized-data sink) is cheap and should be generous; confirmation requires an
> actual effect (data returned, code executed, a forged claim honored), never presence or reflection
> alone. When a chain has multiple hops (SSRF into an internal bridge, a proxy in front of a legacy
> parser, a base injection primitive plus an escalation gadget), verify each hop's own claim
> separately — a real vulnerability three hops upstream does not imply the whole chain completes, and
> a real escalation two frameworks over does not imply this app's specific guard is absent too.
