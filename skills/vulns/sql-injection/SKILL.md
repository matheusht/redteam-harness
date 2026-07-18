---
id: sqli.sql-injection
name: SQL Injection
description: >
  Prove an app builds a database query from unsanitized client input, letting the caller alter the
  query's logic or extract data outside the intended query shape. Covers classic (in-band),
  blind/time-based, and NoSQL operator-injection variants. Confirmed only via a differential that
  proves the query's LOGIC changed, or a planted canary in an owned test row/table.
type: vuln
owasp: "A03:2021 Injection"
atlas: "—"
patterns: []

activation:
  strong:
    - "a request parameter is concatenated or string-formatted into a SQL/NoSQL query before execution, rather than passed as a bound parameter"
    - "a database error message, stack trace, or driver-specific syntax hint is returned to the client on malformed input"
    - "a boolean-tautology or timing payload changes response shape/latency versus a matched control"
    - "JSON body fields reach a NoSQL query verbatim, permitting operator keys ($ne, $gt, $regex, etc.) instead of scalar values"
    - "a client-controlled ORDER BY column, sort direction, boolean connector, or cast type is placed into query text with no allowlist — the identifier/keyword-position variant that value-parameter binding cannot cover (diff-derived: the removed unguarded `db.Order(order)` in CVE-2024-37896, the `Q(_connector=...)` passthrough in CVE-2025-64459 — see the anchors section)"
  weak:
    - "an ORM or query builder is in use but with raw/unsafe escape hatches (raw(), literal interpolation) reachable from user input"
    - "search/filter/sort parameters map directly to column or field names without an allowlist"
  negative:
    - "all query construction uses parameterized statements / prepared queries with no raw interpolation reachable from client input → likely held"
    - "the ORM never exposes a raw-query escape hatch to the affected input path"
    - "identifier/keyword-position inputs (ORDER BY column, boolean connector, cast type) that cannot be bound as parameters are checked against an explicit allowlist / exact-match set before use → likely held (diff-derived: the `fields[col]` membership + asc/desc exact-match in CVE-2024-37896, the `connectors=(None,AND,OR,XOR)` allowlist in CVE-2025-64459)"

safe_signal:
  proxy: >
    a predeclared distinctive artifact only reachable via a genuine change in query logic — e.g. a
    benchmark's build-time flag stored in a row only a broken query could return, or (in a live app)
    a canary row/column planted by the operator in an OWNED test table. A statistically significant,
    reproducible timing delta on a blind/time-based payload versus a matched negative control also
    counts as signal for that sub-variant, but alone is not sufficient for `confirmed` (see below).
  never: >
    do not extract, dump, or enumerate real application data, schemas, or other users' rows; do not
    run destructive statements (UPDATE/DELETE/DROP) outside an owned, disposable fixture; any
    extraction beyond the planted canary requires scope.md authorization AND an operator confirm.

impact_escalation:
  enabled_by: scope.md#impact_demo_authorized
  requires: human_confirm
  containment: "read the planted canary only; no schema dump, no write statements, logged in engagement cleanup.md"

oracle: [signal-oracle, adjudication-oracle, ghsa-fix-diff]
severity_rubric: { data_exfil_arbitrary_table: critical, single_table_read: high, boolean_oracle_only: medium, error_message_only: low }

procedure:
  - "IDENTIFY THE PARAMETER: every input that flows into a query — path/query/body field, header, sort/filter key, even a field name itself in NoSQL filters."
  - "FINGERPRINT (benign): send a single-quote / boolean-tautology (`' OR '1'='1`) or NoSQL operator (`{\"$ne\": null}`) payload and compare to a matched negative control (same shape, benign value). A differing error, row count, or response shape is a candidate signal, not a finding."
  - "CONFIRM LOGIC CHANGE, NOT JUST AN ERROR: an error message alone is low severity and easily contaminated by generic input validation. Prove the query's WHERE/filter logic actually changed — e.g. a tautology returns more rows than the negative control, or a planted canary row surfaces."
  - "BLIND / TIME-BASED: use a time-delay payload (e.g. `SLEEP(5)` equivalent) against a matched negative-control baseline; require a reproducible, statistically significant delta (not a single noisy timing sample) before treating it as signal."
  - "NOSQL VARIANT: probe JSON body fields with operator keys ($ne/$gt/$regex) in place of scalar values; confirm via the same differential-logic-change standard, not merely 'the request was accepted'."
  - "ESCALATE ONLY to the planted canary within scope. Do not enumerate schemas, dump tables, or touch real data. Cross-table or cross-tenant read requires scope.md authorization and operator confirm before any artifact."
  - "RULE OUT contamination (generic 500 handler, WAF quirk, unrelated app error) and REPLAY in a fresh session."

