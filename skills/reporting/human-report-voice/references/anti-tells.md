# Anti-tells and over-corrections

Two lists and a stats table. The first list is what to remove. The second is what NOT to "fix",
because the fix is itself a tell. Sources: `github.com/blader/humanizer` (catalog), filtered to what
applies to a technical vulnerability report, and cross-checked against the 74-report corpus.

## Remove these (real AI tells in this genre)

- **Significance inflation / promotional framing.** "a pivotal weakness", "a critical juncture",
  "breathtaking", "nestled". State the mechanism plainly.
- **Copula avoidance.** "serves as", "boasts", "features" where "is" or "has" is meant.
- **Negative parallelism / tailing negations.** "not just X, it's Y".
- **Synonym cycling.** Naming one function or mechanism three different ways across a paragraph.
  In a technical report, reuse the exact identifier every time.
- **Hedging stacks.** "could potentially possibly". Hedge once, only for real uncertainty.
- **Filler phrases.** "in order to" (use "to"), "due to the fact that" (use "because").
- **AI-vocabulary filler.** "landscape", "testament", "showcasing", "delve", "leverage" as a
  noun-crutch.
- **Signposting announcements.** "Let's dive in", "Here's what you need to know". Start with content.
- **Chatbot artifacts / sycophancy.** "I hope this helps! Let me know if...", "Great question!".
- **Cutoff disclaimers.** "While details are limited in available sources...".
- **Formatting tells.** Curly quotes (use straight `'` `"`), Title Case Headings, boldface on every
  acronym, inline-header repetition ("**Performance:** Performance improved"), emoji as decoration.
- **Em/en dash overuse.** The corpus has zero `—`, and even `--`/`–` appear rarely. A dash on every
  aside is a tell regardless of glyph. Reduce and vary. (Humanizer flags "overuse", not dashes as
  such.)
- **Uniform sentence length.** Even, medium-length sentences throughout is the most legible LLM
  cadence. Introduce variance.

## Do NOT "fix" these (over-corrections that read more synthetic)

Elite real reports do all of the following. Suppressing them is what makes over-groomed AI prose
obvious. This list supersedes the blanket bans in `reporting.vulnerability-report-writing`'s AI-tells
section, on corpus evidence.

- **First person "I".** Present in 60 of 74 reports. Keep it.
- **Contractions.** In 42 of 74 (57%). Keep them at a natural rate.
- **The word "leverage" and similar normal technical vocabulary.** Used in top reports ("can be
  leverage to gain remote code execution", @mehqq #322935).
- **Three-item lists that state three real things.** Normal for preconditions and capabilities. Only
  padding-to-three for cadence is a tell.
- **Blunt, unhedged assertion of what you proved.** "steal ALL collateral", "the request still
  reaches the ENDPOINT stage". Confidence about demonstrated facts is human and credible.
- **A dash, used rarely.** The function is fine at low frequency; only the glyph `—` and the overuse
  are out.
- **Header signposting.** `## Impact`, `## False Starts`, `## Conclusion` are everywhere in the corpus
  and are human. Only narrative signposting is a tell.

## Corpus distribution (n = 74 reports, 70 authors)

| Dimension | Value | Share |
|---|---|---|
| First person "I" dominant | 48 | 65% |
| Mixed (I + impersonal/we) | 12 | 16% |
| Impersonal only | 11 | 15% |
| "We" only (co-authored) | 3 | 4% |
| Reports containing contractions | 42 | 57% |
| Reports containing a typographic em-dash `—` | 0 | 0% |

First person appears in 60 of 74 (81%). A purely impersonal register is a 15% minority. The em-dash
count is exactly zero, the single most consistent signal in the corpus. These hold across the full
class and difficulty range (0-click ATO, memory-corruption RCE, SSTI, SSRF-to-metadata, IDOR, request
smuggling, smart-contract, sandbox chains) and across 70 distinct authors, so they are conventions,
not one writer's habit.

## Two-pass discipline

Scan twice. The first pass catches the loud instances (a stray `—`, a "Let's dive in", a promotional
adjective) and reliably misses the quieter ones (synonym cycling, uniform cadence, a hedging stack).
The second pass is where the report stops reading assembled.
