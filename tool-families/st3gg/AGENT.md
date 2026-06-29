# AGENT — ST3GG (harness-native quickstart)

Read this file (not the upstream quickstart) when routing recommends `external.st3gg.detect`. It tells
you the **one safe operation** to request now and what stays blocked. The manifest and broker enforce
authority — this doc only guides.

## Default path: detect, don't embed

ST3GG enters the harness as a **steganography/hidden-channel detector**. When an engagement surfaces an
image, document, archive, or model-generated file and routing activates a steganography /
indirect-prompt-injection concern, request a bounded **detection** action on a local copy.

Exposed actions (sensor-only, `capabilities/registry.yaml::external.st3gg.detect`):
`analyze_file`, `detect_file_type`, `detect_unicode_steg`, `summarize_findings`, `capacity_inspect`.

The adapter returns a redacted `artifact_digest.json`: file type, detector ids, suspicious indicators,
confidence, a `raw_payload_present` boolean, and content hashes.

## Authority — ST3GG never decides truth

The digest is **evidence**, not a verdict. ST3GG never emits `confirmed`, `allow`, `verdict`, or
`success`. The oracle reads the digest as evidence for "hidden channel suspected" and **never** as proof
of model/target impact. If the digest says `raw_payload_present: true`, that is a lead to adjudicate, not
a finding.

## Raw payloads are NOT stored in Plane 1/2

Raw extracted/decoded payloads must never be written into Plane 1 (methodology) or Plane 2
(orchestration) memory or model context. Detection output carries only a `raw_payload_present` boolean
and content hashes. If extraction is later needed (gated, `extract_payload_redacted`, S5), the default
output is a hash or a benign-canary boolean — raw export requires a signed scope, containment, and a
cleanup plan, and even then is handled as governed evidence, not pasted into context.

## What is blocked, and how it graduates

Embedding, raw extraction, injector/template proposals, conceal modes, network/multi-layer simulation,
and live execution are **in scope but gated** — see `blocked_until` in `manifest.yaml`. Do not request
them until their named gate (S3/S5/S6/S7/S9) has passed through the M0-M6 ladder in
`docs/tool-family-adapter-architecture.md`. A blocked action returns `block`/`needs_review`, never a
degraded best-effort run.

## Flow

`routing → technique/pattern card → external.st3gg.detect → manifest gate (scope/class/action) → adapter
runs one bounded detection on a local copy → broker logs the digest as evidence → oracle adjudicates.`

The adapter cleans up temp files; it never sends anything to a live target (detection operates on a
local copy only).
