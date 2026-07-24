# FAMILY — GLOSSOPETRAE (static source review + module inventory)

**Upstream:** <https://github.com/elder-plinius/GLOSSOPETRAE> · **reviewed commit:** `2c6f59a` ·
**license:** AGPL-3.0 (acceptable if deliberately adopted; arms-length default keeps it out of context).
**Review posture:** static review only — no upstream code executed, nothing vendored into Plane 1/2.

This file is the harness's *inventory* of the upstream family (the M0 gate of the module-graduation
ladder in `docs/tool-family-adapter-architecture.md`). Every module is documented here before it can
become a manifest action. Documenting a module is **not** authorizing it — authority is the manifest +
broker + oracle.

## What GLOSSOPETRAE is

A constructed-language and covert-channel evaluation toolkit: it forges languages, applies stealth
presets, and transports a message through channels a *plaintext/keyword* guard does not track while a
capable model still reads-and-acts on it. For this harness the useful core is **measuring
safety/generalization behavior across encoded channels** — the transport, not a payload arsenal.

## Module inventory → proposed class / risk tier / gate

| Upstream area | Harness action(s) | Class | Risk tier | First gate |
| --- | --- | --- | --- | --- |
| `redteam/channels.mjs` channel split (plaintext / homoglyph / token-break) | `list_channels`, `inspect_channel`, `encode_benign`, `decode_if_possible`, `roundtrip_check` | sensor / converter | benign canary | G2 (local shim) → G3 (external) |
| normalization behavior of a channel | `normalization_profile` | sensor | benign canary | G3 |
| channel-vs-defense measurement | `channel_rank_against_defense` | sensor | hermetic | G4 |
| refusal-consistency across channels | `model_refusal_consistency_eval` | sensor | authorized benign/proxy | G5 |
| semantic steganography module | `semantic_stego_proposal` | payload_generator | proposal only | G6 |
| token-manipulation / token-exploit module | `token_exploit_proposal` | payload_generator | proposal only | G6 |
| glyph / visual transport | `glyph_render_benign` | payload_generator | needs vision/OCR oracle | G7 |
| conlang / glyph channels | folded into `encode_benign` (benign) / `glyph_render_benign` (visual) | converter / payload_generator | benign / needs oracle | G2 / G7 |
| multi-agent shared protocol | `shared_protocol_hermetic` | sensor (test data) | hermetic | G8 |
| probe/corpus-driven eval | `authorized_probe_set_eval` | sensor | scoped live | G9 |
| benchmark/experiment outputs | inspiration only — **not** imported as truth | — | — | — |

## Permanently non-authoritative (never any class but a guarded one; never an oracle)

- any action returning a final harness verdict (`confirmed`/`allow`/`verdict`/`success`);
- any action mutating evaluator / gold / budget / sealed data / casebook / promotion authority;
- any action bypassing broker logs, controls, or replay;
- raw harmful corpus ingestion or live-target execution from this family.

## License / vendoring posture

AGPL-3.0. Default integration is `subprocess` against a *user-installed* checkout (G3+), so upstream
source never enters this repo's Plane 1/2. If deeper integration is ever deliberately accepted, the same
boundary holds: vendored source may supply mechanism, but the manifest/broker/oracle still own authority.

## What is built vs. inventoried

- **Built here (G0):** this inventory, `AGENT.md`, `manifest.yaml`, and the conformance keyhole check.
- **Inventoried, not built:** every `blocked_until` action above — in scope, gated, no adapter yet.
- **Local shim target (G2):** `tools/covert-channel-converter.py` (the harness's own toy channels) — proves
  the action/schema/broker shape with no license/runtime variable before any upstream call.
