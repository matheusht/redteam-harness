---
id: pocinator-oracle
type: oracle
description: Post-confirmation layer — does THIS specific PoC/package prove the exact claim we're about to report? (judgment, anti-reward-hacking)
---

# Pocinator oracle — "does this specific PoC actually prove the exact claim?"

The last adjudication layer before filing. Regrade asks whether the finding is real; this asks
whether the artifact standing in as evidence for it is faithful, sufficient, and scoped correctly.
Full doctrine, worked examples, and rationale: `engine/pocinator.md`. This card is the terse,
invocable version for an agent loading it by id mid-run.

## Required input: the claim tuple
Before applying any lens, extract (don't invent) this tuple from the finding/evidence records:

**target artifact/version · entrypoint · preconditions · mechanism · observable effect · negative
control · claimed impact/severity · package contents · run command/environment · expected observable
output**

If the tuple can't be extracted from existing records → `blocked`, immediately. Do not construct the
tuple yourself; that grades your own homework.

## Verdict set
`verified` · `needs_rework` · `claim_mismatch` · `reward_hacked` · `blocked`

- **`verified`** — proves the exact tuple, including any PoC-dependent severity claim.
- **`needs_rework`** — probably real, specific fixable gap named. Also the correct verdict when it's
  *unclear* whether something is `reward_hacked` — uncertainty is never itself grounds for that verdict.
- **`claim_mismatch`** — PoC is real and sound, proves something narrower/different than claimed.
- **`reward_hacked`** — a *definite, articulable* harness failure only (named mock dodging the real
  gate, traced emulator divergence, an assertion that structurally cannot fail). Not a hedge.
- **`blocked`** — genuinely can't decide (environment/artifact unavailable, tuple not extractable) —
  not a judgment on the PoC either way.

Any non-`verified` verdict routes back to Stage 4/4.25, never a silent kill. `claim_mismatch` routes
to severity/impact reasoning specifically, not to rebuilding the PoC. A *definite* `reward_hacked` on
a high-value finding earns a second independent pocinator pass before being treated as final.

## Lenses (apply what's relevant, not all of them mechanically)
1. **Real-artifact provenance** — actual published artifact/pinned commit, not a reimplementation.
2. **Public-entrypoint realism** — driven the way a real caller would, not a harness-only shortcut.
3. **Mock/stub justification** — for every mock: if this were real code, would the assertion still
   hold, or does the mock exist to dodge the real gate?
4. **Mechanism fidelity via negative control** — control diverges *through the claimed mechanism*,
   traced, not merely observed to differ.
5. **Observable effect, not a blind marker** — a real state change/response/artifact, not
   `exit 0` + a printed string. Even sink-instrumented automated checks aren't sufficient alone.
6. **Claim strength** — assertion matches report language exactly, for the PoC-dependent part of the
   claim only (broader CVSS/novelty precedent is out of scope here — that's the narrow
   CVSS-precedent-reviewer pattern, not a full `regrade-oracle` re-litigation).
7. **Clean-state reproducibility** — fresh checkout/extraction, not leftover dev-session state.
8. **Anomaly tracing** — any stray log/warning/stack trace traced to source, never hand-waved benign.
9. **Package hygiene** — review what would actually ship (re-extracted), no secrets/scratch files/
   internal records; no drift between working copy and packaged artifact.
10. **Self-attestation is not evidence** — re-derive independently; ideally a different context than
    whoever built the PoC.
11. **Optional differential** (when available) — patched version/fixed config/safe control strengthens
    confidence; not required, not every finding shape offers one.
12. **Counterfactual-novice framing** — ask explicitly: *where would a naive or reward-hacked
    verification stop and declare success here?* Sharper than "is this faithful?" alone.

## What this oracle is NOT for
Passing pocinator does not guarantee a report won't return as a duplicate — it verifies the PoC is
real and faithful to its claim, not that the finding is novel or undisclosed. Novelty is a separate,
upstream question.

## When required
Default-required for: any executable PoC/zip attached to a report, any high/critical candidate, any
model-built harness/emulator standing in for the real target, any finding whose severity claim
depends on what the PoC specifically demonstrates. Skippable only with an explicit operator note
recorded in the finding — never a silent skip.
