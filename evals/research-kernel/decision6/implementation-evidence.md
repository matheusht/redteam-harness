# Decision 0006 implementation evidence

Date: 2026-07-13. All target-facing work was prohibited; every exercised fixture was inert and local.
Terra reviews were fresh `--no-session --no-tools` runs and remained outside the repository under
`/tmp`. Terra was treated as a static reviewer, never as an oracle or authority source.

| Slice | Binary closure evidence | Cold Terra disposition |
|---|---|---|
| 0 | Frozen corpus, old baseline, measurement contract, stage map, and source identity validate byte-deterministically. | PASS |
| A | Every live public command/event is classified; unknown command/event/variant fails closed; broker provenance and precreation Zone-2 checks pass. | Two independent PASS |
| B | Agent producers use generic local broker provenance; operator labels cannot upgrade capability; reviewer identity uses scope-bound SSH signatures. | Two independent PASS |
| C | Collector record is immutable and separate from exact operator review; repeated FD-bound source/secret scans and stale-preflight rejection pass. | PASS after blocker/high corrections |
| D | Immutable action bytes, all request states, exact digest/lane/executor/session/time/scope/environment binding, one-use effects, lane continuation, supersession, and prefix-safe repair pass. | Two independent PASS |
| E | Signed canonical `record-review` and async `revise-finding` subprocess paths preserve adjudication/filing separation and recover after a precommitted crash boundary. | PASS |
| F | Identity forgery, gate reclassification, secret leakage, stale environment, scope drift, Zone-2 precreation, deterministic reduction, signature forgery, and subprocess review/finding tests pass. | PASS |
| G | Closed generic/Claude adapters, byte-deterministic export, advisory linkage coverage, null-not-zero, forbidden capture, real-world tiering, lane overlap, and no-influence policy pass. | Two independent PASS |
| H | Interim bypass absent; gates/docs/template/CI/runbook updated; frozen old/new replay records gates held and complete coverage. | Two independent final PASS dispositions after corrections |

## Deterministic verification

- CI-equivalent script: `/tmp/decision6-decision6-release9-full.log` — all commands pass except
  the exact two recorded pre-existing `vulns/authentication-bypass` route failures.
- Current conformance: 373 checks, 2 failing; both are the unchanged OAuth routes above.
- `tools/run-engagement.py --self-test`: PASS.
- `tools/decision6_capabilities.py`: PASS.
- `tools/decision6_replay.py --self-test`: PASS.
- `tools/flow_telemetry.py --self-test`: PASS.
- Schema metaschema/local refs, compileall, frozen campaign input, and `git diff --check`: PASS.
- `frozen-replay-result.json`: old and new `gates_held=true`; required-gate delta `0`; Notebook
  improper-stall delta `-3`; measured trace coverage `10/10` in each arm.
- Final independent cold audits: `/tmp/decision6-final-release9-a.md` and
  `/tmp/decision6-final-release9-b2.md` — PASS after all blocker/high corrections.

## Honest limitations

- Runtime observations are advisory and may be omitted or misreported; linkage and measured coverage
  expose this. Live exports cannot validate as `flow_evidence`.
- Local broker principal/session binding is not cryptographic protection against total same-UID host
  compromise. Independent reviewer identity is separately signature-bound.
- No target contact, Zone-2 artifact, filing, submission, deployment, migration apply, or Git push was
  performed.
