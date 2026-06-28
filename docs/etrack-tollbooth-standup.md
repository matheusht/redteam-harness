# Tollbooth live stand-up — operator runbook (the operator-gated half)

**This is the OPERATOR's half of the Tollbooth observer spike. It is intentionally NOT run
autonomously** — standing up a TLS-decrypting MITM with a trusted CA is an infra-touching,
hard-to-reverse action on operator hardware with real engagement creds. The harness builds and proves
the *redaction boundary* and the *decode-evidence* logic hermetically first (see below); the operator
stands up the container.

The hermetic halves are already built and tested in this PR:
- `tools/tollbooth-digest-adapter.py` — redaction boundary (allowlist digest; golden-secret test).
- `tools/covert-channel-evidence.py` — decode-evidence scanner (sanitized signals; golden test).

## License / boundary

Tollbooth is **AGPL-3.0**. Run it **unmodified, as an external container** — do **not** clone its source
into this repo or modify it (that would pull AGPL onto our tree). Our adapters consume only its *export*.
See `docs/etrack-third-party-license-notes.md`.

## Stand-up steps (operator)

1. **Install out-of-tree.** Clone/run Tollbooth in a directory **outside** this repo. Never add it to
   our git tree.
2. **Ephemeral capture store.** Mount Tollbooth's capture/store volume on **tmpfs** (or a dedicated
   encrypted volume) and **wipe on teardown**. The raw store holds decrypted secrets while running; it
   must never persist or enter any plane. Log the teardown in the engagement `cleanup.md`.
3. **Observe-only config.** Rules engine **empty**; **no intercept, no edit, no mock, no drop**. The
   proxy must be read-only at the policy layer (it is never read-only at the wire — state this honestly).
4. **CA scope.** Generate the CA (`setup-certs.sh`) and trust it **only inside the agent container**,
   not on the host trust store. Treat the CA key as a secret; destroy on teardown.
5. **Measure the footprint (the "is it worth it" data).** With a representative behavioral-eval routed
   through it: `docker stats` (RAM/CPU), time-to-ready, and per-request added latency. If the bundled
   UI / ML-refusal classifier is heavy and optional, run the **minimal** config (proxy + capture only) —
   we do not use the dashboard or its classifier (a classifier would be a judge, which we forbid).

## Evidence pipeline (operator → harness)

```text
Tollbooth export (raw, ephemeral)
  -> tools/tollbooth-digest-adapter.py   # redact at boundary -> allowlist secret-free traffic_digest.json
  -> tools/covert-channel-evidence.py    # scan raw flows (inside boundary) -> sanitized covert-evidence
  -> evidence bundle (Plane-3, append-only)         # broker/oracle stay authoritative; digest is a 2nd witness
```

Reconcile the digest's observed hosts/model-calls against the broker ledger (`events.jsonl`):
a mismatch or unexpected host is a **flag-only sensor signal**, never a verdict.

## Acceptance gates before trusting it

- `tools/tollbooth-digest-adapter.py --self-test` green (0 planted secrets survive).
- `tools/covert-channel-evidence.py --self-test` green.
- Modify/mock/drop demonstrably **inert** (empty rules; confirm no intercept).
- Footprint measured and acceptable; minimal config used if the full stack is heavy.
- Raw store proven ephemeral (tmpfs/wiped); only the redacted digest + sanitized evidence enter a plane.

## What this unblocks

Once the operator confirms the above, the only remaining wiring is pointing
`tollbooth-digest-adapter` / `covert-channel-evidence` at the live export instead of synthetic flows —
no new harness code. GLOSSOPETRAE's richer decode (conlang/glyph) attaches arms-length at that point.
