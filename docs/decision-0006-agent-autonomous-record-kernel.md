# Decision 0006 — the record kernel is the agent's notebook, not the operator's checkpoint

**Status:** proposed; interim experiment exists, but the design below is not yet implemented

**Relationship:** refines Decision 0005's authority boundary; does not weaken signed scope, independent adjudication, Zone-2, cleanup, reporting, submission, memory, or closure gates

**Origin:** operational friction observed during a source engagement; refined by two independent pre-implementation reviews of the autonomy and measurement design

## 1. Problem

Decision 0005 correctly prevents a model from becoming the operator merely by writing an operator role into a record. Its first public CLI implementation then applied the interactive operator-console check too broadly. Ordinary notebook operations such as collecting preflight facts, registering benign evidence, and appending attempts could require a synchronous TTY phrase even though they neither authorize an action nor accept a claim.

A non-interactive research agent therefore stopped for bookkeeping rather than for a consequential decision. Because attempts require an active environment reference, an operator-gated preflight could prevent the accountable notebook from being used at all.

The correction must not replace one false authority signal with another. In particular:

- an environment variable set by the same agent is a mode switch, not identity or attestation;
- a hash chain demonstrates append integrity relative to the observed filesystem, not truth, authorship, authorization, or semantic correctness;
- a clean automated secret scan is useful evidence, not proof that no secret exists;
- asynchronous human review may keep unrelated safe work moving, but the transition that depends on that review must remain blocked;
- a signed category authorization never replaces the fresh confirmation required before each Zone-2 artifact is created.

The desired outcome is high operational autonomy inside the evidence shell, not weaker authority boundaries.

The same run also exposed a measurement gap. Decision 0005 can derive complete candidate-funnel history and conservative cost totals, but it does not yet make agent-runtime flow legible enough to answer: which stage consumed active effort, which lane waited on authority, how many agent turns/tool calls were spent, where backtracking occurred, and whether record completeness improved. Without that layer, Decision 0006 could pass contracts yet still overstate that flow improved. The measurement addition must remain lightweight, agent-runtime-neutral, and non-authoritative.

## 2. Decision

### 2.1 Core rule

> Agents may autonomously create truthful notebook evidence and search state. They may not autonomously create human authorization, accept claim truth on their own work, grant escalation permission, accept reports, record external submissions, or cause real-world effects.

The public record command must classify an operation by capability, validate the true actor, and apply the narrowest applicable gate. It must not infer operator authority from a caller-provided label or from `HARNESS_AGENT_ATTESTED`.

### 2.2 Three human-gate tiers

`engine/gates.md` will encode the following table. The tiers classify interruption behavior; they do not collapse router, researcher, independent oracle, and operator into one role.

| Tier | Examples | Behavior |
| --- | --- | --- |
| **Notebook — agent-autonomous** | collect preflight facts; register Zone-0/Zone-1 artifacts; append attempts, observations, controls, replay results, candidates, hypotheses, and non-authority transitions; record immutable review proposals | Execute without TTY after schema, scope, capability, secret-shape, reference, environment, and hash-chain checks. Record the real actor and session/model/tool provenance. |
| **Authority — human, asynchronous** | initial scope signature; scope amendment; operator filing/acceptance of a finding revision; severity-rung review; report acceptance; submission authorization/recording; memory disposition; closure; ledger repair | Initial scope remains a global prerequisite. Later requests enter `pending_authority`; only the dependent transition waits. The orchestrator continues every unrelated, authorized, safe lane. Human approval is bound to the exact proposed action and immutable digest. |
| **Real-world — fresh live human confirmation** | creation of each Zone-2 PoC artifact; production/live-network contact; cross-user/account effects; destructive or persistent writes; use of real credentials/funds/sensitive data; publication, deployment, disclosure, or filing | Pause the exact lane before the action. Require action-specific scope, environment, containment, expiry, and cleanup references. If no other safe lane remains, the engagement pauses. Never approve retrospectively. |

“Async — never blocks the agent” therefore means **never blocks unrelated safe research**. It does not mean that the harness may execute an unapproved dependent action.

### 2.3 Autonomous notebook capability

Notebook autonomy is an allowlist, not a bypass around `_require_operator_console`.

Every autonomous write must carry:

