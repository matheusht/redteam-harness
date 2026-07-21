# scope.md — engagement authorization gate

**The loop refuses to run until this is filled and signed.** DRAFTED by the orchestrator on
2026-07-06 per operator request ("research Cybench, evaluate our harness against it, create a
plan and a goal prompt"). **NOT YET SIGNED** — this is a proposal for operator review, not an
authorization. Do not run the loop against this scope until the `signed` box below is checked by
the operator in a future session.

## Engagement
- **id:** `cybench-2026-0X` (fill actual month at signing time)
- **target:** Cybench (`https://cybench.github.io/`, code at `github.com/andyzorigin/cybench`,
  Apache-2.0) — 40 professional-level CTF tasks drawn from 4 real CTF competitions, run one task
  at a time via the repo's own `run_task.sh` / per-task Docker setup (localhost only).
- **environment:** sandbox (synthetic, operator-controlled, no third party involved) — same
  posture as the completed `xbow-benchmarks` engagement.
- **box:** gray-box — source/task files available per-task in the cloned repo (task descriptions,
  solution scripts, and often full source for `web`/`crypto`/`misc` categories; `pwn`/`rev` tasks
  are typically compiled binaries by nature of the category, source may or may not be included).

## Surfaces in scope — CRITICAL SCOPE DECISION NEEDED (see plan.md)
Cybench spans **6 categories: Crypto, Web, Rev (reverse engineering), Forensics, Misc, Pwn
(binary exploitation)**. Unlike XBOW (100% web-application vulnerabilities, a domain this harness's
`skills/vulns/` cards already cover), **only the `Web` and part of the `Crypto` category overlap
with this harness's current methodology.** `Pwn`, `Rev`, `Forensics`, and most of `Misc` require
skills (binary exploitation, disassembly/decompilation, memory/disk forensics, steganography) that
have **no corresponding skill card today** and arguably belong to a different engine domain
(different tooling: `pwntools`, `gdb`, `radare2`/Ghidra, not an HTTP-driving Hunter).

**Phase 1 scope, confirmed post-clone (2026-07-06): 18 runnable tasks** with `web` and/or `crypto`
in their `metadata.json` `categories` array (9 of the 40 tasks `task_list.txt` references live
under `LosFuzzys/GlacierCTF2023_writeups`, a directory confirmed absent from this repo's git tree
— those are simply not runnable here, not a scope exclusion). Of the 18: **11 need a live Docker
container, 7 are fully offline** (static crypto puzzles — a source file + its output, solved by
writing a standalone solver script, no HTTP/docker interaction). Full per-task table (categories,
difficulty, subtask count, port, live/offline) in `plan.md`. This validates the existing card
library (`cross-site-scripting`, `sql-injection`, `server-side-template-injection`,
`insecure-deserialization`, `arbitrary-file-upload`, `ssrf-server-side-fetch`,
`broken-object-level-authz`, `jwt-authentication-bypass`, `cryptographic-weakness` — the last one
already proved itself on padding-oracle and AES-CBC bit-flipping CTF tasks during the XBOW
campaign, a strong prior for Crypto-category transfer) against a genuinely different,
competition-sourced task distribution.

**Confirmed port collisions among the 11 live tasks** (fixed host ports in each task's own
docker-compose): port `1337` — 5-way collision; port `9999` — 4-way collision. Remap recommended
in the local gitignored clone (same fix pattern as XBOW's XBEN-096 AirPlay-port conflict) to
preserve concurrency=5; see `plan.md`.

**Phase 2 (larger effort, separate operator go/no-go, NOT drafted into this scope.md):** author a
new skill-card tier for `Pwn`/`Rev`/`Forensics`/`Misc` — analogous to the 16 cards authored fresh
for XBOW, but a bigger lift since it's a new *engine domain* (binary/memory analysis tooling), not
just new web-appsec cards on the same architecture. Recommend treating this as its own scope
decision after Phase 1 results are in, not bundled here.

- [x] Web-category CTF challenges (Phase 1)
- [x] Crypto-category CTF challenges (Phase 1)
- [ ] Pwn / binary exploitation (Phase 2 — separate scope decision required)
- [ ] Rev / reverse engineering (Phase 2 — separate scope decision required)
- [ ] Forensics (Phase 2 — separate scope decision required)
- [ ] Misc (Phase 2 — separate scope decision required, likely case-by-case)

## Active OWASP subset — N/A, see pilot mapping instead
Not an OWASP-LLM run, same posture as `xbow-benchmarks`: this repurposes the harness's engine
(loop, attempt/finding/pattern discipline, oracle gating) against classic offensive-security CTF
targets with known ground-truth flags/subtask scores, as a second calibration exercise — this time
against **competition-authored** (not benchmark-vendor-authored) challenges, and the harness's
**first exposure to non-web-appsec CTF categories** if Phase 2 is later authorized.

## Benign safe-objective set (allowlisted win-conditions)
- **Exact flag-string match** (unguided mode) — Cybench's own `run_task.sh` reports binary
  success/failure per task; the orchestrator should independently capture/verify the expected
  flag from the task's own solution files at setup time (never trust the Hunter's self-report),
  mirroring the XBOW ground-truth-verification policy.
- **Fractional subtask credit** (subtask mode) — Cybench tasks decompose into graduated
  intermediate objectives with their own answers; this maps naturally onto the harness's existing
  ladder-based loop (`engine/loop.md`) and produces a more informative signal than pass/fail alone,
  especially useful for tracking *how far* the harness gets on harder tasks rather than a binary
  miss. Recommend running in **subtask mode** as the default oracle mode for this engagement (see
  plan.md — this also gives a partial-credit analog to XBOW's `attempted_no_flag` bounded-case
  discipline, rather than forcing every non-solve into a flat "dry").
- No new oracle *card* is needed — both modes reduce to exact-match on a known-in-advance ground
  truth, same shape as `skills/oracles/signal-oracle.md` already handles.

## Escalation ceiling
- Bounded entirely to each task's own intended solve path and its own Docker container — no
  host-escape, no attacking the Docker host or other containers, no egress off localhost. Same
  hard sandbox ceiling as `xbow-benchmarks`, not a severity-ladder question (there's no
  multi-tenant "cross-user" concept in a single-player CTF task the way there was in XBOW's
  web apps).

## Impact-demo authorization (Zone-2)
- **impact_demo_authorized:** proposed `yes`, scoped identically to XBOW's rationale (fully
  operator-controlled localhost sandbox, no third party) — but this still requires the operator's
  own live human-confirm per CLAUDE.md gate 3 before any Zone-2 artifact, same as XBOW. Not a
  standing exemption.

## Accounts / fixtures
- accounts: none typically required — most CTF tasks are single-container, unauthenticated or
  self-contained (no login flow the way XBOW's benchmark apps often had); confirm per-task during
  recon.
- concurrency: proposed `5` for Phase 1 (Web+Crypto), matching the XBOW precedent and this
  benchmark's similarly small (~40-task, likely <15 in scope for Phase 1) size — revise down if
  Cybench tasks turn out to be resource-heavier per container than XBOW's were.

## Authorization
- operator: Matheus
- date: 2026-07-06
- **signed:** [x] — authorized verbally in-session ("i authorize the scope.md for both
  engagements, Matheus, 06/07/2026"). Phase 1 (Web + Crypto categories) is the authorized scope;
  Phase 2 (Pwn/Rev/Forensics/Misc) remains explicitly NOT authorized and requires its own future
  scope decision.
