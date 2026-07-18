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
    - "a parser factory (SAXReader, DocumentBuilderFactory, XMLInputFactory) is built with its unsafe library defaults and no explicit disallow-doctype-decl / external-entity setFeature calls, or a null EntityResolver is passed into the parse() call (diff-derived: the inline exception-swallowing `new SAXReader()` in CVE-2020-10683, the bare `XMLInputFactory.newInstance()` in CVE-2016-3720, the hardcoded `null` EntityResolver in CVE-2025-58360 — see the anchors section)"
  weak:
    - "the XML is parsed but the field ultimately reflected is narrow (schema-validated before parsing), reachability of entity expansion unclear"
  negative:
    - "the parser is configured with external entities and DOCTYPE declarations disabled (e.g. a hardened parser flag set) → likely held"
    - "input is JSON/other non-XML format the endpoint merely labels as XML"
    - "the parser factory explicitly sets disallow-doctype-decl / external-general-entities / external-parameter-entities / IS_SUPPORTING_EXTERNAL_ENTITIES=false, or a restrictive EntityResolver is bound in place of null → likely held (diff-derived: `SAXReader.createDefault()` in CVE-2020-10683, the catalog `EntityResolver` bind in CVE-2025-58360, `IS_SUPPORTING_EXTERNAL_ENTITIES=Boolean.FALSE` in CVE-2016-3720)"

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

oracle: [signal-oracle, adjudication-oracle, ghsa-fix-diff]
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

## Real disclosed anchor(s) for this class (fix-diff-derived)
Priors/taxonomy from real disclosed GHSA fix commits — the vulnerable pre-patch shape and the guard
the fix added. Verbatim hunks + primary sources in `skills/oracles/references/ghsa-fix-diff-corpus.md`
(XXE bucket); consult via the `ghsa-fix-diff` oracle. **These are all *fixed* bugs, not live-bug
claims:** a target matching a removed-line shape is a lead to run through the funnel above, never a
confirmation. The class is dominated by one guard shape — entity-expansion-off — with a second,
rarer sub-shape (binding a restrictive EntityResolver in place of null).

**Direct feature/property disabling on the factory/reader, `entity-expansion-off`:**
- **CVE-2020-10683** (dom4j, GHSA-hwj3-m3p6-hj38, fixed 2.0.3 / 2.1.3 @ `a822852`): the public
  `DocumentHelper.parseText(String)` helper built a plain `new SAXReader()` and tried to disable
  external-DTD/entity features inline, silently swallowing `SAXException` and falling back to
  unsafe defaults → a shared `SAXReader.createDefault()` factory. Unauthenticated, any caller of the
  static parse helper.
- **CVE-2020-25649** (jackson-databind, fixed 2.11.0 / backported 2.9.10.5, 2.10.5.1 @ `612f971`):
  `DOMDeserializer`'s shared `DocumentBuilderFactory` only called `setExpandEntityReferences(false)`,
  insufficient on some JAXP impls → added `disallow-doctype-decl=true` +
  `load-external-dtd=false` setFeature calls. Reached by any `ObjectMapper.readValue()` deserializing
  untrusted XML into a `Document`/`Node`-typed field.
- **CVE-2016-3720** (jackson-dataformat-xml, GHSA-hmq6-frv3-4727, fixed 2.7.4 @ `f0f19a4`):
  `XmlFactory`'s default construction path built a bare `XMLInputFactory.newInstance()` with no
  entity restrictions → `IS_SUPPORTING_EXTERNAL_ENTITIES=Boolean.FALSE`. Any `XmlMapper.readValue()`
  on the default factory.
- **CVE-2025-54988** (Apache Tika, GHSA-p72g-pv48-7w9x, fixed 3.2.2 @ `94acef2`): the shared StAX
  `getXMLInputFactory()` used by Tika's PDF-XFA/OOXML parsers had no DTD/entity restrictions → added
  `SUPPORT_DTD=false` + `IS_SUPPORTING_EXTERNAL_ENTITIES=false`. Triggered by any document (e.g. a
  crafted PDF with an embedded XFA form) Tika parses.
- **CVE-2022-28140** (jenkinsci flaky-test-handler-plugin, GHSA-v4rr-65x6-g69f, fixed 1.2.2 @
  `c4ab38f`): `FlakySuiteResult.parse()` built a `new SAXReader()` with unsafe library defaults to
  ingest JUnit XML test-report files → three `setFeature` calls
  (`disallow-doctype-decl`, `external-general-entities=false`, `external-parameter-entities=false`).
  Reached whenever Jenkins ingests a build's test-report XML.

**EntityResolver binding, `entity-resolver-bind`:**
- **CVE-2025-58360** (GeoServer, GHSA-fjf5-xgmq-5525, fixed 2.25.6 / 2.26.2 / 2.27.0 @ `ebe34ef`):
  `SLDXmlRequestReader.read()` parsed the SLD body of an **unauthenticated** WMS GetMap request with
  a hardcoded `null` EntityResolver, letting a `<!ENTITY xxe SYSTEM "file:///...">` inside the
  `<Name>` resolve → a restrictive `EntityResolver` pulled from the catalog `ResourcePool` is bound
  instead of `null`. Pre-auth, high-value anchor.

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
- If the class's added-guard shape is already present in the target's source for the reached
  sink — explicit `disallow-doctype-decl` / external-general-entities / external-parameter-entities
  disabling, or a non-null, restrictive `EntityResolver` bound where the vulnerable shape passed
  `null` (see the anchors above) — this path is patched; do not claim strong activation without a
  further, specific reason. Presence of the guard is a strong held signal, not a soundness proof.
