# Evidence-backed source target and critical-asset ranking

## Eligibility gate

A target is rankable only when all are true:

- corresponding source repository/local tree is identified;
- supplied program/customer authorization covers source review;
- an exact eligible branch, tag, release, or commit can be frozen;
- restrictions permit the planned static/local analysis;
- no live-target interaction is required to begin;
- exclusions and ownership boundaries are available or explicitly marked blocking.

Do not convert missing authorization into a low score. Mark the target `blocked`.

## Repository priority score

Score each factor 0–5 only from cited evidence. Use `unknown` when unsupported and report score coverage. Normalize only over measured weights; never treat unknown as zero.

| Factor | Weight | Evidence examples |
| --- | ---: | --- |
| Security blast radius | 20 | root privilege, consensus/state authority, gateway, package/update trust |
| Attacker-controlled reachability | 20 | unauthenticated parser/input, tenant-controlled config, network protocol entry |
| Privilege/trust-boundary density | 15 | authn/authz transitions, broker/worker split, sandbox escape boundary |
| Impact ceiling in policy | 10 | eligible RCE, authz bypass, funds/state compromise; cite policy |
| Source/build reproducibility | 10 | pinned release, hermetic tests, local integration path |
| Complex state/control flow | 10 | async routing, parsers, callback chains, distributed state transitions |
| Historical weakness relevance | 5 | same component/class precedent at a different fixed revision, not bare CVE matching |
| Research novelty/coverage gap | 5 | high-value surface not already exhaustively reviewed in supplied records |
| Verification feasibility | 5 | real local build and faithful observable oracle available |

Apply explicit penalties separately:

- excluded class or component: reject;
- unsupported/unreleased revision: block;
- requires production/cross-user testing: reject for this source-only workflow;
- dependency CVE without target-specific path: no positive score;
- source unavailable or generated-only mirror: reject;
- impossible faithful local verification: flag as major limitation, not proof of safety.

## Critical asset decomposition

Inside the selected repository, build an asset map before candidate hunting. Prefer concrete symbols and boundaries over generic vulnerability labels.

1. Enumerate externally influenced entry points.
2. Trace identity, privilege, and tenancy transitions.
3. Identify high-consequence sinks and state transitions.
4. Identify parser/serializer and protocol normalization boundaries.
5. Identify plugin/update/template/code-loading paths.
6. Identify process, filesystem, network, crypto, money, and consensus authority.
7. Map local integration tests or real-build observables for each asset.

For each asset record:

```text
asset_id
path and symbol
purpose
attacker-controlled sources
trust boundaries crossed
candidate sinks/state transitions
plausible impact ceiling
release/scope eligibility
faithful local verification route
known exclusions/controls
ranking evidence
confidence: high | medium | low
```

## Candidate-retirement economics

Rules, regexes, SAST queries, sink lists, and cheap classifiers may widen or prioritize the corpus. They may not retire a candidate alone.

A candidate can leave the funnel only by:

- evidence-backed refutation with applicable controls and independent review;
- confirmed/chained adjudication with independent proof review;
- explicit defer/blocked state naming missing evidence;
- bounded coverage closure after every material candidate has a disposition.

Do not use a fixed number of votes as proof. Independence, evidence quality, and control-flow fidelity matter more than majority count. A human review remains required where root policy says so.
