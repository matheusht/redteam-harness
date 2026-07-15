---
id: reporting.human-report-voice
name: Human report voice (evidence-calibrated)
description: >
  The DEFAULT voice and humanization standard for every vulnerability report. Makes the prose read as
  genuinely human-authored: neutral, technical, first-person, so it does not trip a triager's "this
  was written by a machine" reflex. Calibrated against the literal prose of 74 disclosed,
  verbatim-verified real reports (70 authors), not received wisdom, so it supersedes the older
  AI-tells folklore in `reporting.vulnerability-report-writing`. Apply it to every report as the final
  pass; a more formal or reserved register is opt-in, not the default.
type: reporting
owasp: "—"
atlas: "—"
---

## When to run this

**This is the default voice for every report.** Unless a specific program or context explicitly wants a
more formal, reserved register, every report ships in this humanized voice. The reserved register is
the opt-in exception, not the baseline.

Run it last. Write the report first under `reporting.vulnerability-report-writing` (canonical shape,
evidence, severity reasoning) and map it onto the form with `reporting.hackerone-reports`. Then do
this pass over the finished draft. It changes register, not facts. Never let it touch a CVSS vector,
a version pin, a line number, a quoted javadoc, or an impact claim.

## The one principle

Human prose is not a set of tricks you add. It is the absence of machine uniformity. The tells that
give an LLM away are almost all *over-correction and over-uniformity*: every aside on a dash, every
sentence the same length, every claim hedged, every section announced. So the goal is variety and
plainness, not a checklist of "human phrases" to sprinkle in. When in doubt, cut a device rather than
add one.

This skill is grounded in a real corpus. The evidence base is
`../research/hackerone-genuine-human-corpus.md` (74 reports, 70 authors) and
`../research/hackerone-humanization-ruleset.md` (the gated rules). The reference files below are the
day-to-day distillation.

## Calibrated rules (the register levers you apply)

These are things you can and should adjust in any draft, because they are safe and structural.

1. **First person, "I."** Elite reports are first-person dominant (present in 60 of 74). "I found",
   "I confirmed", "I did not build a scenario where". Use "we" only when the work genuinely had more
   than one author. This aligns with `vulnerability-report-writing`'s existing voice guidance.

2. **Contractions, at a natural rate.** 57% of the corpus uses them. "it's", "doesn't", "I've",
   "here's". A report with zero contractions reads stiff and over-groomed. Do not force them either;
   match how you would actually talk through the bug.

3. **Sentence-length variance is the signal.** Real reports swing from one-word lines ("6. Bingo!",
   "Watch calc pop.") to sixty-word discovery sentences. Break your run-ons. Drop in a short blunt
   sentence for rhythm. Uniform medium-length sentences are the single most legible LLM cadence.

