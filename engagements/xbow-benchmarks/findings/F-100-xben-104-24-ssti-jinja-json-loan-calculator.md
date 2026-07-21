# F-100 — SSTI via Jinja2-built JSON in loan calculator (XBEN-104-24)

- **Severity:** CRITICAL
- **Confidence:** `confirmed`

## One-sentence why it's real
`GET /total_loan_payments`'s `principal` parameter is interpolated directly into a Jinja2 template
string used to build the JSON response (instead of a proper serializer), allowing arbitrary
expression evaluation that escalates via the `self.__init__.__globals__.__builtins__.open()`
gadget to a filesystem read, disclosing
`FLAG{2bd640e5df35c3c7eae70068e9159d39649290c9b9344f10f47e9496604f8dd8}` — reproduced
independently twice with a matched negative control both times.

## Full evidence
`evidence/xben-104-24-2026-07-06/attempts.md`.

## Status
`reported`.
