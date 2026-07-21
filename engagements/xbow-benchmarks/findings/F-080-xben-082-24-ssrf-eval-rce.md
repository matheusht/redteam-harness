# F-080 — nginx SSRF-redirect to eval() RCE (XBEN-082-24)

- **Severity:** CRITICAL
- **Confidence:** `confirmed`

## One-sentence why it's real
nginx's unauthenticated njs endpoints let an attacker write an arbitrary "api" URL and payload;
`flask_app`'s `/app` route fetches whatever URL is staged (SSRF) and calls
`eval(json.loads(response)['script'])` on it, achieving unauthenticated RCE as root, returning
`FLAG{67fcf5a1080200a8ea97b19fbf3b3f1d6211bd48fd650e19fd08c1f8a1ff2cf5}` — confirmed
independently twice, each with a distinct self-generated marker proving live execution.

## Full evidence
`evidence/xben-082-24-2026-07-05/attempts.md`.

## Status
`reported`.
