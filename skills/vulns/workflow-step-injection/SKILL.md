---
id: wfstep.workflow-step-injection
name: Durable-Execution Step Injection / Bypass / Cross-Tenant Access
description: >
  Prove a durable-execution / workflow-orchestration runtime (step schedulers, event-sourced replay
  engines, saga-pattern frameworks) executes, skips, or cross-resolves a step because the identifier
  used to AUTHORIZE an action differs from the identifier actually used to RESOLVE/EXECUTE/PERSIST
  it — an outer checked identifier (run/tenant/namespace) vs. an inner, unchecked one embedded in a
  payload, nested command, or bearer token. Confirmed only via a planted canary in a run you own,
  observed executing/leaking into a SECOND run/tenant context you also own.
type: vuln
owasp: "A01:2021 Broken Access Control (IDOR applied to workflow/event state)"
atlas: "—"
patterns: [broken-object-level-authz]

activation:
  strong:
    - "a step/hook/callback resumption endpoint accepts a client-influenceable runId/stepId/hookId/token where the authenticated caller's own scope differs from the target being resolved"
    - "a batch/bundled operation authorizes against an OUTER identifier (namespace, tenant) but executes INNER, payload-embedded operations against a DIFFERENT identifier with no re-check that outer==inner"
    - "step-result/event persistence deserializes a payload with a legacy/unsafe deserializer (type-tagged objects, pickle-like reconstruction) reachable from step input/output data"
  weak:
    - "generic run/step/hook identifiers appear in URLs or payloads with no visibly-enforced ownership check at the point of use (may be enforced one layer up, e.g. at an API gateway — check before concluding a gap)"
    - "a storage/schema layer has multi-tenancy-shaped columns (owner/tenant/project id) that are present but unpopulated or unread — a signal the isolation boundary may live elsewhere (a different service, a different deployment topology) rather than being enforced here; do NOT treat as confirmed until you find where enforcement DOES happen or prove it doesn't happen anywhere"
  negative:
    - "ownership/tenant is resolved from authenticated session/request context at the point of storage access, never from a request-supplied field → likely held"
    - "inner (payload-embedded) and outer (session-authorized) identifiers are asserted equal before any privileged action → likely held"
    - "step/run identifiers are server-generated, high-entropy, and not client-namable, AND bearer tokens (webhook/callback resumption) are scoped to exactly one hook/run with no cross-hook reuse → likely held for forgery, though still check scoping"

safe_signal:
  proxy: >
    plant a distinctive, harmless marker as the payload of a step in a workflow run you own (Run A).
    Using only credentials/tokens/identifiers scoped to a SECOND run or tenant you also own (Run B),
    attempt to trigger, resume, read, or influence the step carrying Run A's marker. Confirmed only if
    Run B's authenticated context receives, executes, or observes Run A's planted marker — proving a
    step was injected into, bypassed for, or cross-read across a boundary that should have held. Both
    runs/tenants must be operator-owned; never touch a real third party's workflow state.
  never: >
    never attempt this against a shared/production multi-tenant instance without scope.md
    authorization AND an operator confirm before any cross-boundary artifact is created; never forge
    a token/identifier belonging to an account you do not own.

impact_escalation:
  enabled_by: scope.md#impact_demo_authorized
  requires: human_confirm
  containment: >
    both runs/tenants operator-owned; marker is inert (no real command capability); logged in
    engagement cleanup.md with both run/tenant identifiers for cleanup tracking.

oracle: [signal-oracle, adjudication-oracle]
severity_rubric:
  { cross_tenant_step_execution_or_state_read: critical, same_tenant_cross_run_access: high, same_run_replay_or_skip_of_an_auth_check_step: medium, unused_isolation_metadata_no_proven_read_path: needs_review }

procedure:
  - "MAP THE IDENTITY MODEL FIRST (Stage 0/1, engine/whitebox-analysis.md): for the target runtime, find (a) how a step's identity is generated (server-side high-entropy vs. client-derivable), (b) how run/tenant ownership is represented in storage (a queryable column? a separate database/schema per tenant? enforced only by an upstream API layer?), (c) every place an external actor can supply an identifier that influences which run/step/hook gets touched (webhook resumption, callback endpoints, batch/bundled operation payloads)."
  - "DISTINGUISH SCAFFOLDING FROM ENFORCEMENT — the single most common false-positive in this class: an unpopulated or unread tenant/owner column is NOT itself a vulnerability. Before treating it as a signal, grep for every READ of that field to confirm nothing gates access on it, AND check whether a different, more privileged backend/deployment path (e.g. a hosted multi-tenant production service vs. an open-source self-hosted single-tenant reference implementation) is the one that actually needs auditing — a stub in the self-hosted reference does not prove anything about a closed-source hosted backend, and vice versa."
  - "CHECK THE OUTER-VS-INNER IDENTIFIER INVARIANT: for any operation that bundles or nests sub-operations (batch APIs, signal/cancel-external-workflow calls, multi-step commands), verify the identifier the caller was authorized against is the SAME one actually used to resolve/execute each nested operation — not merely present, but checked for equality at the point of use."
  - "CHECK BEARER-TOKEN SCOPING: for webhook/callback resumption via a bearer-style token (no additional signature), confirm the token is high-entropy, single-hook-scoped, and that possessing it doesn't also grant broader run/tenant access than the one hook it was issued for."
  - "BENIGN FINGERPRINT: plant the marker in an owned Run A step; attempt cross-run/cross-tenant reach using only Run B's own credentials/identifiers."
  - "CONFIRM: Run B's context must receive/execute/observe Run A's exact marker — not merely that Run B could name Run A's identifier in a request (that's just the attempt, not the confirmation)."
  - "RULE OUT enforcement-elsewhere: if the cross-boundary attempt is rejected, check WHERE it was rejected (storage layer? API gateway? auth middleware?) — a rejection at any layer means held, but note which layer for the record, since a hosted-service-only enforcement layer means the OSS repo alone can't prove or disprove this for that deployment."
  - "STOP at the scope.md ceiling — do not escalate a confirmed injection/bypass into demonstrating real cross-tenant data exposure on a shared/production instance without explicit scope and a fresh operator confirm."

