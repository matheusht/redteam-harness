# Lessons — case-2026-07-jvm-gateway-telemetry-oss (portable, scrubbed)

Generalized routing, false-positive, and process lessons from three JVM open-source targets under a
single bug-bounty program. No client verbatim, no secrets, no file:line. The confirmed finding (F1)
sits under an active no-disclosure program term, so this file leans deliberately on METHODOLOGY —
what generalizes to the next white-box engagement — rather than on the vulnerability's own mechanism,
which is already abstracted to pattern-shape level in `case.yml` and stays that way everywhere.

## A citation is a claim about a permalink, not about the commit you're actually looking at
The single highest-confidence lead out of a pre-Stage-0 research pass was grounded in real, strong
disclosed precedent and pointed at a named source file with a specific URL. It did not exist at the
exact pinned commit/tag actually in scope — only on a separate, architecturally distinct legacy
branch of the same repository. Multi-branch, multi-era OSS projects (and this applies well beyond
JVM software) can have the same repository host code that is completely different depending on which
tag you check out. The fix is cheap and non-negotiable: before spending any Stage-0 budget on a
research-grounded lead, verify the cited file/class actually exists at the exact pinned commit you
are auditing. This one check, run early, would have prevented misdirecting the entire primary-target
search onto a sink that plain does not exist in scope.

## Module and class NAMES lie more often than you'd expect — verify the behavior, not the label
This engagement hit the same trap shape repeatedly, across unrelated modules in two of the three
repos: a name strongly implies a security-relevant capability that the implementation does not
provide. A module named for something that sounds like a sandboxing boundary turned out to be a
deprecated legacy wrapper with no security role at all. A feature named for something that sounds
like template-style string substitution (an injection-prone shape) turned out to be same-process,
developer-populated deferred-value resolution with no recursive-expansion primitive. An entry point
named like a bytecode-instrumentation agent accepted the instrumentation handle but never used it to
transform anything. Each of these cost real Stage-0 time before being closed as a name mismatch.
Routing rule: when a name promises a security-relevant mechanism, go read the implementation before
building a hypothesis around the name — the name is a hint, never evidence.

## The same fork-based Stage-0 discipline transfers cleanly across ecosystems
This engagement ran the identical shape of process across three different build systems and two
different host languages (Gradle/Java for the gateway and the metrics library, sbt/Scala for the
telemetry backend) with no methodology changes: parallel forks per hypothesis, each fork required to
back its verdict with direct source reads and grep, each candidate that looked real pushed through
empirical confirmation with the project's own real classes rather than an emulator, and a negative
control required before any verdict was trusted. Nothing ecosystem-specific had to be invented. The
practical implication: white-box Stage 0 discipline is a property of the METHOD, not of the language —
don't reinvent it per repo, port it.