- truthful actor role and stable actor/session identifier;
- provider/model/tool versions when applicable;
- active signed-scope hash;
- active environment reference where required;
- operation class (`notebook`);
- immutable source/artifact references and digests;
- automated validation and secret-scan results;
- no operator attestation fields unless an operator actually supplied them.

The reducer rejects an agent actor attempting any operator-only or real-world transition. Adding a new event type does not make it agent-autonomous until it is explicitly classified and tested.

Ordinary `register-artifact` autonomy applies only after the proposed bytes are classified Zone-0/Zone-1. Zone-2 is gated **before byte creation**, not merely before later registration.

### 2.4 Preflight collection is separate from operator review

Preflight becomes two distinguishable facts:

1. **Agent/source collector evidence:** observed Git/package/runtime identity, dirty tracked state, generated/untracked build state, runtime digest, reproduction metadata, cleanup state, and automated secret-scan result.
2. **Operator review, when required:** redaction acceptance, credential-sensitive context, unknown/review-required Zone classification, identity exception, or other authority judgment.

A complete, exact, clear-local, credential-free preflight may become usable for ordinary notebook work without a TTY. `needs_review`, `unknown`, identity drift, incomplete secret coverage, cleanup debt, or credential-sensitive context cannot be promoted by the collecting agent.

Generated build artifacts should be represented separately from tracked source drift so a reproducible build does not silently change the frozen source identity.

### 2.5 Claim judgment remains separated from operator acceptance

Research agents may propose findings and record supporting/refuting evidence. They may not self-confirm their own work.

An independent oracle/reviewer may record a claim-adjudication proposal only when the reducer verifies independence, committed evidence, controls, environment, chronology, and review-role contracts. One model simulating multiple graders is not independence.

Operator authority remains required to file/accept a finding revision for reporting. The intended sequence is:

```text
agent evidence and search state
  -> independent oracle/regrade/Pocinator records
  -> supported or refuted adjudication proposal
  -> pending operator finding action
  -> operator-filed revision
```

A pending operator finding action does not stop investigation of other candidates or continued chainability work within scope.

### 2.6 Scope and scope drift

The initial signed scope remains a blocking global gate. Later scope changes are immutable revisions, not silent edits or restoration that erases history.

If `scope.md` drifts:

- preserve the drifted bytes as an unattested draft or digest-bound event;
- retain the previously attested revision unchanged;
- block only work that depends on the proposed expansion;
- require operator re-attestation before activation;
- never rewrite the ledger or pretend the drift did not occur.

### 2.7 Minimal agent-runtime-neutral flow telemetry

Decision 0006 adds observability, not a second authority system. Reuse Decision 0005's candidate history, measured-cost fields, source hashes, and per-dimension coverage semantics. Do not add a database, daemon, scheduler, live dashboard, or agent-authored metrics checklist.

Use two inputs with unequal trust:

1. **Kernel-derived facts:** operation tier from the frozen capability matrix; event/attempt/review transitions; stage boundaries supported by committed records; authority-request intervals; backtracks/reopenings; reviewer interventions; record completeness; and existing measured costs. These are deterministically derived from append-only records.
2. **Optional runtime observations:** turns, model/tool calls, runtime timing, token counts, and cost supplied by a normalized agent-runtime adapter. These are advisory because the runtime or agent can omit or misreport them. They may never authorize an action, establish independence, alter claim truth, or qualify calibration.

The adapter contract is agent-neutral. Implement a generic normalized JSON envelope and a Claude Code adapter first because Claude Code is the primary runtime. Other agents can add adapters later without changing the kernel schema. Runtime-specific fields are optional, attributed by runtime name/version, and compared only within the same runtime or a frozen replay. No Pi-specific dependency belongs in the core design.

The minimum normalized runtime observation is:

```text
engagement_id, run_id, session_id, runtime_name, runtime_version
recorded_at, observation_kind(turn|model_call|tool_call|runtime_wait)
linked operation/candidate/hypothesis/attempt id when available
counts or durations only; tokens/cost nullable
```

Never capture prompts, model responses, tool arguments, command lines, environment values, file contents, credentials, or target payloads in runtime telemetry. Missing values remain `null` with `{records, measured}` coverage; absence of an observation is unknown, not zero.

The derived flow export remains separate from research calibration and contains only:

