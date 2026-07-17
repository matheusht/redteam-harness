---
id: reporting.hackerone-reports
name: HackerOne submission mechanics
description: >
  Platform-specific companion to `reporting.vulnerability-report-writing`. That skill is
  platform-agnostic writing craft; this one is what HackerOne's actual submission form does with
  your content — which fields exist, how they're split, what to put in each one, and the mechanics
  learned from walking a real report through a real HackerOne form (Vercel Open Source program,
  2026-07-07).
type: reporting
owasp: "—"
atlas: "—"
---

## Use this alongside, not instead of, the general skill

Write the report following `reporting.vulnerability-report-writing`'s canonical shape and worked
template first. This card is about mapping that content onto HackerOne's specific form fields, which
split things differently than the generic template assumes.

## The form's actual field split (observed, not assumed)

HackerOne's "new report" flow is not one big text box. Confirmed field structure, in order:

1. **Asset** — a searchable picker over the program's in-scope assets (repos, domains). Pick the
   exact one your affected files live in. Each option shows its own severity ceiling and bounty
   eligibility inline.
2. **Title** — short, one line, **hard-capped at 150 characters**. Confirmed by a real submission
   attempt (kube-aggregator engagement, 2026-07-08) where a title following the general skill's
   "component + vulnerability class" template ran to 177 characters and was rejected by the form. Count
   the actual title string before finalizing a report, don't estimate — a title packing in the full
   mechanism *and* the CVE-precedent class name *and* a parenthetical tends to overrun this quietly.
   Front-load component + core defect + impact class; move anything else (CVE-class callouts, extra
   mechanism detail) into the Summary, which has no such cap.
