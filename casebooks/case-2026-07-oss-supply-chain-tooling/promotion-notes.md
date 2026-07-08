# Promotion notes — case-2026-07-oss-supply-chain-tooling

What this engagement promotes into Plane-1, what is proposed but gated, what stays local, and the
sanitization sign-off.

## Reinforces existing/engagement-built pattern cards
| Pattern card | Reinforced by | Held counterexample / bounded-negative carried |
| --- | --- | --- |
| `skills/vulns/prototype-pollution` | F3 (flag-provider-merge, JSON.parse-literal-`__proto__` shape), F4 (approval-map lookup, plain-truthy-fallback-defeat shape), F4b (discovery-side bracket-assignment container hijack, a THIRD related but distinct sub-shape) | the JSON.parse-literal-key vs. bracket-assignment-setter distinction (several "safe" adapters trigger the setter variant, not the vulnerable one); F4b's exhaustive gadget search found no downstream consumer reading inherited properties, a genuine bounded negative on further chaining |
| `skills/vulns/workflow-step-injection` | F5 (deterministic-RNG-fed bearer token, full authorization-boundary chain closed at same-run-caller scope) | the step-completion-forgery refutation (predictable id, but no public token-only acceptance surface) and the held encryption-key-derivation code (same `runId` reused correctly, as non-secret context only) both belong on this card as counterexamples |
| `skills/patterns/legacy-route-differential` | C-staticroute-fw, as a REFUTATION | a comprehensive, same-day, CVE-citing hardening pass verified by running the project's own regression-test suite directly — the non-finding this card exists to help recognize and stop chasing |
| `skills/vulns/known-cve-exploitation` | C-ms-redos, as a REFUTATION | a public issue's own claimed reproduction that does not reproduce against the current real package — always independently re-run the claimed PoC before trusting an open issue as a live lead |

This engagement is also notable for building three of these cards from scratch, mid-engagement, from a
grounded deep-research pass (see `lessons.md`): `skills/vulns/cache-poisoning` (built but not exercised
by a confirmed finding this engagement — flagged for the next Next.js/Nuxt/SvelteKit pairing),
`skills/vulns/prototype-pollution`, and `skills/vulns/workflow-step-injection`. The latter two are
directly reinforced above.

## Proposed NEW pattern cards (operator-gated — NOT auto-created)

### `sanitizer-fixed-pass-order-reconstitution` — seeded by F1
No card exists yet; referenced in this casebook as `candidate:sanitizer-fixed-pass-order-reconstitution`.
The shape, if promoted:
- **Trigger:** a denylist-style sanitizer strips a class of dangerous byte sequences using a FIXED
  SEQUENCE of independent passes, each mutating the string once, rather than looping to a fixed point.
- **Activation:** craft an obstructing byte that (a) defeats every early, pattern-specific pass by
  breaking the exact adjacency/shape those passes require, then (b) is itself removed by a later,
  more generic catch-all pass — reconstituting the original dangerous pattern from two previously
  non-adjacent fragments that are never re-scanned.
- **Held counterexample to bake in:** a sibling call site in the same codebase that happens to run the
  same sanitizer TWICE incidentally self-heals, because the spacer byte is gone by the second pass —
  a real, in-repo illustration of why a fixed-point loop (not a single extra pass) is the correct fix.
- **Routing cue:** applies generally to ANY ordered multi-pass string-stripping sanitizer, not just
  terminal-escape/ANSI sanitizers specifically — the terminal-escape angle is this engagement's
  concrete instance, not the card's scope boundary.