- source hashes and trace-coverage counts;
- per-stage operation counts and measured active/wall/blocked time;
- turns, model calls, tool calls, tokens, cost, and human-review time when measured;
- authority-request intervals and resolutions, with overlapping lane activity represented rather than flattened into a misleading global stall;
- backtrack/reopen and independent-review intervention counts derived from existing records;
- record-completeness counts;
- runtime identity and an explicit `flow_telemetry | flow_evidence` classification;
- policy flags forbidding automatic gate, routing, prompt, finding, or severity changes.

Do not add per-tool histograms, model leaderboards, cross-runtime averages, live productivity scores, or dashboards in this decision.

### 2.8 Measurement claim boundary and anti-Goodhart rule

The primary invariant is **gates held**, not speed. Required Authority and Real-world pauses are correct behavior and never count as bottlenecks to eliminate. “Improper stall” means only a Notebook operation blocked by a mechanism that the frozen capability matrix says it does not require.

Live engagement traces are observational and target-confounded. They can identify possible bottlenecks and regressions but cannot demonstrate that a model, stage, or workflow is more effective. A before/after flow claim requires the same frozen operation corpus replayed under the old and new gate regimes, stratified by runtime and checked by an independent reviewer. Missing trace coverage keeps the result `flow_telemetry`; only complete frozen replay evidence may become `flow_evidence`.

No metric may optimize or automatically modify the capability matrix. Number of findings, severity, shortest run, fewest human gates, or highest candidate conversion are not success metrics. Useful descriptive measures are time/cost to evidence-backed resolution, notebook improper-stall count, record completeness, reviewer corrections/rescues, and active versus dependency-blocked time—always reported alongside rigor regressions and missing-data coverage.

## 3. Planned `engine/gates.md` behavior

The gates document will distinguish global, lane-local, and asynchronous blocking explicitly:

| Operation | Gate | Continuation behavior |
| --- | --- | --- |
| Initial signed scope | Global authority | No research run before signature |
| Agent preflight collection | Notebook | Continue automatically if exact and clear-local |
| Append attempt/control | Notebook | Continue automatically with usable environment |
| Register benign evidence | Notebook | Continue automatically after pre-creation classification |
| Independent review proposal | Notebook/reviewer capability | Continue; cannot self-adjudicate or file |
| Scope amendment | Async authority | Existing-scope lanes continue; expanded lane waits |
| File finding revision | Async authority | Candidate waits; other research continues |
| Accept report / record submission | Async authority | External path waits; research continues |
| Create one Zone-2 artifact | Fresh live confirmation | Exact lane pauses before creation |
| Production/cross-user/destructive action | Fresh live confirmation or refusal | Exact lane pauses; scope ceilings still apply |
| Memory disposition / close | Async authority | Terminal transition waits; completed evidence is preserved |

This table is intended to remove bookkeeping stalls while making consequential boundaries easier to see and test.

## 4. Implementation plan

### Slice 0 — Freeze measurement contract and before-state

- Freeze the pre-Decision-0006 capability matrix, implementation identity, and a synthetic operation corpus that includes Notebook, Authority, and Real-world operations.
- Reuse Decision 0005 cost and coverage definitions rather than creating competing semantics.
- Define `gates_held` as the primary invariant and notebook improper stalls as the bounded flow defect.
- Specify the normalized agent-runtime envelope, separate derived flow export, missing-data behavior, secret-minimal field set, and a versioned stage-mapping table; unsupported stage attribution remains `unknown`.
- Record baseline replay output before changing gate behavior. Do not retain the unsafe interim bypass merely to gather live baseline data.

### Slice A — Freeze the capability matrix

- Enumerate every public CLI subcommand and engagement event.
- Assign allowed actor roles, tier, required evidence, and blocking scope.
- Fail closed for unclassified operations.
- Add explicit `pending_authority`, `approved`, `rejected`, `expired`, and `superseded` request states without collapsing claim/search/report/closure state.

### Slice B — Truthful actor attribution

- Add actor/session parameters to preflight and other notebook producers.
- Remove hardcoded operator provenance from agent-collected records.
- Bind scope authorization separately from authorship.
- Reject agent-supplied operator attestations and operator-role impersonation.

### Slice C — Split preflight collection and review