3. **Weakness** — a CWE picker (searchable dropdown). Pick the CWE that matches the actual root
   defect, not the closest-sounding name. A prototype-chain lookup bypassing an authorization check is
   CWE-863 (Incorrect Authorization), not automatically CWE-1321 (commonly labeled "Prototype
   Pollution") unless something is actually written to `Object.prototype` — read the CWE's own
   definition before picking it to avoid a technically-inaccurate label, even if it "sounds right."
4. **Description** — one large textarea. This is where the general skill's Summary, Vulnerability
   Details, Steps to Reproduce, Supporting Material/References, Novelty check, and Suggested Fix all
   go, as `##` sub-headers inside this single field. There is no separate field for most of those.
5. **Impact** — a genuinely separate textarea from Description. Do not blend them. Impact-specific
   content (the attacker scenario, the CVSS reasoning) goes here and only here.
6. **CVSS calculator** — a structured, metric-by-metric widget (this program uses CVSS 4.0), not free
   text. It computes the score from the vector you select. Work out your vector from the general
   skill's per-metric reasoning, enter it here, and read the actual computed number back before you
   write the severity sentence in Impact (see the general skill's "reconcile prose severity with the
   actual calculator output").
7. **Additional information** section, with two required fields:
   - **Affected version(s)** — free text, but the platform gives you its own format example
     ("Next.js 15.4" or "SWR 2.3.6-2.3.3"). Match that convention: `package version` pairs,
     comma-separated if there are several, pinned to the exact published version(s) you confirmed
     against, not a version range you're guessing might also be affected.
   - **Affected File** — one or more direct GitHub links to the exact file(s), ideally pinned to the
     commit hash you tested against with a `#Lxx` or `#Lxx-Lyy` line anchor, not just the file path.
     **This field supersedes anything you'd otherwise put in Supporting Material.** Do not also list
     the same GitHub links under Supporting Material/References inside Description — that's pure
     duplication once this dedicated field exists. Supporting Material should be left to the PoC
     artifact itself.
8. **Attachments** — drag-and-drop file upload (PoC zip goes here) plus an optional "Record a demo"
   button. For a pure backend/library logic bug with no UI, a captured, trimmed text log of the PoC
   output is stronger evidence than a video (see the general skill on textual over screenshot/video
   evidence) — skip the recording unless the bug has a visual/UI component that text genuinely can't
   convey.
9. **Review and Submit** — the platform states editing after submission is not possible. Treat this
   as the trigger for the "proofread the actual submission" step in the general skill, not optional.

## Verify GitHub links before submitting them

Line-anchored `#Lxx` links are trivial to get off by one. Before submitting: read the actual file at
the exact commit hash you're citing (not just from memory or an earlier pass) and confirm the line
number matches what you're describing. If you spot-check a link by fetching the rendered GitHub page
through an automated/AI tool, treat that as a weak signal only — page-summarization passes can
miscount rendered line numbers. The authoritative check is `git show <commit>:<path> | sed -n
'<N>p'`, or the direct raw file at that exact commit, not a re-rendered and re-summarized page.

## CVE requests: not part of this form

There is no CVE-request field anywhere in the submission flow. A CVE describes a validated (often
already-fixed) vulnerability, so asking for one before triage is premature by design. Submit first;
once the report is accepted, or once a fix is underway, raise the CVE ask directly in the report's own
conversation thread with the triager, not at submission time.

## Verify the CVSS version against the real form — do not assume it transfers across programs

The Vercel Open Source program's form used CVSS 4.0. The very next program worked in this harness,
Netflix's, uses CVSS 3.1 — a different program, a different version, discovered only because the
operator screenshotted their real calculator widget after a full CVSS 4.0 vector had already been
reasoned through and written into the report body. **Do not assume a CVSS version from a prior
engagement's precedent; confirm it against the actual live calculator widget on the real form before
reasoning through metrics**, since the two versions have different metric sets (4.0 splits impact
into Vulnerable-System and Subsequent-System groups plus an Attack Requirements metric; 3.1 has a
single impact triad plus a binary Scope metric) and a vector reasoned for one doesn't translate
mechanically to the other.

**CVSS 3.1's Scope:Changed formula is more front-loaded than intuition suggests.** Translating a
CVSS 4.0 vector that used SC:H/SI:H (Subsequent System) into 3.1 by moving to Scope:Changed with the
matching C:H/I:H does not land at a proportionally similar score — a real, worked example from this
harness: reasoning through a bug that scored "high" under CVSS 4.0 (SC:H/SI:H, with AT:P encoding a
real precondition 3.1 has no metric for) came out to 10.0, Critical, once mechanically translated to
3.1's S:C/C:H/I:H, because 3.1's Scope-Changed multiplier interacts much more aggressively with a
full C:H/I:H impact pair than 4.0's independent-metric model does. Do not trust an assumed
"in-between" value either: dropping Integrity to Low as a compromise, while keeping Scope:Changed,
still computed to 9.3 (still Critical) in that same worked example — Low is not a safe middle ground
once Scope:Changed and C:H are both already set. If translating a severity argument across CVSS
versions, hand-verify the arithmetic (or better, an independent reviewer's arithmetic) rather than
assuming metric-for-metric equivalence produces a proportional result.

## Ground severity in real disclosed comparable CVEs when metric definitions alone don't converge

For a bug class shaped like "a generic mechanism bypass where the specific protected resource/action
is unspecified" (a framework-level authz gap, a gateway bypass, a middleware defect) — the CVSS
metric definitions alone often don't settle whether Confidentiality/Integrity should be scored for
the worst case the mechanism *could* reach, or only for what was *directly demonstrated*. Real,
disclosed precedent for the exact same bug shape is genuinely split even among well-known projects:
in one worked example, a prior CVE against the very same project scored Integrity Low, a comparable
bug in a different but structurally similar framework (a generic middleware auth bypass) scored
Integrity High, and a third comparable (a path-normalization bypass) scored Integrity None. When
metric-definition reasoning alone doesn't converge, load `skills/oracles/severity-precedent-oracle.md`
(the `oracles.severity-precedent` card): find the finding's bug-class bucket, read the per-metric
convention (IN / CONTESTED / THIN) and the named discriminator for the contested metric, and cite the
closest CVEs the card lists. Match the convention rather than defending a novel scoring choice from
definitions alone, which is both more defensible to a triager and closer to what the platform's own
reviewers will likely expect. Depart from the convention only with an explicit argument grounded in the
card's shown distribution (e.g. "this is the boundary-crossing case the S:C minority covers, here is the
concrete pivot"). The card's CVSS 3.1 conventions are solid but its 4.0 pools are thin (NVD backlog), so
confirm the program's actual CVSS version first and never carry a 3.1 convention across into 4.0. Only
fall back to spawning a fresh precedent-research subagent (distinct from a regrade of the finding's
validity) if the class is thin or absent from the card.

## Platform-specific reputation mechanic worth knowing before you submit

HackerOne tracks a "Signal" score per researcher (accuracy of past reports), and a program may cap or
restrict further submissions if it drops below a threshold. This is a direct, structural reason the
persistence-and-rigor discipline this harness already runs on (don't inflate severity, don't overclaim
a chain that isn't closed, land negatives honestly) is not just good practice in the abstract, it is
the thing the platform itself is measuring. A single overclaimed report costs more than the time it
took to write it.