## Two full passes dry, then stop — a repeatable convergence rule
Both secondary targets converged on the same discipline: round one, three forks against the most
plausible hypotheses; round two, three fresh-angle forks plus direct follow-up on any loose thread
round one left open; then declare Stage 0 exhausted. Neither target got a third round manufactured
just because the operator might want more — once every realistic vuln-class hypothesis for the
codebase had a checked, sourced verdict (confirmed, refuted, or "needs_review" with a stated reason
it can't go further from source alone), the answer was allowed to be "genuinely dry" without being
reopened on spec. This is the harness's persistence discipline working as intended in the other
direction: exhaust hard when evidence says a vuln is present (F1), but also let a real dry result be a
real dry result once the space is actually bounded and covered, rather than treating "no finding yet"
as license to keep manufacturing more rounds indefinitely.

## Honest-negative discipline: a dry secondary target is not a wasted secondary target
Two of the three targets closed with zero rewardable findings, and one of those two closed with one
real, mechanism-confirmed finding that is not rewardable by policy regardless of how well it was
proven. Both outcomes were recorded with the same rigor as the confirmed finding: every held control
traced to the actual enforcing code (not "looks fine"), every orphaned-but-present defensive class
traced to its real call graph before being called either a gap or a proof of safety, and the one
architecturally-plausible-but-undocumented "no auth layer at all" case flagged explicitly as an
assumption rather than quietly upgraded to a clean bill of health. A dry engagement leg that is dry
for reasons you can point to in source is worth exactly as much to the routing brain as a confirmed
finding — it's the corpus that keeps the next engagement from re-chasing the same shapes here.

## Mechanism confirmed, reward excluded — these are two different verdicts, don't conflate them
Two real findings this engagement (a protocol-downgrade coverage gap that turns out to be
non-exploitable-as-smuggling but leaves an unbounded-body-size residual, and an unbounded
client-supplied-regex-against-a-live-registry sink) are both real and mechanism-confirmed from source,
and both non-submittable because the program's own policy excludes denial-of-service /
resource-exhaustion classes regardless of proof quality. The lesson is procedural: policy-exclusion is
a filter applied AFTER technical confirmation, not a reason to skip confirming the mechanism, and not
the same verdict as "refuted." Recording "confirmed but excluded" distinctly from "refuted" (rather
than collapsing both into a single "not filed" bucket) keeps the false-positive corpus honest — a
future engagement against a program that DOES reward DoS should be able to reuse the mechanism-level
confirmation, not have to re-derive it because it got filed as a plain negative here.

## A single pass does not get to set final severity — the regrade is not a formality
The confirmed finding's own first-pass framing would have overclaimed it as a default-deployment
bypass. An independent, cold-context regrade re-verified every mechanism claim from source
independently, ran the actual test suite itself rather than trusting a summary, and — critically —
ran a full-repository grep that found no shipped filter anywhere in the project's own source actually
uses the vulnerable pattern. That single check moved the honest framing from "this breaks a stock
deployment" to "this is a foreseeable trap for anyone extending the library's own documented public
API," and correspondingly moved the severity ceiling down a full tier. Never let the pass that finds
something be the same pass that sets its final severity and framing without an independent adversarial
re-check — this is the harness's standing regrade discipline, and this engagement is a clean example
of it materially changing the outcome, not just rubber-stamping it.

## CVSS version must be verified against the real submission form, not assumed
The finding was first scored under CVSS 4.0, reasoned carefully including an honest precondition
metric. The operator later confirmed, from the real bug-bounty platform's own scoring widget, that the
live form actually uses CVSS 3.1 — a materially different metric set with no equivalent precondition
metric. Re-deriving the score in 3.1 produced a second, sharper lesson: an initial proposed compromise
metric combination "sounded" like a moderate middle ground but, run through the actual 3.1 formula,
still computed to a near-maximal critical score, because the Scope-Changed calculation path is far
more front-loaded than intuition suggests — small changes to which sub-metrics you set under
Scope:Changed swing the total much harder than the same changes do under Scope:Unchanged. Two
generalizable rules: (1) confirm which CVSS version a program's real submission form actually uses
before reasoning a vector in a different one — don't assume the newest version is the one in use; (2)
hand-verify the arithmetic of any proposed CVSS vector yourself rather than trusting that a metric
combination which "sounds moderate" computes to a moderate score, especially anywhere Scope is
involved. Check real disclosed comparables for the same bug class (this engagement found genuinely
split precedent among close comparables) before defaulting to the more aggressive scope treatment.

## Novelty-check discipline: absence of a prior report is evidence, corroborating confusion is not disclosure
Before treating the confirmed finding as report-ready, the novelty check queried the project's own
security-advisory API (empty) and searched broadly for any prior CVE/GHSA/issue describing the exact
mechanism (none found). Separately, it found genuine, independent public developer confusion around
the exact API surface involved, which strengthened the "foreseeable trap, not contrived" framing
without those threads themselves constituting a prior disclosure of the actual bypass mechanism —
they show people hitting the SYMPTOM, not people reporting the underlying defect. Keep that
distinction sharp: evidence that a surface confuses real users is corroboration for impact framing,
not a substitute for (or a violation of) the novelty check itself.

## No-disclosure program terms are a stricter constraint than the harness's standard scrub
The harness's standard casebook rule strips PII, secrets, tokens, and client names. A program term of
"no disclosure, ever, under any circumstance" is categorically stricter for an UNRESOLVED finding: even
the exact class/method names and file:line citations of the specific defect can themselves constitute
inappropriate disclosure while a report sits pending triage, independent of whether they contain any
secret in the usual sense. This casebook is the concrete instance: F1 is described at full pattern-
shape generality (a documented reject API not honored by a downstream pipeline stage) with the
specific identifiers removed, while the underlying open-source projects' names stay in the open
because their existence is already public. The generalizable rule for any future engagement under a
no-disclosure program: apply the standard scrub AND a second abstraction pass on any pending,
unresolved finding's technical mechanism, and re-review both passes again once the finding's
disposition changes (filed, triaged, resolved, or the program's policy changes).

## Routing rule distilled
> For white-box JVM/multi-language OSS work: verify every research citation against the exact pinned
> commit before routing budget onto it; verify what a security-sounding name actually implements
> before hypothesizing about it; run the same fork-based Stage-0 discipline regardless of language or
> build system; let two full passes plus follow-ups be a real stopping rule, not a floor to exceed on
> spec; keep "mechanism confirmed" and "reward-excluded by policy" as two distinct, both-recorded
> verdicts; never let the pass that finds something also be the only pass that grades its final
> severity; verify the CVSS version against the real form and hand-check the arithmetic yourself,
> especially near Scope:Changed; and under a no-disclosure program, abstract an unresolved finding's
> technical mechanism to pattern-shape, not just its client identity, before it ever reaches this file.