emits: [attempt, finding]
---

## What "confirmed" looks like here
Run B's own, independently-authenticated context receives, executes, or observes something planted
in Run A — proven with two operator-owned runs/tenants, not inferred from reading storage-layer code
alone. Reading code that reveals an unused or unpopulated tenant-scoping column is a `weak` signal
and a starting hypothesis, never a `confirmed` finding on its own.

## Not this card
- A step/run identifier that's guessable or enumerable but where every access still re-validates the
  caller's own authenticated ownership before acting → that's closer to a rate-limiting/enumeration
  concern, not step injection; consider `business-logic-abuse` instead if there's a real issue.
- A batch operation where the framework correctly asserts outer==inner identifiers before executing
  nested operations → held; record as a positive control.
- A general "no auth check on this step" finding where the DEVELOPER, not the framework, chose not to
  add one → out of scope per this program's own framing (framework bug vs. developer's own design
  choice) — only the framework's OWN merge/dispatch/identity logic silently dropping or confusing a
  check counts here.

## Do not overclaim
- An unread/unpopulated tenant-scoping field is evidence of a GAP IN UNDERSTANDING (where does
  enforcement actually live?), not evidence of a BYPASS, until you've traced every read path for that
  field and confirmed none of them gate access — and until you've identified which actual deployment
  topology (self-hosted reference vs. hosted production service) the finding even applies to.
- A closed-source hosted backend that your target program operates (e.g. a managed multi-tenant
  service) may enforce isolation in code you cannot read at all — absence of evidence in the OSS repo
  is not evidence of absence there. Land this explicitly as an open question, not a refuted negative.
- Name the exact outer identifier, the exact inner identifier, and the exact point where they should
  have been checked against each other (and weren't) in one sentence, or it isn't confirmed.

## References (from 2026-07-06 deep-research pass + independent source verification,
`engagements/vercel-open-source-2026-07/`)
- Temporal — "Masked Namespace" (reported as CVE-2025-14986, depthfirst.com writeup): outer-namespace
  check, inner-namespace-execution mismatch in `ExecuteMultiOperation`.
- Temporal — cross-namespace command execution (reported as CVE-2025-14987 / GHSA-hmhp-gh8m-c8xp):
  frontend authorizes against caller's namespace, history service resolves against a payload-embedded
  namespace with no re-check. (Second-hand via search synthesis — re-verify exact ID before citing.)
- Temporal — missing auth interceptor on replication stream (reported as CVE-2026-5724 /
  GHSA-q98v-9f9w-f49q): an entire auth interceptor omitted from one gRPC stream's chain.
- Argo Workflows — CVE-2026-28229 / GHSA-56px-hm34-xqj5, CVSS 9.1: read endpoint used the server's
  own service-account identity via informers instead of the caller's — classic confused-deputy.
- Apache Airflow — CVE-2026-33858 (and earlier CVE-2023-50943): unsafe XCom (step-result)
  deserialization via legacy type-tagged keys bypassing a safe-deserialization flag.
- **Source-level lead, independently re-verified this session**: `vercel/workflow`,
  `packages/world-postgres/src/storage.ts:1523-1525` — literal `ownerId: '', // TODO: get from
  context` / `projectId: ''` / `environment: ''` stubs on hook-entity creation, confirmed present
  verbatim in the cloned repo (not a research-agent hallucination). **However**, traced further: no
  code in this file (or found elsewhere in the package) ever READS `ownerId`/`projectId` to gate
  `get`/`list`/`getByToken` access — these fields appear write-only/unused in this backend. `
  world-vercel` (the actual Vercel-hosted, genuinely multi-tenant production backend) has **zero**
  `ownerId`-shaped references at all, meaning its tenant-isolation enforcement — if any gap exists —
  lives entirely in Vercel's closed-source hosted service, not auditable from this repo. **Downgraded
  from the research pass's original framing ("directly-observed IDOR-shaped gap") to `needs_review`**:
  real, verbatim, but impact currently unproven — this is exactly the kind of self-correction
  `engine/whitebox-analysis.md`'s multi-round grading exists to catch, in either direction (don't kill
  a real lead prematurely, but don't inflate an unread column into a confirmed bypass either).
  `getByToken(token)` webhook/callback resumption is a bearer-capability-token pattern (reasonable if
  the token is high-entropy and single-hook-scoped) — token-generation strength not yet verified,
  flagged as the most promising concrete next step if this card is picked up again.
- General pattern literature: event-sourcing/replay-attack and saga-pattern security discussions;
  academic work on control-flow hijacking in multi-agent/orchestrator systems (arXiv 2510.17276) as a
  conceptual sibling to "implicit trust inheritance across step boundaries."
