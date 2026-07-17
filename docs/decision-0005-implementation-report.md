# Decision 0005 implementation and evidence report

> Decision 0006 is additive. It preserves every Decision-0005 truth, safety, filing, submission,
> memory, and closure boundary while replacing agent bookkeeping stalls with fail-closed Notebook
> capabilities and lane-local digest-bound authority. See
> [`decision-0006-agent-autonomous-record-kernel.md`](decision-0006-agent-autonomous-record-kernel.md).

Date: 2026-07-10  
Branch: `decision-0005/research-kernel`  
Decision: `docs/decisions/0005-reasoning-directed-evidence-constrained-research.md`

## Result and claim boundary

Mandatory Slices A–J are implemented. The implementation demonstrates **architecture/contract conformance** on synthetic, hermetic fixtures. It does **not** demonstrate historical reconstruction, regression parity, or improved real-world efficacy. No live or historical target was contacted during implementation.

The architecture is now strong at authority separation, provenance, deterministic resume, correction, and fail-closed reporting. Its operational effectiveness remains unqualified: the historical corpus is unresolved, artifact replay was not run, no blinded arm ran, and no prospective holdout is registered.

## Slice evidence

| Slice | Delivered authority / ambiguity removed | Commit |
| --- | --- | --- |
| A | Pinned Draft 2020-12 schemas, closed records, typed references, canonical validation | `bedc848` |
| B | Append-only hash-chained ledgers, locking/recovery, reducer, snapshots/views, scope drift | `016ff97` |
| C | Operator-only contiguous finding revisions and claim-bounded adjudication | `5bbb5a7` |
| D | Independent regrade/Pocinator contracts and explicit correction/escalation evidence | `6fd596e` |
| E | Revision-bound deterministic reports, operator acceptance/submission, migration base | `090468b` |
| F | Offline source/build/runtime preflight, cleanup debt, advisory Zone classification | `4fa2f5a` |
| G | Exactly-one terminal memory disposition and gated engagement closure | `c3cab7e` |
| H | Complete-funnel ordered telemetry, independent outcomes, null-safe costs/calibration | `09a498e` |
| I | Full-source migration inventory, immutable legacy artifacts, needs-review v3 reconstruction, bounded retrospective | `ee8e265` |
| J | Frozen-arm preregistration/readiness contracts, documentation, CI, final audit | current slice |

All new governed schemas are version 1 except attempt v2 and finding v3. Legacy `finding.schema.json` remains readable as `finding-v2-legacy`. Validation requires pinned `jsonschema==4.26.0` and fails closed when unavailable.

## Sections 3–20 requirement matrix

| Plan section | Implemented surface | Verification / rollback |
| --- | --- | --- |
| 3 Architectural boundaries | `engagement_records.py`, `engagement_state.py`, `run-engagement.py`; model semantics remain outside authority shell | state/self-tests; stop appends and preserve ledgers |
| 4 Authority map | typed event actors, operator-only filing/report/submission/memory/closure, independent reviews | injected model/operator-authority negative tests |
| 5 Record layout | canonical `events.jsonl`, `attempts.jsonl`, `artifacts.jsonl`; versioned records; derived snapshot/views | noncanonical/tail/tamper/orphan/rebuild tests |
| 6 Core schemas | closed versioned schemas in `schemas/`, pinned full validator, semantic/ref checks | minimum/rich/reject fixture suite and schema-ID/ref checks |
| 7 State/reducer | deterministic reduction, typed transitions, cross-ledger causal time, locks/recovery | resume, rollback, scope drift, collision, repair tests |
| 8 Hypothesis/persistence | candidate/material-hypothesis lifecycle, prior provenance, held/exhausted/reopen, exact cold-reviewed dry closure | funnel and post-dry/reopen negative tests |
| 9 Oracle/reviews | signal/adjudication/coverage/regrade/Pocinator/candidate-outcome roles remain distinct | independence, correction, escalation, reward-hack tests |
| 10 Views/reporting | hash-bound generated views; deterministic claim/proof reports; revision history; operator acceptance/submission | stale/tampered/orphan/render/binding tests |
| 11 Domain neutrality | free domain IDs, namespaced weakness identifiers, atomic mechanism/reachability/impact; no pack is an oracle | LLM and non-LLM finding fixtures; optional domain packs not required for core |
| 12 Safety/operations | signed scope, safe signal, advisory Zone, fresh Zone-2 event/cleanup, secret scans, credential-label restriction | preflight/artifact/cleanup/scope adversarial tests |
| 13 Slices A–J | phase commits, bounded Terra audit, full CI, push, Draft PR update per slice | commit/PR evidence below; rollback is additive stop/no rewrite |
| 14 Migration | full-file dry inventory/bundles; separate reviewed apply; immutable legacy artifacts; needs-review v3 reconstruction; unresolved reports | source-before/after equality, no-invented-attempt, alias/stale/redaction tests |
| 15 Test architecture | schema, semantic, lifecycle, crash/tamper, integration, frozen-campaign, historical and readiness fixtures | CI 31/31 plus I/J self-tests and 323/0 conformance |
| 16 Retrospective | three layers represented separately; historical matrix and offline report; blocked/not-run never imputed | 136,154-file deterministic inventory; replay/rerun explicitly not run |
| 17 Prospective A/B | full-tree arm freezes, common safety overlay, preregistration/study-evidence/readiness contracts | structurally `not_ready`; zero arm runs; no authorization transition |
| 18 Compatibility/rollback | legacy v2 adapter plus v3 kernel flag; preserve partial history; fail closed on version/reducer bugs | legacy fixtures, migration manifest, append-only rollback tests |
| 19 Required evidence | this report, per-slice commits/PR notes, known limitations, complexity/safety/claim accounting | Draft PR #21 and final audit |
| 20 Explicit deferrals | no scheduler, auto-promotion, DB/service, extra concurrency, bandit/UCB, universal ontology, permanent model assignment, or sealed evaluator service | repository inventory and non-authoritative readiness schema |