emits: [attempt, finding]
---

## What "confirmed" looks like here
The query's logic demonstrably changed because of unsanitized input — proven by the **planted
canary** surfacing, or a reproducible boolean/timing differential against a matched negative
control — with contamination ruled out and reproduced once in a fresh session. A raw database
error with no logic-change evidence is `needs_review` at best, not `confirmed`.

## Boundaries (escalate in order; each rung gated on the prior + scope.md)
1. **error/behavior differential only** — query logic provably altered, no data read → low/medium.
2. **single owned canary row read** — the planted marker returned → high.
3. **arbitrary table / cross-tenant read** — critical; **operator confirm before any artifact**.

## Real disclosed anchor(s) for this class (fix-diff-derived)
Priors/taxonomy from real disclosed GHSA fix commits — the vulnerable pre-patch shape and the guard
the fix added. Verbatim hunks + primary sources in `skills/oracles/references/ghsa-fix-diff-corpus.md`
(SQL injection bucket); consult via the `ghsa-fix-diff` oracle. **These are all *fixed* bugs, not
live-bug claims:** a target matching a removed-line shape is a lead to run through the funnel above,
never a confirmation. The class splits bimodally by injection position.

**Value-position (bindable → the fix is a `?`-placeholder), `param-binding`:**
- **CVE-2024-32461** (librenms, fixed 24.4.0 @ `d29201f`): raw `$_POST['package']` concatenated into
  `LIKE '%...%'` → bound `LIKE ?` + `$param[]`. Authenticated blind SQLi.
- **CVE-2026-26980** (Ghost, GHSA-w52v-v783-gw97, fixed 6.19.1 @ `30868d6`): slug values interpolated
  into `ORDER BY CASE WHEN ... = '${slug}'` → `?` placeholders + `bindings[]`. **Pre-auth** Content-API.

**Identifier/keyword-position (NOT bindable → the fix is an allowlist / exact-match), `exact-match-swap`:**
- **CVE-2024-37896** (gin-vue-admin, fixed 2.6.6 @ `53d0338`): client `order` param → `db.Order(order)`
  unguarded → field-name allowlist (`fields[col]` membership) + `asc`/`desc` exact-match. Authenticated
  `ORDER BY` injection.
- **CVE-2025-64459** (Django, GHSA-frmv-pr5f-9mcr, fixed 4.2.26 / 5.1.14 / 5.2.8 @ `72d2c87`):
  `Q(_connector=...)` passthrough into the WHERE-tree connector → `connectors=(None,AND,OR,XOR)`
  allowlist + `ValueError`. Library-level, reachability-gated.
- **CVE-2026-30951** (Sequelize, GHSA-6457-6jrx-69cr, fixed 6.37.8 @ `b147528`) — **CONTESTED**
  (non-contiguous fix, illustrative only): JSON `key::type` cast segment interpolated raw into
  `CAST(... AS <type>)` → `ALLOWED_CAST_TYPES` Set membership.

## Not this card
- Application-level business-logic filters that happen to accept unexpected values but never
  reach a query (that's `business_logic`, not injection).
- A generic 500 error with no distinguishable logic-change signal — that's a bug report, not a
  confirmed injection.

## Do not overclaim
- "The response changed" proves nothing until you can name which query clause changed and why.
- A single slow response is noise, not a timing oracle — require a repeatable delta against a
  negative-control baseline, or it isn't confirmed.
- If the class's added-guard shape is already present in the target's source for the reached sink —
  a bound `?` placeholder for a value-position input, or an allowlist / exact-match check for an
  `ORDER BY` column / connector / cast type (see the anchors above) — this path is patched; do not
  claim strong activation without a further, specific reason (an unguarded sibling sink, a reachable
  pre-guard path). Presence of the guard is a strong held signal, not a soundness proof.
