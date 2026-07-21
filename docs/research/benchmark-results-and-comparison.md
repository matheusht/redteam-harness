# Benchmark calibrations — our results, public baselines, and the Mythos comparison

> Where this harness stands on three public security/CTF benchmarks, and an honest answer to
> "how do we compare to the Mythos Preview model?" Our numbers are extracted from the engagement
> records (cited by file); external numbers carry source URLs. **Rigor rule: this doc separates
> what we can defend from what we cannot, and does not manufacture a comparison the public data
> won't support.**

---

## 1. Our results (source-grounded)

Methodology across all three: a single orchestrator + **fresh, never-contaminated per-benchmark
Hunter agents** (the flag is never shared into a Hunter's context), a **two-layer oracle gate**
(`signal-oracle` = mechanical exact flag-string match → `adjudication-oracle` = did the boundary
actually break), and **gray-box ground truth computed independently by the orchestrator** for
verification only (never shared to the Hunter). Concurrency is *target-parallelism across independent
boxes*, not multi-agent on one box. No specific model id is recorded — the roles are model-agnostic.

| Benchmark | In our scope | Attempted | Confirmed (oracle-gated) | Bounded / dry | Status |
|---|---|---|---|---|---|
| **XBOW / XBEN** (104 web CTF challenges) | all 104, all 25 tag categories | **104 / 104** | **~100** (99 distinct records) | 4 bounded · 0 dry | complete (~96%) |
| **Cybench** (40 pro CTF tasks) | Phase-1 = 18 Web+Crypto | **18 / 18** | **17** | 1 bounded · 0 dry | Phase-1 complete (~94%); Phase-2 deferred |
| **CVE-Bench** zero-day (40 real-world web CVEs) | all 40 proposed | **0 / 40** | **0** | — | **authorized-but-unexecuted (planning)** |

**XBOW** (`engagements/xbow-benchmarks/`): "104/104 benchmarks attempted, 100 confirmed findings
(F-001–F-100), 4 attempted-no-flag, 0 dry" (`progress.md:420`). The post-campaign integrity audit
reconciles the on-disk record to **99 distinct findings** — the `F-058` id is an *intentional
numbering gap*, not a missing finding (XBEN-058 itself is confirmed, recorded as F-054)
(`progress.md:463-465`). We cite ~100 confirmed / 104 attempted (~96%) and note the 99-record
reconciliation rather than paper over it.

**Cybench** (`engagements/cybench/`): "18/18 tasks attempted. 17 confirmed findings (F-001–F-017), 1
attempted-no-flag (randsubware, Expert difficulty), 0 dry" (`progress.md:11`). Scope was deliberately
split: **Phase-1 = the 18 Web+Crypto tasks** (11 live-Docker + 7 offline crypto); **Phase-2 = 13
Pwn/Rev/Forensics/Misc tasks, explicitly deferred and never attempted** (`scope.md:48-59`) — the same
13 that drive the binary-exploitation-tier research. (Also: 9 of the 40 upstream tasks are absent from
the benchmark's own repo, leaving 31 runnable.) The single miss (randsubware, Expert) is consistent
with Cybench's own published finding that models essentially never solve Expert-tier tasks without
subtask guidance (`progress.md:52`).

**CVE-Bench zero-day** (`engagements/cve-bench/`): scoped (black-box zero-day track — the agent gets
no CVE id and must recon/fingerprint/find the flaw), **but 0/40 run** — phase is recon/planning, the
`findings/` dir is empty, the prerequisite ground-truth recipes were never authored
(`progress.md:6-12`). **Documented as queued, not as a result** — reporting an unrun benchmark as a
result would be the exact reward-hack this harness refuses.

**Redaction status (verified before publishing):** the harness-authored records (findings/, evidence/,
reports, progress/scope) are clean — passwords are consistently redacted with explicit notes, and the
engagement's own audit found 0 credential-leak hits. Real test-keys/JWTs exist *only* inside the
gitignored `upstream/` vendored challenge clones (challenge-design artifacts), which are **not
published**.

## 2. Verified public baselines (for context)

- **Cybench** — 40 pro CTF tasks, 6 categories, from 4 competitions (`cybench.github.io`, Zhang et
  al.). Public **pass@1 unguided** leaderboard: Claude Opus 4.7 **47%**, Opus 4.6 **46%**, Grok 4.1
  **43%**, Opus 4.5 **39%**. Anthropic's Opus 4.6 system card reports **~100% pass@30**.
- **CVE-Bench** — 40 critical (CVSS ≥ 9.0) real-world web CVEs, 8 attack objectives (arXiv 2503.17332;
  `github.com/uiuc-kang-lab/cve-bench`). Paper abstract: the **SOTA agent framework resolves up to
  13%** of the vulnerabilities.
- **XBOW / XBEN** — 104 containerized web-exploitation CTF challenges (`github.com/xbow-engineering/
  validation-benchmarks`). This is XBOW's *own* validation suite. The one widely-cited absolute figure
  is **XBOW's own agent at 85% (85/104) in black-box mode** — the same 85% reached by the strongest of
  5 professional pentesters given 40 hours (the other four scored ≤59%). A third party (FireCompass)
  independently reports **96.15% (100/104) first-attempt / 104/104 with bounded retry** using a single
  frontier model + router (explicitly *not* a Mythos-class model). **No cross-model Mythos XBEN number
  exists.**

## 3. The Mythos comparison — the honest answer

**Mythos Preview is real:** an unreleased/preview Anthropic frontier model disclosed ~April 2026 for
its cyber-offense capability and channeled to vetted partners ("Project Glasswing"), not released
generally. Corroborated independently by Anthropic's Frontier Red Team
(`anthropic.com/research/mythos-preview`), UK AISI (`aisi.gov.uk`), XBOW
(`xbow.com/blog/mythos-offensive-security-xbow-evaluation`), and Epoch AI — all treat the gains as
real, strongest in exploit development.

**But a like-for-like Mythos-vs-us comparison on these three benchmarks cannot be honestly built from
public data:**
- **Cybench:** no primary Mythos number. The widely-repeated "100% pass@1 on Cybench" traces only to
  SEO content-farm sites — it is **absent from Anthropic's primary red-team disclosure**, which speaks
  only qualitatively ("saturating nearly all of our existing benchmarks"). Treat it as unconfirmed.
- **CVE-Bench:** **no Mythos number exists anywhere credible.**
- **XBEN:** **no Mythos absolute solve rate exists.** XBOW published Mythos only as *relative* deltas
  (42% fewer false negatives than Opus 4.6, 55% fewer with source access, in an 80-action budget). The
  circulated "85/104 on XBEN" is **XBOW's own agent, not Mythos** (see §2) — a common conflation.

Mythos's *actual* published cyber scores are on **different** benchmarks: **CyberGym 83.1%**,
**ExploitBench ~78%**, and ExploitGym — plus custom internal disclosures (an OSS-Fuzz corpus run; a
Firefox 147 exploit-dev harness — 181 working exploits vs Opus 4.6's ~2). None of these is XBEN,
Cybench, or CVE-Bench.

### The XBEN head-to-head, specifically (the one asked for)

| On XBEN (104 web CTF challenges) | Result | Metric / caveat |
|---|---|---|
| **Our harness** | ~100/104 confirmed (~96%), 0 dry | oracle-gated (exact-flag + adjudication), gray-box ground-truth verification, bounded-retry campaign |
| **XBOW's own agent** | 85/104 (85%) | fully autonomous, **black-box** (no ground-truth assist) |
| Best of 5 human pentesters (40h) | 85% | human baseline XBOW published |
| FireCompass (single frontier model + router) | 100/104 first-attempt, 104/104 bounded-retry | independent third party, not a Mythos-class model |
| **Mythos Preview** | **— (no XBEN number published)** | only relative deltas vs Opus 4.6 exist |

**Read this carefully, don't overclaim it.** Our ~96% is *not* a clean win over XBOW's 85%: XBOW's
agent runs **black-box with no ground-truth assist**, while our loop holds gray-box ground truth for
oracle verification and runs a bounded-retry campaign — arguably an easier setting. The honest takeaway
is that our oracle-confirmed coverage on XBEN is **in the same high band** as XBOW's own agent and the
FireCompass router result, and that a Mythos comparison on XBEN **cannot be made at all** because
Mythos has no published XBEN score.

## 4. Why even the baseline comparison must be caveated (do not overclaim)

Our high solve rates are **not** directly comparable to the public pass@1 leaderboards, for three
structural reasons — stating them is the point:

1. **Different metric.** Our "confirmed" = exact flag-string match **plus** an adjudication that the
   boundary genuinely broke, with the orchestrator holding **gray-box ground truth** for verification.
   The public leaderboards measure **unguided pass@1 flag capture**. These are different measurements,
   not the same number.
2. **Different task subset.** On Cybench we ran the **18 Web+Crypto tasks and deferred the harder 13
   Pwn/Rev/Forensics/Misc**; the public 46% is over **all 40**. Comparing our ~94% on the easier
   subset to 46% over the full set is apples-to-oranges. (XBEN is the fairer comparison — we ran all
   104 — but XBEN lacks a clean cross-model baseline.)
3. **Different attempt/assist posture.** Our loop is a bounded, oracle-gated, gray-box-verified
   campaign, not a single blind pass@1 shot.

**Bottom line:** we can honestly say the harness reached **oracle-confirmed solves on ~96% of XBEN
(104/104 attempted) and ~94% of the Cybench Web+Crypto subset (18/18)**, with **zero dry results and
every claim oracle-gated** — which is a strong *rigor* result on the surfaces we ran. We **cannot**
honestly claim to beat Opus 4.x or Mythos: the subset/metric/assist differences explain much of the
gap, CVE-Bench is unrun on our side, and no comparable Mythos numbers for these benchmarks exist
publicly. The defensible framing is "high oracle-confirmed coverage on our scoped subsets," not a
capability ranking against frontier models.

---

*Sources — external: `cybench.github.io`; `arxiv.org/abs/2503.17332`;
`github.com/uiuc-kang-lab/cve-bench`; `github.com/xbow-engineering/validation-benchmarks`;
`anthropic.com/research/mythos-preview` + `red.anthropic.com/2026/mythos-preview`; `aisi.gov.uk`;
`xbow.com/blog/mythos-offensive-security-xbow-evaluation`;
`bleepingcomputer.com/news/security/xbow-tests-anthropics-mythos-preview-for-offensive-security`;
`firecompass.com/blog-fable-5-mythos-offensive-security`; `helpnetsecurity.com` (Mythos CyberGym/OSS);
Epoch AI. The XBEN "85/104 = XBOW's agent, not Mythos" attribution is corroborated across the XBOW,
BleepingComputer, and FireCompass sources. Internal:
`engagements/{xbow-benchmarks,cybench,cve-bench}/{scope,progress}.md` +
`casebooks/case-2026-07-{xbow-ctf-calibration,cybench-ctf-corpus}/`.*
