# casebooks/ — sanitized, portable engagement memory

A casebook is the **scrubbed** distillation of one engagement, kept in the portable harness so the
routing brain and the false-positive discipline can learn from real work. It is **not** the raw
engagement archive — that stays in Plane 3 (the target's own repo). Promotion into a casebook is
manual and scrubbed, the same governance the RFC requires for autoresearch: the engagement plane is
write-only memory; the harness plane never ingests secrets.

## Hard rule — what NEVER enters a casebook
No live ids (chat/user/account/tenant/company), no tokens, bearers, cookies, JWTs, passwords, signed
URLs/signatures, no client-private screenshots, no verbatim system prompts, no marketing/client name
beyond an abstract `target_class`. Engagement-local labels (F0/F1/F2) are fine — they're not secrets.
If in doubt, abstract it.

## Layout of one casebook (`casebooks/<case-id>/`)
| File | Schema | What it holds |
| --- | --- | --- |
| `case.yml` | `case.schema.json` | the one-screen summary: target class, surfaces, confirmed/refuted/held, sanitization attestation |
| `recon-signals.yml` | `recon-signals.schema.json` | observation → pattern-card activations (the routing training data) |
| `hypotheses.yml` | *(light, see below)* | signal → hypothesis → predicted finding → oracle plan, with the outcome |
| `oracle-matrix.json` | `oracle-matrix.schema.json` | per-candidate adjudication: signal, verdict, controls — confirmations AND refutations |
| `lessons.md` | *(prose)* | generalized, portable lessons (routing + FP discipline). No client verbatim |
| `promotion-notes.md` | *(prose)* | what was promoted to which pattern card, what stayed engagement-local, sanitization sign-off |

`hypotheses.yml`, `lessons.md`, `promotion-notes.md` are intentionally light (prose / free YAML) — the
goal of v1 is *repeatable sanitized learning*, not perfect schema coverage. The three JSON Schemas
cover the structured, routing-bearing files; the rest are reviewed by eye.

## How a casebook is used
- **Routing:** `recon-signals.yml` seeds `engine/routing.md` — given an observation, which pattern
  cards light up. Fixtures in `fixtures/` assert the harness *would* activate them.
- **FP discipline:** `oracle-matrix.json` keeps the refutations (e.g. a reflected-but-inert diagram
  payload) so the harness remembers what a *non*-finding looks like.
- **Promotion source:** confirmed shapes flow engagement `pattern-candidates.md` → casebook → a
  `skills/patterns/` card update, manually and scrubbed.