## Authority and trust boundary

- The signed-scope operator alone files finding revisions, accepts reports, records submissions, chooses memory disposition, closes engagements, and authors any Plane-1 promotion PR. Public CLI mutations carrying operator/migration authority require a fresh phrase on an interactive operator console; noninteractive model/tool calls fail with `operator_console_required`.
- Models direct semantic research but cannot adjudicate their own claims or mutate trusted state.
- Attempts and artifacts are immutable; findings are revisioned; events are append-only; views are derived.
- Claim, search, coverage, proof-review, report, environment, memory, and submission state remain separate.
- Root policy overrides engagement-local authorization. Zone-2 always requires fresh human confirmation and cleanup tracking.
- External models/tools, including Terra, are reviewers—not oracles.
- The operator account, local OS, signed scope, and engagement filesystem are the trusted computing base. Hash chains are tamper-evident commitments, not authentication against total host/filesystem compromise.

## Fixtures and tests

`fixtures/engagement-records/suite.json` contains minimum/rich and invalid closed-schema cases for the governed record families, plus semantic attacks covering unresolved references, fake confirmation, operator-prior-as-proof, contamination, drift, stale reports, review confusion, false `coverage_dry`, telemetry denominators, historical classification, retrospective claims, and A/B readiness.

Primary verification:

```text
python3 tools/run-engagement.py --self-test
python3 tools/migrate-decision5.py --self-test
python3 tools/evaluate-retrospective.py --self-test
python3 tools/prepare-ab-study.py --self-test
python3 tools/check-conformance.py
python3 -m py_compile tools/*.py
git diff --check
```

The full CI-equivalent command set passed after each completed slice. CI also runs the retrospective and A/B readiness self-tests. Conformance currently reports 323 checks and zero failures. The canonical behavioral campaign remains `behavioral-canonical-v3-2026-07-10`; revision 2 remains immutable historical evidence.

Each slice received bounded static adversarial review with `openai-codex/gpt-5.6-terra`, correction, regression testing, commit, push, and Draft PR evidence. Terra did not contact targets, rerun engagements, or adjudicate findings.

## Migration and retrospective result

The deterministic operator-local inventory covered 136,154 files across complete historical engagement trees. Every file was classified and hashed; all remain `needs_review`; zero attempts or controls were invented; source bytes were unchanged. Artifact/unknown files require a complete hash-bound `migration-artifact-review`; executable or `review_required` entries additionally require fresh escalation-confirmation and cleanup references enforced by artifact registration. Recognized legacy finding records can be proposed as revision-1 v3 `needs_review` records bound only to their immutable source artifact, with scope, environment, attempts, controls, replay, and adjudication explicitly missing. Reports are preserved as artifacts and remain unresolved when destination authority is unavailable.

Artifact replay: `not_run`.  
Blinded historical rerun: `not_run`.  
Exact resume from approved migrated ledgers: `not_run`.  
Prospective release qualification: `not_qualified`.

## Prospective A/B readiness

`evals/research-kernel/ab-readiness/` freezes:

- staged baseline at commit `34351f0`;
- Decision-0005 A–I kernel at commit `ee8e265`;
- a common safety overlay for both arms.

Readiness is `not_ready`: model/provider, budgets, pilot variance, sample size, eligible uncontaminated holdouts, signed hermetic environments, sealed judge packet, independent panel, and tie rule are absent. Historical Decision-0005 cases are regression-only and excluded from efficacy holdouts. No arm ran and no result was fabricated.

## Complexity and rollback

Added complexity is limited to versioned JSON Schemas, append-only JSONL ledgers, deterministic Python reducers/adapters, and offline evaluation files. No database, daemon, service, scheduler, generic case abstraction, concurrency controller, bandit, or automatic promotion path was added.

Rollback stops new v1-kernel appends, preserves ledgers/artifacts, and records a blocker/compatibility note. It never rewrites or deletes history.

## Safety, secrets, and unresolved work

Synthetic tests used temporary engagements and inert local Git/runtime/package fixtures. Secret-shaped artifacts, metadata, argv, and memory promotions fail closed; credential values are not represented. No deployment, filing, target contact, Zone-2 creation, or Plane-1 promotion occurred.

Explicit Section-20 deferrals remain deferred. Future artifact replay or A/B execution requires fresh scope and operator gates. `autonomous_gap_closure_count` remains unchanged: Decision 0004's independent criteria have not been satisfied.