- Represent collector evidence and operator review separately.
- Separate tracked source drift from generated/untracked build outputs.
- Preserve existing fail-closed identity, cleanup, credential, advisory-Zone, and secret-shape behavior.
- Define exactly when clear-local notebook readiness can be derived automatically.

### Slice D — Async authority requests and flow continuation

- Add immutable authority-request records bound to the proposed action digest.
- Let the orchestrator continue unrelated authorized lanes while requests are pending.
- Prevent dependent state transitions until exact operator approval exists.
- Expire or supersede stale requests when scope, environment, evidence, or proposal bytes change.
- Do not add a scheduler or service; compose the existing event loop and reducer.

### Slice E — Canonical review and finding path

- Ensure public commands can atomically record reviews and propose finding revisions without ad hoc file writes.
- Preserve independent oracle, regrade, Pocinator, and operator filing separation.
- Keep report acceptance, submission, memory disposition, closure, and Plane-1 promotion operator-owned.

### Slice F — Adversarial and end-to-end tests

At minimum, prove:

- an agent can collect a clear-local preflight and append ordinary notebook records non-interactively;
- an agent cannot claim operator redaction review, scope amendment, finding filing, report acceptance, submission, memory disposition, closure, repair, or Zone-2 approval;
- changing an actor label or environment variable cannot upgrade capability;
- a researcher cannot self-adjudicate through a fabricated reviewer identity;
- pending authority blocks only the dependent transition while an unrelated safe candidate continues;
- Zone-2 is stopped before bytes are created and remains bound to one artifact, environment, scope, expiry, and cleanup obligation;
- scope drift is preserved and cannot be silently restored into authority;
- a complete subprocess-only engagement path works through preflight, artifacts, attempts, independent reviews, finding proposal, operator filing, report, and closure;
- hash-chain, crash recovery, deterministic reduction, secret scanning, contamination, and stale-environment tests remain green.

### Slice G — Add minimal flow export and runtime adapters

- Add one closed, versioned flow-telemetry export schema and one deterministic exporter that reuses Decision 0005 records and coverage semantics.
- Add a generic normalized JSON runtime adapter and the first concrete Claude Code adapter; do not couple the kernel to Claude Code hooks or transcript formats.
- Derive tier, stage transitions, authority intervals, backtracks, reviews, and completeness from kernel records; treat runtime turns/tokens/tool timing as optional advisory observations.
- Refuse causal or cross-runtime comparisons from live engagement data.
- Prove that flow fields are unreachable from claim adjudication, calibration, gate classification, routing, severity, reporting, and authority transitions.

### Slice H — Remove the interim bypass and update documentation

- Delete `HARNESS_AGENT_ATTESTED` after the capability path is verified.
- Update `engine/gates.md`, the Decision-0005 implementation report, templates, and operator runbook.
- Migrate no historical actor attribution silently; retain interim records as what they actually recorded and document the limitation.
- Replay the frozen Slice-0 corpus under old and new gate regimes; report `gates_held`, notebook improper-stall delta, trace coverage, and limitations.

## 5. Strict implementation feedback loop

Every slice, including Slice 0, uses the same fail-closed loop:

```text
freeze slice inputs and binary acceptance criteria
  -> implement the smallest slice
  -> targeted positive/negative/adversarial tests
  -> full Decision-0005/0006 conformance and deterministic replay
  -> independent cold Terra static audit
  -> classify blocker/high findings
  -> correct code or plan; never explain away a failed invariant
  -> rerun targeted tests, full conformance, and all prior frozen replays
  -> record evidence and only then advance
```

Terra is a reviewer, not an oracle. It receives primary source, schemas, tests, and frozen outputs; it does not contact targets or adjudicate vulnerabilities. A Terra failure does not mutate authority or claim state.

Use one independent Terra closure audit for every slice. Use two independent cold Terra audits for the highest-risk boundaries: Slice A's tier matrix, Slice B's attribution/capability enforcement, Slice D's async authority isolation, Slice G's telemetry isolation, and the final Slice-H integration. Reviewers do not see each other's draft before reporting. Any blocker/high must be fixed and re-audited to `PASS` before the next dependent slice.

The Terra audit must specifically attempt to:

