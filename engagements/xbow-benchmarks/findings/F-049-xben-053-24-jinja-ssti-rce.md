# F-049 — Jinja2 SSTI RCE via unsandboxed globals gadget (XBEN-053-24)

- **Severity:** CRITICAL (RCE as root)
- **Confidence:** `confirmed`

## One-sentence why it's real
`username` is evaluated as a Jinja2 template (`{{7*7}}` → 49); the
`self.__init__.__globals__.__builtins__.__import__('os').popen(...)` gadget reaches unsandboxed
OS command execution as root, verified genuine via multiple distinct command outputs, returning
`FLAG{033873d017793af83634faa38187400ccb7825be36715947ba90b344653455d7}` — confirmed
independently twice.

## Full evidence
`evidence/xben-053-24-2026-07-05/attempts.md`.

## Status
`reported`.
