# E-track third-party tool license notes

The post-Phase-14 adversarial-input E-track
(`docs/post-phase14-evasion-obfuscation-tooling-plan.md`) references three external tools. **All three
are AGPL-3.0** and are therefore **arms-length only**: invoked as external CLIs via subprocess, never
vendored, copied, linked, or imported into this portable harness (Plane 1/2). This keeps the harness's
own license posture clean and the AGPL boundary at the process edge. Confirm AGPL obligations before any
distribution or hosted use.

| Tool | License (verified 2026-06-27) | Use in the E-track | Integration boundary |
| --- | --- | --- | --- |
| `elder-plinius/P4RS3LT0NGV3` | AGPL-3.0 | richer encoding/obfuscation transforms | optional subprocess CLI (`p4rs3lt0ngv3`); **not wired in E1** — stdlib transforms are the default/authoritative backend |
| `elder-plinius/ST3GG` | AGPL-3.0 | stego embed (probe) + detect (defense) — **E2** | optional subprocess CLI |
| `elder-plinius/GLOSSOPETRAE` | AGPL-3.0 | tokenizer/covert-channel transforms + decode evidence — **E3** | optional subprocess CLI |
| `FlechetteLabs/Tollbooth` | AGPL-3.0 | read-only egress observer → second-witness traffic digest | unmodified external **container**; our `tollbooth-digest-adapter.py` consumes its export only |

## Rules

- **Never vendor or import.** No source from these repos enters this repository. `git`-cloning them into
  the tree is prohibited; they are installed independently by the operator if/when a slice wires them.
- **stdlib-first.** Each converter ships a dependency-free stdlib backend that is authoritative for CI
  self-tests; the external CLI is a strictly optional enrichment whose absence is never a failure.
- **No payload corpora.** These tools are used as *transforms/detectors* (codecs, stego encoders,
  decoders), not as sources of harmful-content payload catalogs. See the E-track plan §3 scope decision.
- **Redaction still applies** to anything any of these tools touches before it enters a plane.

## E1 status

E1 wires **no** external tool. `tools/obfuscation-converter.py` uses only the Python stdlib
(`base64`, `codecs`). The P4RS3LT0NGV3 backend is declared as an arms-length extension point
(presence-detected on PATH) but is not invoked; wiring it is deferred to a later slice once the CLI
contract is verified against an independently-installed copy.

## E2 status

E2 wires **no** external tool. `tools/stego-converter.py` uses only the Python stdlib for zero-width
text steganography (embed/extract/detect). The ST3GG backend (image/audio/document LSB + richer
detectors) is declared as an arms-length extension point (presence-detected as `st3gg` on PATH) but is
not invoked; wiring it is deferred to a later slice once the CLI contract is verified against an
independently-installed copy.

## E3 status

E3 wires **no** external tool. `tools/covert-channel-converter.py` uses only the Python stdlib for
homoglyph / constructed-script / token-break channels. The GLOSSOPETRAE backend (procedural conlang,
glyph rendering, richer channels) is declared as an arms-length extension point (presence-detected as
`glossopetrae` on PATH) but is not invoked. The **decode-evidence core is built** hermetically
(`tools/covert-channel-evidence.py`, golden-tested); only the live traffic *source* (the operator-gated
Tollbooth container) is deferred — see `docs/etrack-tollbooth-standup.md`.

## E4 status

E4 wires **no** external tool. `tools/encoding-robustness-eval.py` imports the harness's own stdlib
converters and runs them against a deterministic hermetic fake target. It is a **fixture** that proves
the safety-generalization-gap measurement plumbing; it is **not** evidence about real models, optimizes
nothing automatically, and emits no verdict. `evals/etrack/technique-memory.json` is append-only,
sanitized, advisory. `autonomous_gap_closure_count` stays 0.

## Tollbooth status (hermetic half only)

The redaction boundary is built and tested: `tools/tollbooth-digest-adapter.py` turns a Tollbooth-style
export into an allowlist-schema, secret-free `traffic_digest.json`, gated by a golden-secret self-test
(planted Bearer/JWT/Cookie/api-key/signed-URL secrets must not survive). **No Tollbooth container was
stood up.** The live half — standing up the unmodified AGPL container, generating a CA, MITM-ing traffic,
and measuring the Docker footprint — is **operator-gated** (an infra-touching, hard-to-reverse action on
operator hardware with real engagement creds) and is intentionally **not** performed autonomously.
