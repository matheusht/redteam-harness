---
id: protop.prototype-pollution
name: Prototype Pollution
description: >
  Prove attacker-controlled key names reach an object-mutation path (deep-merge, deserializer,
  key-based property assignment) without a `__proto__`/`constructor`/`prototype` guard, polluting
  `Object.prototype` itself — not just the object the input was fed into — and that a concrete
  downstream reader (an auth flag, an allowlist check, a config value, a template attribute) then
  consumes the polluted property. A local-object mutation (e.g. reassigning ONE object's own
  `[[Prototype]]`, not the global one) is a different, usually inert, finding — don't conflate them.
type: vuln
owasp: "A08:2021 Software and Data Integrity Failures (Prototype Pollution)"
atlas: "—"
patterns: []

activation:
  strong:
    - "a deep-merge/deep-set utility (custom, or a library with a documented history of this class — e.g. defu, lodash.merge/.set, older js-yaml) copies attacker-JSON-shaped input into a plain object without stripping __proto__/constructor/prototype keys"
    - "a custom deserializer (not JSON.parse alone, which is itself safe) reconstructs nested objects key-by-key, or reassigns an object's prototype chain based on a payload-carried key (devalue-style)"
    - "an attacker/third-party-controlled STRING (an MCP tool name, a plugin id, a webhook event type) is used as a bracket-index key into a plain object or Map-like structure without an own-key guard (`hasOwnProperty`/`Object.hasOwn`/`Map` instead of a plain object)"
  weak:
    - "a deep-merge library with a known prior CVE class is present as a transitive dependency, even if not obviously reachable yet"
    - "code uses `for...in` or object-spread over a value that could carry inherited (not just own) properties, without an ownership filter — this is the CONSUMPTION half (Svelte-SSR-attribute-spread style): only a real finding once paired with an actual pollution source, but worth noting as a multiplier"
  negative:
    - "merge/assignment target is created via `Object.create(null)` (no prototype to pollute) → held"
    - "storage is Map/WeakMap-keyed, not a plain-object property store → held (key traversal can't reach `[[Prototype]]`)"
    - "merge uses object-spread (`{...a, ...b}`) rather than `Object.assign`/manual key-loop assignment → held against the classic `__proto__`-setter-invocation gadget (spread uses `[[DefineOwnProperty]]`, never a setter)"
    - "explicit denylist of `__proto__`/`constructor`/`prototype` keys present at the merge site → likely held, but verify the denylist covers all three keys and both bracket and dot-access forms"

safe_signal:
  proxy: >
    inject `{"__proto__":{"<nonce>_marker": true}}` (or, where a `constructor.prototype` path is the
    reachable shape, `{"constructor":{"prototype":{"<nonce>_marker": true}}}`) through the candidate
    input path using a fresh random nonce per attempt, THEN — from a SEPARATE, freshly-created,
    otherwise-unrelated plain object/request handled later in the same process — check whether
    `({}).{"<nonce>_marker"}` (or the unrelated object) now carries the marker. A harmless boolean
    property with a random name, trivially distinguishable from real application state, cleaned up
    (or left to be garbage-collected with the process/test run) after.
  never: >
    never pollute a property name that collides with real application logic (`isAdmin`, `role`,
    `toString`, etc.) in anything but a fully isolated local test process; never target a shared/
    production process where pollution could affect other tenants' requests without scope.md
    authorization AND an operator confirm.

impact_escalation:
  enabled_by: scope.md#impact_demo_authorized
  requires: human_confirm
  containment: >
    marker property uses a random nonce, never collides with a real application property name;
    pollution only ever demonstrated in an isolated local process/test run, never against a shared
    running instance; logged in engagement cleanup.md.

oracle: [signal-oracle, adjudication-oracle]
severity_rubric:
  { confirmed_chain_to_auth_bypass_or_rce: critical, confirmed_global_pollution_with_downstream_reader: high, confirmed_global_pollution_no_reader_yet: medium, local_object_mutation_only: info_or_no_finding, held: info }

