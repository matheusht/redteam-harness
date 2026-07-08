# Lessons — case-2026-07-oss-supply-chain-tooling (portable, scrubbed)

Generalized routing, false-positive, and methodology lessons from a white-box/source-available audit
of a public OSS developer-tooling ecosystem under a HackerOne bounty program. No verbatim submitted
report text, no exact CVSS-vector strings, no PoC source, no file:line permalinks — those stay in
Plane 3. Project identities are kept (public GitHub repos), matching this repo's own precedent for
naming a real backend vendor in the worked b2b/webapp-builder cases.

## Methodology lessons (this engagement's biggest generalizable contribution)

### Ground a new pattern card in real prior art before firing it, same session
Three OWASP/vuln gap classes had no existing card at engagement start (cache poisoning, prototype
pollution, workflow-runtime step injection). Rather than force a bad-fit existing card or skip the
class, the engagement ran a deep-research pass FIRST (disclosed CVEs/GHSAs, researcher writeups,
cross-project confirmation), built a real card from that research, and only then fired it against the
live source. Two of the three research passes surfaced a genuinely novel, source-level lead in the
SAME session (an MCP-specific prototype-pollution shape with no disclosed prior art; a workflow
authz-boundary shape whose closest public analogues are Temporal/Argo/Airflow CVEs on a different but
related invariant). Both leads became confirmed findings. Lesson: "we don't have a card for this
yet" is a research task with a tight, same-session turnaround, not a reason to skip a strong-looking
gap or to force it into an ill-fitting existing card.

### Multi-round, keep-biased regrade caught a real miss the original investigation had wrongly closed
The symlink-disclosure finding (F2) had a second, independently unguarded occurrence of the exact same
anti-pattern in a different file, reached by a different command. The ORIGINAL investigation had
already looked at that second file and concluded it was safe — but it had only checked one of two
relevant internal functions and missed the other. An independent regrade agent, instructed to trust
nothing and re-derive every claim from primary sources, found the second occurrence, and its claim was
then independently re-verified against source (not just accepted) before the prior "checked, safe"
conclusion was corrected IN PLACE, with the wrong prior text left visible and marked corrected rather
than silently deleted. This is the single sharpest lesson of the engagement: a "checked this, looks
safe" note inside an evidence file is a hypothesis at the time it was written, not a verdict — it needs
a second, differently-motivated pass before a finding is closed as bounded. The same discipline also
caught two real overclaims across the three findings (a "called from every install path" claim that
was actually one of four; a stale checklist line contradicting its own report's correct Impact
section) and one severity-inflation issue (critical revised to high once PR:L vs PR:N was traced
correctly) — all fixed in place, all before submission.

### Verification-of-the-verification: prefer the real, unmodified artifact over a hand-built emulator
Every one of the five findings in this engagement was, at some point, confirmed against the REAL
published package: the real CLI binary spawned exactly as a user would run it (not an internal
function import), the project's own real test harness with a new test added to it, or the real
exported public API with only the network boundary intercepted. Two concrete near-misses this
discipline caught: (1) an isolated regex-replica round for the terminal-escape sanitizer was
insufficient on its own — the escalation to a fully-terminated clipboard-write sequence required
confirming against real stdout bytes, exact-match not substring-match, because a naive terminator
would itself be independently stripped by the same catch-all pass the isolated replica didn't fully
model; (2) an early draft of a prototype-hijack PoC artificially injected an extra property to
simulate a stronger, unproven claim ("any phantom tool name becomes callable") — this was caught and
removed before reporting, a self-caught overclaim, not one an external reviewer had to find.

### A HackerOne "duplicate" verdict is a validity signal, not a refutation
Two of the five confirmed findings (the MCP tool-approval bypass and the workflow token-
predictability finding) were submitted and returned as duplicates. Both had passed the full internal
adjudication pipeline: real-package reproduction, negative controls, independent regrade, and
pocinator review. A duplicate outcome under a well-run CVD program most often means another
independent researcher found the same root cause via their own path, not that the harness's own
verdict was wrong — the routing/oracle discipline that produced "confirmed" should not be discounted
by a later program-side administrative outcome. The correct response, taken here, is to ask the
triager what the report duplicates (closing the loop, not just accepting the label) and to keep
scoring the internal verdict on its own evidence rather than retroactively downgrading confidence
because of it. Practically: this engagement's own novelty checks (public advisories, GitHub issues,
CVE databases) structurally CANNOT see another researcher's private, already-queued report on the same
mechanism — that blind spot is inherent to novelty-checking, not a process failure, and duplicate
outcomes on genuinely well-verified findings should be expected at some rate, not treated as evidence
the verification process needs to be stricter.

