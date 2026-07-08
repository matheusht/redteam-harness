# Lessons — case-2026-07-waf-content-filter-bypass (portable, scrubbed)

Generalized routing and false-positive lessons from a WAF/gateway-fronted upload-testing surface
plus a separate public CMS behind the same gateway. No client verbatim, no secrets, no file:line
(those stay in Plane 3).

## Keyword blocklists enumerate syntax, not capability
The single most important, cross-cutting lesson here showed up **twice, on two unrelated surfaces**,
which is exactly what makes it worth generalizing rather than treating as a one-off. On the upload
surface, a content-based PHP filter blocked a broad, genuinely well-designed set of function-call
shapes (`system(`, `exec(`, `eval(`-family, superglobal access) — but a shell-exec operator syntax
carrying zero keyword, zero call shape, and zero superglobal access sailed through untouched, despite
achieving the same capability. On the CMS side, a WAF blocked the `AND`/`OR` keywords and one boolean
operator symbol, but not a second, semantically-equivalent operator symbol in the target's query
dialect. Same shape both times: **the filter's mental model is "these specific named things are
dangerous," not "here is the underlying capability being reached."** Any time you find a keyword/
call-shape blocklist, the next move — cheap, and high-yield per this engagement — is to ask "what's
a different syntax that reaches the same capability without using any of the blocked words or
shapes?" This is worth its own routing signal independent of which vuln class it shows up in.

## Reachability is a non-negotiable gate, and "dry" has to be earned
Two upload-surface content-filter bypasses were both genuinely confirmed as filter bypasses — but
neither escalated to a code-execution finding, because the accepted artifacts were never shown to be
web-reachable. The discipline that made "not established" a real, load-bearing verdict rather than an
early stop: quantify the search space up front (four independent technique classes: direct path
guessing, verbose-error-message leakage, script/query-param serving guesses, subdomain enumeration;
~95 total guesses), and use a **working control** to validate the negative result (a gateway-level
route-allowlist that visibly, differently blocked out-of-list script guesses proved the plain 404s on
real path guesses were genuine misses, not a gateway silently hiding a real path). Without that
control, "no reachable path found" could just as easily mean "the gateway is intercepting my guesses
before they'd tell me anything" — the control is what makes the dry verdict trustworthy.

## An AND-tautology against a nonexistent id proves nothing — and a scope wall isn't always permanent
A classic differential-SQLi trap: testing `id=<nonexistent> AND TRUE` only ever returns zero rows,
whether or not the field is injectable, so it's not diagnostic on its own. The genuinely useful move
here was **testing a true-clause AND a false-clause against a real, self-owned record** once one
existed — the false-clause variant returning the same "found" result as the true-clause variant is
the actual signal (zero effect on logic). The record became available through an already-authorized,
narrowly-scoped canary submission (self-owned, not cross-user reach), which is worth remembering as a
pattern in itself: a lead that looks "capped by scope" may become testable without ever touching
cross-user data, if a self-owned positive fixture can be created within the existing authorization.

## A functionally capable payload found mid-batch needs its own gate, recognized in the moment
A systematic signature-mapping batch (many inert single-word/keyword probes to map filter coverage)
produced one item that was qualitatively different from its neighbors: a real, if reachable,
command-execution primitive, not an echoed string. The process lesson isn't "don't ever discover this
kind of thing mid-batch" — it's that the moment you notice the difference, stop and separate it out
for its own explicit confirmation, rather than logging it after the fact alongside inert probes. This
happened here with a one-step lag (flagged immediately on discovery, but ideally would have been
isolated *before* running); recorded transparently rather than smoothed over, because catching your
own near-miss and saying so plainly is part of the rigor bar, not a mark against the finding.

## Distinguish gateway-layer holds from app-layer holds using the shape of the block
Two different held controls in this engagement were provably enforced ahead of the application, not
by it: a positive allowlist on a content-selector parameter (any out-of-list value, garbage or
crafted, gets a byte-identical generic block), and a route allowlist that intercepted serving-path
guesses with a visibly different block page than a plain not-found. Recognizing these as
gateway-layer, not app-layer, matters for two reasons: it correctly caps what you can claim about the
app's own logic, and — as above — it becomes a positive control for a completely different question
(whether a "not found" elsewhere in the same session is trustworthy).

## Unusual escaping isn't automatically weak
A non-standard character-substitution scheme protecting a reflection sink looked worth probing
precisely because it wasn't a familiar library-standard escape. It survived ten distinct encoding
attempts across two passes, including one that revealed it *also* doubles a raw input backslash — a
detail that only shows up if you specifically test the trailing-backslash trick, and one that flips
the read from "ad hoc, maybe incomplete" to "someone specifically closed this known bypass class."
Lesson: test unusual defenses harder, not less, precisely because you can't pattern-match them against
a known-good or known-bad shape in advance — and let the actual coverage found update your prior
about whether it's deliberate.

## Routing rule distilled
> When a content filter or WAF enumerates a blocklist of specific keywords, function-call shapes, or
> operator forms, treat "what other syntax reaches the same capability, using none of the blocked
> vocabulary" as a first-class next probe, not an afterthought — this shape recurred across two
> unrelated surfaces in the same engagement. Separately: a filter/detector bypass is not a finding
> until reachability or execution is independently shown, and a "reachability not established"
> verdict needs its own positive control (proof the negative result isn't itself gateway-masked)
> before it can be called dry.