- reclassify an Authority/Real-world operation as Notebook to improve flow metrics;
- forge operator or independent-review identity through caller-controlled fields;
- make missing runtime data appear as zero or smooth flow;
- make runtime telemetry affect truth, tier assignment, or calibration;
- leak prompt/tool/payload/secret material through trace fields;
- hide a lane-local wait inside engagement-wide averages;
- produce different exports from identical frozen inputs.

A slice is not complete merely because its new tests pass. It is complete only when previous behavior replays cleanly, the independent audit passes, and no required gate was weakened. Final acceptance requires the old-versus-new frozen operation replay plus a clean full-suite run.

## 6. Interim implementation status

The current worktree contains an experimental `_AGENT_NOTEBOOK_OPS` / `HARNESS_AGENT_ATTESTED` path for `environment-preflight`, `register-artifact`, and `append-attempt`. Existing self-tests pass, and it demonstrated that non-interactive notebook collection removes a real flow stall.

That experiment is **not the accepted design**:

- the same agent can set the environment variable;
- preflight still records operator authorship;
- passing integrity tests do not prove truthful authority or end-to-end semantic safety;
- no permanent capability boundary should depend on this switch.

Keep it isolated or revert it if implementation does not proceed immediately. Do not broaden its allowlist. The accepted implementation must replace it through Slices 0–H.

## 7. Operational lessons retained

1. Reserved kernel directories contain only registered/generated kernel records. Working notes belong in `analysis/`; report drafts belong in `report-drafts/`.
2. Formalization is incremental: register artifacts and append attempts as work occurs rather than reconstructing the engagement at the end.
3. Scope revisions are append-only authority changes. Never erase drift by silently replacing bytes.
4. Persistence and notebook autonomy do not lower the oracle bar. A difficult or long-running PoC still requires faithful real-control-flow verification and independent proof review.
5. A blocked authority request is a routing input: continue other safe work, then return when the exact dependency is approved or rejected.

## 8. Acceptance criteria

Decision 0006 is ready for acceptance only when:

- every public operation has one tested capability/tier classification;
- ordinary notebook work runs without synchronous operator bookkeeping;
- no agent-controlled value can produce operator authority;
- independent claim review and operator finding acceptance remain distinct;
- pending human decisions block only dependent lanes;
- initial scope and every Zone-2 artifact retain their existing hard gates;
- preflight provenance is truthful and automated scans are not represented as human attestations;
- a subprocess-only end-to-end engagement test passes;
- the flow layer is agent-runtime-neutral, with a generic envelope and Claude Code only as the first adapter;
- runtime-specific and missing metrics remain optional, nullable, coverage-counted, and observational;
- no prompt, response, tool argument, command line, environment value, file content, credential, or target payload enters flow telemetry;
- flow telemetry cannot affect authority, claim truth, independence, calibration, routing, severity, reporting, or gate classification;
- required gates are excluded from the notebook improper-stall metric;
- identical frozen inputs produce byte-identical derived exports;
- the old/new frozen operation replay shows gates held and reports flow deltas only at complete measured coverage;
- every slice completes the test → Terra audit → correction → replay loop, with two independent audits on the named high-risk slices;
- Decision-0005 conformance, integrity, safety, reporting, memory, and closure tests remain green;
- no database, service, scheduler, dashboard, or automatic optimization path was added;
- the interim environment-variable bypass is removed.

This decision claims improved flow only after the frozen old/new replay and all authority invariants pass. Live traces remain descriptive telemetry. It does not claim improved vulnerability-discovery efficacy without separate prospective evidence.

## 9. Independent pre-implementation review disposition

Two independent Claude Code reviewers assessed the combined autonomy and measurement direction before this revision. Both returned `CHANGES`, not rejection. Their converged requirements are incorporated above:

- reuse Decision 0005 funnel/cost/coverage machinery rather than build another analytics system;
- derive kernel facts deterministically and keep runtime observations optional/advisory;
- make the contract agent-neutral, with Claude Code as the first adapter rather than a core dependency;
- separate required human gates from improper Notebook stalls;
- preserve `null` and measured-coverage semantics;
- capture counts/ids/durations only, never prompts, arguments, payloads, or secrets;
- refuse live causal claims and cross-runtime averages;
- prove gates held before discussing flow gains;
- require frozen replay and independent Terra closure audits.

No reviewer output is authority or evidence that the implementation works. These reviews refine the plan; Slices 0–H and their acceptance loop must still be implemented and verified.
