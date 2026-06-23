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
engine/         PLANE 2 — orchestration: loop · routing · roster · gates
schemas/        the contracts: attempt · finding · pattern · technique-card
fixtures/       sanitized oracle-calibration + routing-activation ground truth
casebooks/      PLANE 1 — scrubbed prior-engagement memory (routing + false-positive discipline)
engagements/    PLANE 3 — _TEMPLATE copied OUT into each target's own project repo (append-only)
tools/          conformance checker — the first mechanical gate
docs/           architecture + decisions + field-notes (cross-engagement methodology log)
```

**Plane rule:** Plane 1 is read-only knowledge; Plane 3 is write-only memory. The portable harness
(Plane 1+2) travels; each engagement's Plane 3 wiki lives with its target.

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

## Status

`v0` scaffold — first vertical slice: **LLM07 system-prompt leakage** (structure only, no live run
yet). See `docs/architecture.md` and `CLAUDE.md`.