### Persistence discipline produces real, valuable negatives, not just findings
Several genuine dead ends were reached by actually testing, not by assumption, and are recorded with
the same rigor as the positive findings: a git-transport RCE angle killed by git's own hardened
default (not the target's own code); a step-completion-forgery angle killed by tracing the real
dispatch path to an internal queue rather than a public token-only endpoint; a public GitHub issue's
own claimed ReDoS reproduction that simply didn't reproduce against the current real package; and a
sibling framework's named bounty-program focus areas that resolved to a recent, comprehensive,
same-day hardening pass verified by actually running the project's own regression-test suite. None of
these were reported as "looks probably fine" — each has a concrete, reproducible reason it's closed.

## Vulnerability-mechanism lessons (generalizable shapes, not this-repo trivia)

### Prototype pollution has (at least) two distinct triggering shapes — classify which one you have
A literal, `JSON.parse`-derived own key named `__proto__` on an object reads through to the live
`Object.prototype` on a bare property access — this is what fed the flag-provider-merge finding. A
runtime bracket assignment (`obj[name] = x` where the variable `name` holds the string `__proto__`)
instead triggers the inherited setter and reassigns that ONE object's own prototype pointer — a
narrower, more locally-scoped primitive, seen in several "safe" adapters that turned out not to feed
the first shape at all. Getting this distinction right at triage time is what let this engagement
correctly rule several code paths in and several others out, rather than treating every `__proto__`
sighting as equally exploitable.

### An attacker-controlled object key needs an own-key guard at BOTH construction and lookup
The most root-cause finding in this engagement (a tool-discovery container prototype hijack) was found
by re-examining a data flow ALREADY confirmed vulnerable at one point (a lookup) for whether the SAME
untrusted-key-as-object-key anti-pattern also existed earlier, at construction. It did, independently.
General rule: when you find "attacker-controlled string used as an object key with no
`hasOwnProperty`/own-key check," don't stop at the first instance — trace the data backward and
forward through every other place it touches a plain object as a key.

### A "safe default" combined with `??`/truthy-only guards is defeated by any non-nullish prototype hit
Two separate findings in this engagement shared this exact sub-shape: a lookup meant to fall back to a
safe default when a key is absent used `??` or a plain truthy check, and a prototype-chain hit is
non-nullish/truthy, so the fallback silently never fires. This is a distinct, narrower lesson from
"prototype pollution exists" — the specific interaction with nullish-coalescing/truthy-guard fallback
patterns is what makes the pollution executable/impactful rather than just present.

### A multi-pass sanitizer that mutates once, in fixed order, is a reconstitution risk
Any sanitizer built as a fixed sequence of independent regex/string-replace passes (rather than a loop
to a fixed point) is vulnerable whenever an EARLIER pass's non-match can be caused by a byte a LATER
pass removes. The generalizable fix is either a fixed-point loop, or collapsing all generic-control-
byte stripping into one early pass before any pattern-specific detection runs. This shape is not
specific to terminal escapes — it applies to any denylist-style sanitizer implemented as ordered passes
over the same string.

### `dereference: true`-style fixes for symlink handling need their own boundary check, not just a working reported case
A legitimate, narrow fix (symlinks pointing WITHIN a source tree breaking after cleanup) is commonly
shipped by simply dereferencing on copy — and it's easy to ship that fix without ever asking "resolved
to WHERE." The generalizable check: does this codebase, ANYWHERE it dereferences a symlink from
untrusted content, verify the resolved real path stays inside the expected boundary? A "yes" in one
function is not evidence of a "yes" everywhere else the same library/language feature is used.

### A determinism mechanism reused as an implicit security boundary is a recurring anti-pattern
A runtime that deliberately makes its own randomness deterministic for one legitimate reason (replay,
ordering, uniqueness) silently becomes a liability for anything ELSE that draws from the same
randomness source, including things whose own documentation claims a different property
(unpredictability) for that value. The maintainers' own code comments, when checked, plainly stated
the seed was designed for uniqueness/replay-stability — a real, honest impedance mismatch with a
separate, more casual security claim made elsewhere in the same project's docs. General rule: whenever
a sandboxed/VM runtime overrides a language-level nondeterminism primitive for its own legitimate
purpose, enumerate every OTHER consumer of that same overridden primitive before trusting any of their
outputs as unpredictable.

### Predictability is necessary but not sufficient — always check what the predicted value actually authorizes
The same predictable-RNG mechanism fed both a real authorization finding (a public, token-only bearer
endpoint) and a genuine, checked negative (step-completion identifiers, which are equally predictable
but dispatched through an internal queue with no public token-only acceptance surface). Predictability
alone is not the finding; the finding is predictability PLUS a real, reachable surface that accepts the
predicted value as its only credential.

### Code adjacent to a project's own prior CVE is often the best-hardened code in the repo, not the weakest
A flag framework's discovery-endpoint auth and override-cookie handling had already been through one
real hardening round from a prior, unrelated published advisory on the same file. That code held up
completely on re-review. The correct move is to still check it (a second bug on the same surface is
possible), but to calibrate expectations: look at what the OLD fix did not touch, rather than assuming
"one CVE here means this whole area is soft."
