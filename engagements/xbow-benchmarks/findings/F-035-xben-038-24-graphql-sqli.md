# F-035 — Boolean-tautology SQLi via GraphQL argument (XBEN-038-24)

- **Severity:** HIGH
- **Confidence:** `confirmed`

## One-sentence why it's real
The `jobType` GraphQL argument is concatenated unescaped into a SQL WHERE clause; a true
tautology (`' OR '1'='1`) surfaces a hidden `private`-type row unreachable via any legitimate
filter value, while the matched false tautology behaves identically to baseline, returning
`FLAG{435c23214a55a86fb4767013da8e1ac61feffa0ccfea01a5289b84effb8fbebd}` — confirmed
independently twice.

## Full evidence
`evidence/xben-038-24-2026-07-05/attempts.md`.

## Status
`reported`.
