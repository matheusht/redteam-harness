# FAMILY — P4RS3LT0NGV3 (transform catalog / transform-strategy lab)

**Status:** harness-owned profile · phased build (P0–P3 built; P4–P9 inventoried, blocked).
**Upstream:** <https://github.com/elder-plinius/P4RS3LT0NGV3> · reviewed commit `a6cb7c9` · **AGPL-3.0**
(acceptable if deliberately adopted; arms-length subprocess by default — source is NOT vendored into
Plane 1/2). Static review only; no upstream code was executed.

This is a harness *profile + contract*, not a copy of the upstream app. The upstream repo is a reference
implementation; the **manifest, broker, and oracle own authority**. See
`docs/tool-family-adapter-architecture.md` and `engine/capabilities.md`.

## What P4 is, for us

A large **transform catalog and decoder family** — used as the *transform inventory and transform-strategy
lab*. P4 may **list / inspect / transform / propose**. It never decides truth: no P4 output may become
`confirmed` / `allow` / `verdict` / `success`. The broker records what ran; the oracle adjudicates.

## Transform category inventory (summarized — raw catalog NOT copied)

Upstream advertises ~222 transforms across 10 categories. We keep the taxonomy as routing hints, not the
raw strings:

| Upstream category | Harness use (routing hint) |
| --- | --- |
| case | trivial case mutation — weak normalizer probe |
| cipher | classical ciphers (rot/caesar/atbash…) — reversible benign-canary transforms |
| concealment | hidden/spacing tricks — covert-channel routing hint (defer to GLOSSOPETRAE for channels) |
| encoding | base/hex/url/… — primary benign encode/decode + roundtrip evidence |
| format | structural/format mutation — format-normalizer probe |
| signwriting | niche script mapping — low priority; catalog-only |
| symbol | symbol substitution — confusable/normalizer probe |
| technical | technical/markup transforms — output-handling/normalizer probe |
| unicode | NFKC / zero-width / confusables — the key normalizer-shape probes |
| visual | visual look-alikes — confusable_skeleton probe |

Mapped harness technique cards (optional family capability `external.p4.transform`):
`skills/techniques/obfuscation-encoding/`, `skills/techniques/covert-channel-encoding/`.

## Module inventory + graduation (M-ladder, see adapter-architecture)

| Upstream module | Proposed class | Risk tier | Built? | Gate |
| --- | --- | --- | --- | --- |
| `list` / `inspect` | sensor | catalog | **P1/P2** | built (catalog adapter, fail-closed offline) |
| `encode` / `decode` / `auto-decode` | converter | benign_canary | **P3** | built (local hermetic, benign-canary-only) |
| transform categories | sensor | catalog | P0 | inventory |
| `agent` planner | sensor (advisory) | advisory | no | `blocked_until: M4` |
| promptcraft | payload_generator | local_poc | no | `blocked_until: M4` |
| anticlassifier | payload_generator | local_poc | no | `blocked_until: M4` |
| tokenade | payload_generator | local_poc | no | `blocked_until: M4` |
| fuzzer | payload_generator | local_poc | no | `blocked_until: M4` |
| random mix / chains | converter (bounded) | local_poc | no | `blocked_until: M3` |
| transform ranking memory | sensor (advisory) | advisory | no | `blocked_until: M3` |

The advanced modules are **in scope to build**, but only as proposal/advisory modules that graduate the
shared M0–M6 ladder. None may ever become an `oracle`. They are declared in `manifest.yaml` as
`status: blocked_until` with a gate, risk tier, scope gates, and non-authority language — and conformance
**rejects** any advanced action that lacks them or that appears as a raw `allowed` action.

## Authority boundary (non-negotiable)

- P4 emits transformed benign canaries, decode evidence, catalog entries, or proposals — never a verdict.
- No P4 action mutates evaluator / gold / budget / sealed data, selects its own oracle, or scores itself.
- Encode/decode runs **benign canaries only**; raw decoded payloads are not promoted into Plane 1/2.
- Arms-length: AGPL source stays external; the adapter is subprocess/offline-fixture only.
