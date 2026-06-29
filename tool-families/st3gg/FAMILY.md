# FAMILY — ST3GG (steganography detection + benign-artifact family)

**Status:** S0 family profile — inventory + authority contract only. No runtime build. No upstream code executed.
**Upstream:** <https://github.com/elder-plinius/ST3GG> · reviewed commit `35f8b2b` · **AGPL-3.0**
**Integration posture:** arms-length `subprocess` (default). AGPL source is not vendored/linked into Plane 1/2.
**Authority:** the manifest, broker, and oracle hold authority. ST3GG is **never** an oracle — it emits
detection evidence, artifact digests, or (later, gated) proposals; never `confirmed`/`allow`/`verdict`/`success`.

This is a harness profile of the upstream repo, not a copy of it. The agent reads the harness-owned
`AGENT.md`, not the upstream quickstart. Plan of record: `docs/tool-family-plans/st3gg.md`.
Graduation ladder (M0-M6): `docs/tool-family-adapter-architecture.md`.

## Module inventory (M0)

Every upstream surface is inventoried now; runtime authority is earned gate-by-gate. Risk tier and the
proposed capability class are recorded so nothing is "erased from scope" — high-risk modules are listed
with a `blocked_until` gate, not deleted.

| Upstream surface | Purpose | In → Out | Risk | Proposed class | Status / gate |
| --- | --- | --- | --- | --- | --- |
| `stegg_cli.py` (JSON CLI) | subprocess-friendly entrypoint | argv/JSON → JSON | low | (transport) | adapter target (S2) |
| `analysis_tools.py` registry | detect/inspect file & text artifacts | file/text → findings | low | `sensor` | **exposed** (S2) |
| Unicode stego detectors | hidden prompt/content channel evidence | text → indicators | low | `sensor` | **exposed** (S2) |
| file-type detection | artifact triage before specialized analysis | file → type | low | `sensor` | **exposed** (S2) |
| image capacity / detect / decode | carrier capacity + detection | image → metrics/indicators | low-med | `sensor` | capacity exposed; decode is redacted-only (S5) |
| benign-canary embedding | embed a known benign canary in a local carrier | canary+carrier → artifact | medium | `payload_generator` | `blocked_until: S3` |
| raw payload extraction | decode hidden content from an artifact | artifact → decoded data | high | `sensor` (redacted) | `blocked_until: S5` (hash/canary-only default) |
| injector / template actions | construct injection-carrying artifacts | spec → candidate artifact | high | `payload_generator` | `blocked_until: S6` (proposal-only) |
| conceal / agent modes | autonomous concealment workflows | spec → concealed artifact | high | `payload_generator` | `blocked_until: S6` (proposal-only) |
| network covert-channel | covert channel over network | spec → channel artifact | high | `payload_generator` | `blocked_until: S7` (hermetic sim only) |
| multi-layer / encrypted stealth | layered/encrypted carriers | spec → carrier | high | `payload_generator` | `blocked_until: S7` (hermetic lab) |
| live executor behavior | act against a live target | artifact → live effect | critical | `executor` | `blocked_until: S9` (broker-mediated) |

## What is exposed today

**Nothing runs yet — this family is S0 (manifest-declared, runtime not built).** The sensor-only
capability `external.st3gg.detect` and its contract exist in `capabilities/registry.yaml`
(`analyze_file`, `detect_unicode_steg`, `detect_file_type`, `summarize_findings`, `capacity_inspect`),
but **no ST3GG runtime adapter or selftest is built** (that is S2). When S2 lands, its output will be a
redacted `artifact_digest.json` (file type, detector ids, suspicious indicators, confidence,
`raw_payload_present` boolean, hashes). Until then, the `exposed (S2)` rows above are *target phases*,
not live surfaces.

## Permanent non-negotiables (any phase)

- No ST3GG action returns a final harness verdict or scores its own result.
- No ST3GG action mutates evaluator, gold, budgets, sealed data, or promotion authority.
- No raw decoded secret is stored in Plane 1/2; default extraction output is hash or canary-boolean.
- No live or persistent artifact bypasses scope, containment, cleanup, and broker evidence.

## License note

AGPL-3.0 is acceptable if deliberately adopted; arms-length subprocess keeps it testable, replaceable,
and out of the context window. A deeper vendored route stays subject to the same authority model.
