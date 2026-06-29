# Research Ingestion Backlog — 2026-06

This is the cross-track holding pen between research memos and harness behavior. A row is not a
finding and not build permission. It becomes durable only after fixture-first validation and the
normal conformance gates.

## Feedback Loop

1. **Hypothesis intake:** record the source track, citations, hypothesis, affected harness area, risk,
   validation path, stop condition, and whether a 5.5 subagent critic reviewed it. The critic may
   triage clarity and risk; it is not authority.
2. **Fixture before belief:** add a false-discovery trap, hermetic target, fake-model episode, or
   sanitized casebook row before any card behavior persists.
3. **Card/oracle change:** update cards only after the fixture shape is explicit.
4. **Mechanical validation:** run conformance, false-discovery scoring, hermetic self-tests, and
   payload/secret scans on touched files.
5. **Persistence:** promote only scrubbed patterns, cards, casebook rows, or memory after validation.

## Backlog Rows

| id | source | citations | hypothesis | affected harness area | risk | validation path | stop condition | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| d-01 | Track D | D1,D5,D6 | BOLA selectors can appear in path/query/header/body; integer enumeration is activation, and ID opacity is not a defense. | `pattern.client-supplied-selector-authz`, BOLA routing | false positives on public/ignored ids | Add `trap-idor-public-value-not-cross`; extend card activation/counterexamples. | Public/ignored values never confirm without victim canary. | implemented |
| d-02 | Track D | D5 | State-changing BOLA can be tested safely with inert effects on controlled foreign canary objects. | `bola.broken-object-level-authz`, hermetic API runner | accidental Zone-2/persistent proof | Add `api-bola-state-change`; require inert effect and positive/negative controls. | Bare 200/204 on mutation remains `needs_review`. | implemented |
| d-03 | Track D | D11,D12 | JWT claim-validation failures should route on wrong-audience and algorithm-confusion shapes. | `pattern.jwt-claim-validation`, hermetic API runner | signature-valid token overclaimed as authz bypass | Add JWT pattern and `api-jwt-claim-validation`. | Decoded/signature-valid token with no canary privilege is refuted. | implemented |
| d-04 | Track D | D2 | BOPLA needs property-level canaries for overfetch and mass assignment. | `pattern.bopla-property-authz`, hermetic API runner | echoed property mistaken for effective state | Add BOPLA pattern, FDR trap, and `api-bopla-property-authz`. | Echo-only property remains `needs_review`. | implemented |
| d-05 | Track D | D3,D9,D10 | SSRF redirect-follow needs a stand-in canary rule and must reject echo-only URL observations. | `pattern.ssrf-server-side-fetch`, hermetic API runner | unsafe internal probing or URL-reflection false positives | Add redirect-follow guidance, `trap-ssrf-echo-not-fetch`, and `api-ssrf-redirect-follow`. | No live metadata probing; echo/storage without fetch never confirms. | implemented |
| d-06 | Track D | D7,D14 | GraphQL introspection/global-id decoding is recon only; chained resolver access to a foreign canary is the proof. | hermetic API runner; future GraphQL pattern/card | introspection overclaimed as vuln | Add `trap-graphql-introspection-only` and `api-graphql-global-id`. | Introspection-only never confirms. | implemented |
| b-01 | Track B | B1,B2,B8 | GEPA reflection feedback must be assembled from broker events and mechanical adjudication, never researcher narration. | `tools/broker-feedback.py`, behavioral run artifacts | model self-report becomes optimizer authority | Add broker-feedback artifact and self-test where claimed success without broker confirmation yields no positive feedback. | No adjudication event, no positive feedback. | implemented |
| b-02 | Track B | B8 | Runtime evaluator gaming needs permanent fixtures: fabricated controls, visible overfit, nonexistent events, hidden/gold inference. | `fixtures/runtime-gaming/`, `tools/score-runtime-gaming.py`, conformance | runtime cheat increases coverage | Add corpus + scorer; conformance requires non-allow dispositions. | Every fixture blocks/probes and adds zero coverage. | implemented |
| b-03 | Track B | B2,B13,B14 | Campaigns need explicit reflection/train vs held-eval split, hash-pinned through frozen inputs. | `tools/check-campaign.py`, canonical behavioral manifest | train/held contamination or candidate edits held data | Add optional `autoresearch_splits` gate; frozen input paths are immutable; update canonical manifest. | Overlap, unknown split id, drift, or held touch blocks. | implemented |
| b-04 | Track B | B11 | Replay should report advisory verdict/cost variance while keeping 3/3 replay as the hard floor. | `tools/replay-candidate.py` | variance hidden or used as an unreviewed gate | Add `verdict_variance` and preserve downgrade-only semantics. | Variance is recorded and does not upgrade/probe/block beyond existing policy. | implemented |
| b-05 | Track B | B1,B7,B13 | Pareto-over-episodes is promising but must remain design-only until axes are evaluator-owned. | design note | candidate defines its own coverage niche | Add design with axes, risks, stop condition. | No selection logic shipped in this slice. | implemented |