- **routes_to:** would sit alongside `skills/vulns/cross-site-scripting` and `information-disclosure`
  as a sibling sanitizer-bypass shape, distinct from transitive-sanitizer-reliance (which is about
  TRUSTING a sanitizer exists at all, not about a specific sanitizer's own internal ordering flaw).

### `symlink-dereference-no-target-boundary-check` — seeded by F2
No card exists yet; referenced as `candidate:symlink-dereference-no-target-boundary-check`. The shape,
if promoted:
- **Trigger:** a recursive directory-copy or similar bulk file operation over untrusted content uses a
  dereference-symlinks flag/option, commonly added to fix a real, narrower "symlink breaks after
  cleanup" bug.
- **Activation:** a symlink inside the untrusted content resolves to a target OUTSIDE the expected
  source boundary; with no post-resolution boundary check, the operation silently reads/copies real,
  external content the untrusted content's author should not have access to.
- **Escalation multiplier to check for every time:** does anything downstream (an agent prompt, a
  build step, a rendering pipeline) automatically read from the directory now populated by this
  operation? If so, silent disclosure escalates to automatic exposure/exfiltration with no separate
  bug needed.
- **Held counterexamples to bake in:** an allowlist-based path-safety check present elsewhere in the
  SAME codebase for a related but different untrusted-path scenario (proves the team knows the general
  pattern, just missed this specific instance); a crafted-`..`-tree-entry escalation attempt refuted by
  the underlying VCS tool's own hardened checkout logic; a symlink-loop DoS attempt refuted by the
  runtime's own bounded-hop error handling.
- **Routing cue:** once one instance is found, grep the WHOLE codebase for the same
  dereference-copy call shape before closing the finding — this class recurs within one codebase more
  often than it appears in only one place (see `lessons.md`).
- **routes_to:** overlaps `skills/vulns/path-traversal-lfi` but is specifically about SYMLINK
  resolution rather than path-string construction — worth a distinct card so the routing brain doesn't
  conflate "check for `..` in a path string" with "check where a followed symlink actually resolves."

## Stayed engagement-local (NOT promoted)
- Exact npm package/version pins, exact commit hashes, exact GitHub file:line permalinks, and the
  submitted HackerOne report bodies (title/CVSS-vector reasoning/exact prose) — those stay in the
  engagement's own `reports/`, `findings/`, and `evidence/` directories in Plane 3.
- PoC source code and packaged zip contents for all five findings — mechanism-level description only
  crosses into this casebook.
- The two remaining open threads on the agent-skill install/registry CLI project noted honestly as
  not-yet-investigated in the source engagement (prompt-injection risk in the agent-invocation prompt
  path beyond the confirmed disclosure escalation; a well-known-URL provider SSRF surface; a
  plugin-manifest supply-chain angle) — not findings, not promoted, just an honest open-threads note
  kept in Plane 3's own `progress.md`.
- The sibling static-routing framework's architecture-read-only conclusion on WS-upgrade-bypassing-
  route-rule-auth (recorded as likely-held but not backed by a dedicated existing test the way the
  other candidates for that project are) — kept as a lower-confidence internal note, not elevated to a
  `held_defenses` entry in `case.yml` since it wasn't exhaustively proven.

## Sanitization sign-off
Operator-scrubbed 2026-07. Verified `program-policy.md` before naming any project: Gold-Standard-Safe-
Harbor, Coordinated Vulnerability Disclosure, CVE'd findings go public 30 days after CVE publication —
but report/PoC/communications carry their own 2-year confidentiality obligation requiring the vendor's
written consent for further disclosure, which is a narrower guarantee than "publish freely once fixed."
This casebook is written for the operator's own private harness memory, not public disclosure. Per the
harness's own hard rule ("no marketing/client name beyond an abstract target_class"), the vendor/
platform name and every named project identity are abstracted out of all six files — an earlier draft
incorrectly kept them, citing a nonexistent repo precedent for doing so; corrected on independent
audit, 2026-07, since no such precedent actually exists anywhere in this harness. Every mechanism is
abstracted to pattern-shape level rather than reproducing submitted-report prose, exact CVSS-vector
strings, PoC code, or file:line permalinks. Grepped every engagement evidence/report/finding
file for credential-shaped strings; none found beyond the engagement's own benign PoC marker literals,
which are also excluded from this casebook. No live user/tenant/session ids, cookies, tokens, or
signed URLs exist in the source material at all, since this was a source-audit/local-repro engagement
with no live target. Re-review before this casebook is ever shared outside the operator's own harness.
