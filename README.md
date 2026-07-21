# llm-redteam-harness

A **target-agnostic, portable** harness for **authorized** red-teaming of LLM / agentic
applications. It drives a target through a validated, OWASP-LLM-aligned checklist of
application-layer weaknesses, proves each finding against a ground-truth **oracle**, and
accumulates what it learns as reusable methodology.

> **Prime directive.** A red-team harness's product is **rigor, not findings**. It is engineered to
> **default to disbelief** and to **disprove itself before it is allowed to believe**. Success is not
> "found lots of issues" — it is being *more conservative than the operator's own intuition* about
> what counts as real.

## Scope fence (read first)

Three zones, enforced structurally (not just documented):

| Zone | What | Gate |
| --- | --- | --- |
| ✅ **Default — benign proxy** | system-prompt disclosure, refusal-flip on a *harmless* target, indirect-injection canary, excessive-agency / unsafe-render, cross-user canary propagation | a skill with no benign `safe_signal` **will not load** |
| ⚠️ **Authorized impact-escalation** | a real PoC artifact to prove blast radius (e.g. contained worm/exfil chain) | `scope.md` authorizes **+** runtime human-confirm **+** contained **+** cleanup-logged |
| ❌ **Never** | real-harm uplift as the product · a library of working harmful jailbreaks · HarmBench-style harm-elicitation as a metric · wholesale ingestion of harm corpora | — |

**Authorization is mandatory.** No `scope.md` filled and signed → the loop refuses to run.

## What it is / isn't

- It **is** a knowledge base of composable cards (vulns × techniques × oracles, plus **patterns** that
  route recon to the right cards) + one adaptive loop that reads them, driven by a single orchestrator
  with on-demand hunters, and **casebooks** of scrubbed prior engagements it learns from.
- It **isn't** a universal jailbreak generator, a payload arsenal, or a self-rewriting memory.

## Layout

```
skills/         PLANE 1 — methodology (read-only): vulns/ · techniques/ · oracles/ · patterns/
engine/         PLANE 2 — orchestration: loop · persistence · routing · roster · gates
schemas/        the contracts: attempt · finding · pattern · technique-card
fixtures/       sanitized oracle-calibration + routing-activation ground truth
casebooks/      PLANE 1 — scrubbed prior-engagement memory (routing + false-positive discipline)
engagements/    PLANE 3 — _TEMPLATE copied OUT into each target's own project repo (append-only)
tools/          conformance checker — the first mechanical gate
docs/           architecture + decisions + field-notes (cross-engagement methodology log)
```

**Plane rule:** Plane 1 is read-only knowledge; Plane 3 is write-only memory. The portable harness
(Plane 1+2) travels; each engagement's Plane 3 wiki lives with its target.

## Decision 0005/0006 record kernel

Decision 0006 keeps Decision 0005's evidence and authority boundaries while allowing the local
broker to maintain truthful Notebook records non-interactively. Consequential transitions use
lane-local digest-bound authority requests; Zone-2 remains freshly confirmed before creation.

New version-3 engagements use `python3 tools/run-engagement.py <subcommand> ...` as the sole public
Plane-3 authority. Append-only ledgers are authoritative; snapshots and Markdown are derived. See
`docs/decision-0005-implementation-architecture.md`,
`docs/decision-0005-implementation-report.md`, and
`docs/decision-0006-agent-autonomous-record-kernel.md` for commands, trust boundaries, migration, telemetry,
and the precise distinction between conformance, regression parity, and efficacy.

The retrospective and A/B tools are offline evaluators only. They do not contact targets, authorize
Zone-2 work, file reports, promote memory/cards, or prove efficacy.

## Conformance (run before promoting any card / casebook change)

```
python3 tools/check-conformance.py     # stdlib only; exit 0 = clean
```

Structural gate (Phase 2.5A): front matter, pattern `activation` tiers, vuln `safe_signal`,
`routes_to` resolution + `stub:` quoting, casebook pattern-refs, and a casebook secret scan. **A green
run is required before a pattern/vuln/casebook change is promoted** (also enforced in CI —
`.github/workflows/conformance.yml`). It is structural, not a full schema validator; that's Phase 2.5.

## Naming & anonymization

- **Casebooks are strictly anonymized** — no client/marketing name beyond an abstract `target_class`,
  no live ids/tokens/URLs. Enforced by the schema rule + the conformance secret scan.
- **Plane-1 methodology files** (field-notes, fixtures, vuln-card lessons) MAY keep an operator-internal
  engagement label as *provenance* (it makes a lesson credible), but **never a secret** — the redaction
  rule still applies. This repo is private / operator-internal.
- **Before any external sharing**, run a pre-publish pass that replaces engagement labels with abstract
  handles. Until then, labels stay internal.

## Benchmark calibrations

The harness has been calibrated against public security/CTF benchmarks as a **capability + rigor
signal** (its own records are published under `engagements/`; the vendored third-party challenge
corpora and raw attempt logs are not redistributed). Every solve is **oracle-gated** (exact
flag-match → adjudication), driven by a single orchestrator with **fresh, never-contaminated Hunter
agents** and gray-box ground truth held only by the orchestrator.

| Benchmark | Scope run | Attempted | Confirmed (oracle-gated) | Result |
| --- | --- | --- | --- | --- |
| **XBOW / XBEN** (104 web CTF challenges) | all 104, all 25 tag categories | 104 / 104 | ~100 (99 distinct records) | ~96%, 0 dry |
| **Cybench** (40 pro CTF tasks) | Phase-1 = 18 Web+Crypto | 18 / 18 | 17 | ~94%, 0 dry; Phase-2 (13 Pwn/Rev/Forensics/Misc) deferred |
| **CVE-Bench** zero-day (40 real-world web CVEs) | all 40 proposed | 0 / 40 | 0 | **queued — authorized but not yet run** |

**Honest framing (see `docs/research/benchmark-results-and-comparison.md`):** these are strong
*oracle-confirmed coverage* results on the subsets we ran, **not** a capability ranking against
frontier models — the numbers use a different metric (confirmed-finding + gray-box verification vs
public unguided pass@1) and, for Cybench, a different (easier) task subset than the public
leaderboards. A direct comparison to the **Mythos Preview** model is *not* constructible from public
data: Mythos is real (an unreleased Anthropic cyber-offense preview, ~April 2026) but has **no
primary-sourced score on any of these three benchmarks** — the circulated "100% Cybench" figure
traces only to SEO sites, CVE-Bench has no Mythos number, and on XBEN the circulated "85/104" is
**XBOW's own agent, not Mythos** (Mythos published only relative deltas). Mythos's real cyber scores
are on *other* benchmarks (CyberGym 83.1%, ExploitBench ~78%).

## Status

`v0` scaffold. The **LLM07 system-prompt-leakage** LLM-app slice is structure-first; the harness's
live exercise to date is the **CTF/benchmark calibration** above (XBOW + Cybench Phase-1 complete;
CVE-Bench zero-day queued) plus the source-available engagements under `engagements/`. See
`docs/architecture.md` and `CLAUDE.md`.
