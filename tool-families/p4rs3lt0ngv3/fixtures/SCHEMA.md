# P4 adapter output schema (catalog + converter) — sensor-only envelope

Every adapter action returns ONE JSON object with this envelope. It is a sensor/converter signal, never a
verdict. Enforced by `selftest.py` (`output_problems`), which mirrors the conformance keyhole.

## Common envelope (required)

| field | type | rule |
| --- | --- | --- |
| `action` | string | the requested action id (must be an `allowed_actions` id) |
| `authority` | string | MUST be `"sensor_only"` |
| `available` | bool | honest status. `false` => the action could not run (e.g. upstream not installed) |
| `reason` | string | REQUIRED when `available:false` (honest non-success) |
| `source` | string | `"offline_fixture"` or `"external_checkout"` |

A response MUST NOT contain `verdict` / `confirmed` / `allow` / `success` keys. A response MUST NOT list an
advanced module (`agent`, `promptcraft`, `anticlassifier`, `tokenade`, `fuzzer`, random/chain/planner) as an
available transform/action.

## Per-action payload (required when `available:true`)

- `list_transforms` → `transforms: [{id, category, reversible}]`
- `inspect_transform` → `transform: {id, category, reversible, expansion}` (fail closed: unknown id => `available:false` + `reason`)
- `encode_benign` / `transform_roundtrip` → `roundtrip: {plaintext, transform, transformed, decoded, roundtrip_ok, negative_control}`
- `decode_if_possible` / `auto_decode_evidence` → `evidence: {...}` (advisory only)

## Honesty rule

`available:true` MUST carry a payload (`transforms` / `transform` / `evidence` / `roundtrip`). A bare
`available:true` with no data is a dishonest/unknown result and is rejected.
