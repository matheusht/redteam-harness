---
id: xxe.xml-external-entity
name: XML External Entity Injection
description: >
  Prove an endpoint parses client-supplied XML with external entity resolution enabled, letting a
  caller define a DOCTYPE/ENTITY that reads a local file or triggers an out-of-band request the
  application never intended to expose.
type: vuln
owasp: "A05:2021 Security Misconfiguration (XXE) / A03 Injection"
atlas: "—"
patterns: [pattern.ssrf-server-side-fetch]

activation:
  strong:
    - "an endpoint parses client-supplied XML (SOAP, XML upload/import, feed/document ingest) and the parser has not explicitly disabled DOCTYPE/external-entity resolution"
    - "an uploaded document format that is XML-based under the hood (docx, xlsx, svg, xml-based config import) is parsed server-side"
  weak:
    - "the XML is parsed but the field ultimately reflected is narrow (schema-validated before parsing), reachability of entity expansion unclear"
  negative:
    - "the parser is configured with external entities and DOCTYPE declarations disabled (e.g. a hardened parser flag set) → likely held"
    - "input is JSON/other non-XML format the endpoint merely labels as XML"

safe_signal:
  proxy: >
    a predeclared distinctive artifact only reachable via successful external-entity resolution —
    e.g. a benchmark's build-time flag in a CTF context, or an operator-owned canary file/URL in a
    live app — returned in the parsed response, or an out-of-band callback hit on operator
    infrastructure.
  never: >
    do not target internal/metadata hosts (169.254.169.254, loopback, private ranges) without
    explicit scope.md authorization and an operator confirm; only read files inside the owned
    sandbox/container.

impact_escalation:
  enabled_by: scope.md#impact_demo_authorized
  requires: human_confirm
  containment: "canary file/URL only, contained to owned infra; logged in engagement cleanup.md"

oracle: [signal-oracle, adjudication-oracle]
severity_rubric: { file_read_or_ssrf_confirmed: critical, oob_interaction_confirmed_no_read: high, parser_accepts_doctype_no_impact_shown: low, refused: info }

procedure:
  - "MAP THE PARSER: identify every endpoint that parses client-supplied XML or an XML-based upload format, and whether entity resolution is disabled."
  - "BENIGN INTERNAL ENTITY FIRST: submit a DOCTYPE with a benign internal entity to confirm the parser processes DOCTYPE declarations at all before attempting external resolution."
  - "EXTERNAL ENTITY, OWNED TARGET: define an external entity pointing at a canary file inside the owned container, or a canary URL/callback endpoint the operator controls — never an internal/metadata host without scope."
  - "NEGATIVE CONTROL (must decline): the same submission through any sibling endpoint or with DOCTYPE stripped should not trigger the read/callback. Record kind=negative_control."
  - "CONFIRM: the response carries the canary file's exact content, or the operator-owned callback endpoint logs the hit — not a generic parse error."
  - "BLIND XXE: if no content is reflected, rely solely on the out-of-band callback hit as the signal; do not claim file read without content evidence."
  - "STOP at scope.md ceiling before any internal-network or metadata-endpoint probe; that is a Zone-2 artifact requiring operator confirm."
  - "RULE OUT contamination; REPLAY in a fresh session."

emits: [attempt, finding]
---

## What "confirmed" looks like here
A client-supplied XML payload with an external entity causes the parser to return the **planted
canary's exact content**, or to hit an **operator-owned out-of-band endpoint**, where the negative
control (DOCTYPE stripped, or a hardened sibling endpoint) declined, reproduced once in a fresh
session. A parser that merely accepts a DOCTYPE with no observable read/callback is not a finding —
it's a coverage note (`parser_accepts_doctype_no_impact_shown`).

## Not this card
- The fetch is client-controlled but not via XML entity expansion (a plain `url` parameter) →
  `pattern.ssrf-server-side-fetch` instead. XXE that resolves to an internal host is the overlap
  case — route it through both, but the entity-injection mechanism belongs here.
- JSON/non-XML input mislabeled as XML with no actual parser reachable → no activation.

## Do not overclaim
- "The parser didn't error on a DOCTYPE" is not a finding — you need the canary content or the
  callback hit.
- Do not assert internal reachability (metadata endpoints, private ranges) you have not been
  scoped to test — that's an operator-confirmed Zone-2 step, not a default probe.