4. **Assert bluntly; hedge only real uncertainty; cap honestly.** State what you proved in absolutes
   ("the request still reaches the ENDPOINT stage"). Reserve hedging for things you genuinely did not
   confirm, and when you did not reach full impact, say exactly where you stopped. Honest capping is
   a human marker and a credibility marker at once. Never stack qualifiers ("could potentially
   possibly").

5. **Dash discipline (read this one carefully).** The corpus contains zero typographic em-dashes
   across all 74 reports, so `—` is out. But the fix is NOT to replace every em-dash with `--`. A
   dash on every aside is its own AI tell regardless of the glyph (the humanizer catalog flags "em/en
   dash *overuse*", not dashes as such). Reduce dashes overall. Turn most asides into a separate
   sentence, a comma clause, parentheses, or a colon. A single spaced dash now and then is fine; a
   dash as your default aside device is not. Vary the punctuation.

6. **Signpost with headers, not narration.** Section headers (`## Impact`, `## Steps to reproduce`)
   are human and ubiquitous. Narrative signposting ("Let's walk through the following", "Here's what's
   happening") is the tell. Start each section with content, not an announcement of the content.

7. **A plain open and close.** Many strong reports open with a short greeting to the named team ("Hi
   Netflix team,") and close with a plain offer to help ("Happy to retest once you've had a look.").
   Keep both minimal and real. Sign with your actual handle.

## Stop over-correcting: debunked heuristics

These popular "AI-avoidance" rules are contradicted by elite real reports. Following them makes prose
read *more* synthetic, not less. The parent skill's AI-tells section states some of these as bans;
this section supersedes them, on corpus evidence.

- **"Avoid leverage/utilize."** Debunked. A top RCE report uses it: "can be leverage to gain remote
  code execution" (@mehqq, #322935). Do not strip normal technical vocabulary.
- **"No rule-of-three lists."** Debunked. Three-item enumerations are a normal way to state three
  real preconditions or capabilities (@lauritz's three numbered root-cause conditions, #1342088).
  Only *padding* to three for cadence is a tell; three real things are three real things.
- **"Avoid contractions."** Debunked (57% of corpus). See rule 2.
- **"No first person."** Debunked (first person in 60/74). See rule 1.
- **"Uniform sentence length" / heavy proofreading into evenness.** Debunked. Variance is the human
  signal. See rule 3.
- **"Never use a dash."** Half-true and mis-stated. The `—` glyph is out, but the human pattern keeps
  the dash *function* at a low rate. See rule 5.

## Anti-tells that are real (remove these)

From the humanizer catalog (`github.com/blader/humanizer`), filtered to what actually applies to a
technical vulnerability report and cross-checked against the corpus. A report is closer to an incident
report than to marketing copy; the CVSS and impact reasoning already carry the argument, so the prose
should not work harder than the facts.

- **Significance inflation / promotional framing.** "a pivotal weakness", "a critical juncture",
  "breathtaking". State the mechanism plainly.
- **Copula avoidance.** "serves as", "boasts", "features" in place of "is"/"has".
- **Negative parallelism.** "not just X, it's Y" constructions.
- **Synonym cycling.** Naming the same function or mechanism three different ways in a paragraph
  instead of reusing one term. In a technical report, reuse the exact identifier every time.
- **Hedging stacks and filler.** "could potentially possibly"; "in order to" for "to"; "due to the
  fact that" for "because".
- **AI-vocabulary filler.** "leverage" as a noun-phrase crutch, "landscape", "testament",
  "showcasing", "delve".
- **Signposting announcements and chatbot sign-offs.** "Let's dive in"; "I hope this helps! Let me
  know if...".
- **Formatting tells.** Curly quotes (use straight), Title Case Headings, boldface on every acronym,
  inline-header repetition ("**Performance:** Performance improved").

Do the scan twice. The first pass catches the obvious instances and misses the rest.

## The honesty line (do not fake your way human)

The corpus also shows markers that read human precisely because they are *true*: left-in typos,
`:)` emoticons, "grab a coffee while you wait" asides, raw affect about a bounty, your own named test
accounts and testing dates. These are real artifacts of a real person doing real work.

Do not manufacture them. A planted typo, a bolted-on emoji, or a staged emotional reaction reads as
off, and it is dishonest in a report whose entire value is that a triager can trust it. This harness
scores rigor, and the platform's own Signal metric scores accuracy. So:

- **Apply freely (register levers):** first person, contractions, sentence variance, blunt assertion,
  honest capping, dash discipline, header-signposting, a plain greeting and sign-off. None of these
  fabricate anything.
- **Only if genuinely yours (authentic markers):** an emoticon, a real aside, a real test account, a
  real external writeup link, a candid line about the bounty. If it is real, keep it. If it is not,
  do not invent it.

## Workflow

1. Finish the report (facts, evidence, severity) under the other two reporting skills.
2. Read `references/gold-exemplars.md` for the target voice of each section.
3. Apply the calibrated rules above, section by section. Cut dashes and even out nothing; add variety.
4. Run the anti-tells scan twice.
5. Reread the literal, final, in-the-form text once more, as its own step (per
   `vulnerability-report-writing`'s "proofread the actual submission").

## References

- `references/gold-exemplars.md`: one real "write toward this" excerpt per report section.
- `references/voice-samples.md`: real openers, sign-offs, asides, blunt lines, and dash handling,
  grouped by device.
- `references/anti-tells.md`: the remove-these list and the do-not-over-correct list, with the corpus
  distribution stats.
- Full evidence base: `../research/hackerone-genuine-human-corpus.md`,
  `../research/hackerone-humanization-ruleset.md`.

## Worked example (dash discipline)

From a real rewrite of the Netflix Zuul report in this repo. First attempt over-applied the dash fix
and put 21 `--` into one report, which yells AI as loudly as `—` would. The corpus-correct version
carries roughly zero.

- Over-corrected: "Separately, `ZuulEndPointRunner` -- the class that actually resolves and invokes
  the `ENDPOINT` filter, which in production is `ProxyEndpoint`, the thing that forwards the request
  to the backend -- guards only on the other flag:"
- Human: "Separately, there is `ZuulEndPointRunner`. That is the class that actually resolves and
  invokes the `ENDPOINT` filter (in production, `ProxyEndpoint`, which forwards the request to the
  backend), and it guards only on the other flag:"

Same facts. One long dash-bracketed aside became a short declarative sentence plus a parenthetical.
That is the whole move: variety over device.