procedure:
  - "MAP THE SINK: find every deep-merge, deserializer, or bracket-keyed-by-untrusted-string assignment in the candidate code path. Note whether the target is a plain object, `Object.create(null)`, or a Map — this alone often resolves the candidate without touching the target."
  - "CHEAP CLASSIFY (Stage 1, engine/whitebox-analysis.md): before writing any PoC, read the ACTUAL merge/assignment implementation, not just its name/reputation — the same library can be safe in one call site (spread) and unsafe in another (Object.assign / manual key loop) in the same codebase (seen in this engagement: one file used both patterns inconsistently)."
  - "LOCAL-VS-GLOBAL CHECK (the single most common misclassification in this class): confirm whether the mutation reassigns the fed-in object's OWN `[[Prototype]]` (local, usually inert) versus `Object.prototype` itself (global, real). Bracket-assigning `obj['__proto__'] = x` on a plain object literal is LOCAL unless `obj` itself somehow IS (or aliases) `Object.prototype`. Do not report a local mutation as prototype pollution."
  - "BENIGN FINGERPRINT: run the safe_signal payload with a fresh random nonce through the candidate input path."
  - "CONFIRM GLOBAL REACH: from a separate, freshly-created object/request in the SAME process (not the one you fed input into), check for the nonce marker. This is the line between a real finding and a same-object echo."
  - "CONFIRM DOWNSTREAM READER: identify a concrete piece of code that reads the polluted property name (or a property name in the same shape) via unguarded property access, and show that reading it after pollution returns the attacker's value. Without this, land as `needs_review` (real pollution, no proven consumer) not `confirmed`."
  - "FOR MCP/TOOL-NAME-KEYED VARIANTS: drive the payload from an actual controlled/simulated malicious MCP server or plugin registration (a tool/plugin NAMED `__proto__`/`constructor`/`toString`), not from a unit test constructing the vulnerable object directly — the sink under test is the boundary between an untrusted party's chosen string and the host's object keying, and skipping that boundary is exactly the kind of self-built-harness-doesn't-match-reality gap `engine/whitebox-analysis.md` §4 warns about."
  - "RE-VERIFY: run the full confirm sequence twice in fresh, isolated process instances — pollution that only reproduces once can indicate a stateful test-order artifact, not a real reachable bug."
  - "STOP at the scope.md ceiling — do not chain a confirmed pollution primitive into an actual auth-bypass/RCE demonstration against a shared instance without explicit scope and a fresh operator confirm."

emits: [attempt, finding]
---

## What "confirmed" looks like here
The nonce marker appears on `Object.prototype` (or a shared/global structure), observed from a
SECOND, independently-created object/request handled after the payload — not merely on the object the
payload was fed into — AND a concrete downstream reader consumes the polluted property name in a way
that changes real behavior (an auth check, an allowlist lookup, a config value, a rendered
attribute). Reproduced twice in fresh, isolated process instances.

## Not this card
- A payload that reassigns ONE local object's own `[[Prototype]]` (e.g. `tools['__proto__'] = {...}`
  on a fresh object literal) with no evidence of global `Object.prototype` reach → not prototype
  pollution; if there's still a real bug here (e.g. a read-side `hasOwnProperty`-less lookup that
  resolves to an inherited member because of THIS local reassignment), describe it as what it is
  (an object-key/allowlist-confusion bug adjacent to this class), not as classic pollution.
- `JSON.parse` alone, with no subsequent deep-merge/deserializer/key-loop touching the parsed result
  → `JSON.parse` itself does not create own-enumerable `__proto__` properties that propagate; the risk
  is entirely in what happens to the parsed object afterward.
- Pollution demonstrated only inside a unit test that constructs the vulnerable object directly,
  never actually exercised from the real untrusted-input boundary (a real request, a real MCP
  server response, a real deserialization call) → `needs_review`, not `confirmed`.

## Do not overclaim
- "The library has a documented history of this CVE class" is a `weak` signal only — the SAME
  library can be patched, or used safely at one call site and unsafely at another within the same
  codebase. Always read the actual call site.
- A polluted property surviving to a second object proves GLOBAL reach, not IMPACT — always find and
  name the concrete downstream reader before calling it `confirmed` rather than `needs_review`.
- Name the exact sink (file:line), the exact property polluted, and the exact downstream reader in
  one sentence, or it isn't confirmed.

## References (from 2026-07-06 deep-research pass, `engagements/vercel-open-source-2026-07/`)
- `defu` — GHSA-737v-mqg7-c878 / CVE-2026-35209 (`Object.assign`-setter gadget bypassing the
  library's own `__proto__` denylist; fixed by switching to spread).
- Axios — GHSA-3g43-6gmg-66jw / CVE-2026-44495 (chain-to-impact example: polluted
  `transformResponse` executed with request-config `this`, exposing credentials/headers).
- `devalue` (used by SvelteKit for server→client serialization) — GHSA-vj54-72f3-p5jv /
  CVE-2025-57820 (`__proto__` key + unvalidated array-index assignment).
- Svelte SSR attribute spreading — GHSA-crpf-4hrx-3jrp / CVE-2026-27125 (consumption-side: `{...attrs}`
  enumerates inherited properties during SSR, turning pre-existing pollution into leaked/corrupted
  output — the read-side half of the pattern, only fires paired with a write-side source).
- MCP-specific: no disclosed CVE/GHSA found for a prototype-pollution-based MCP allowlist bypass as
  of this research pass — general MCP threat-model writeups list it as a theoretical risk class, not
  a confirmed instance. Treat the MCP angle of this card as genuinely novel-research territory, not a
  reproduction of known work.
- Source-level lead found this engagement (unconfirmed, needs a driven PoC):
  `vercel/ai`, `packages/policy-opa/src/wrap-mcp-tools.ts:78` — `filled[name] = approval[name] ??
  fallback` keyed by a server-controlled MCP tool name with no `hasOwnProperty` guard, inconsistent
  with the same file's correct `hasOwnProperty.call(...)` usage elsewhere. See
  `engagements/vercel-open-source-2026-07/recon-signals.md`.
