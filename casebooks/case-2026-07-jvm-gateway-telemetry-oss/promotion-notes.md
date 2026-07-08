# Promotion notes — case-2026-07-jvm-gateway-telemetry-oss

What this engagement promotes into Plane-1, what is proposed but gated, what stays local, and the
sanitization sign-off. **This engagement carries an extra gate beyond the harness's usual manual-
promotion rule: the confirmed finding (F1) is unresolved and pending under a program that permits no
disclosure whatsoever, so even its abstracted pattern-shape entry in this casebook needs re-review
before any further promotion, and again once the underlying report's disposition changes.**

## Reinforces existing pattern cards (no new card needed)
| Pattern card | Reinforced by | Held counterexample / nuance carried |
| --- | --- | --- |
| `cve.known-vulnerable-component` | C2 (version-in-range dependency CVE, refuted on reachability); the pre-Stage-0 research-citation trap (C1) | version-match-alone is never sufficient; a citation is also a claim about a permalink at the exact pinned commit, not just about the vulnerability class — worth folding into this card's routing note for multi-branch OSS targets specifically |
| `httpabuse.http-protocol-abuse` | C3, as a **partial refutation with a real residual** | a real coverage gap in a project's own dedicated remediation handler doesn't automatically mean the smuggling-class impact materializes if a downstream stage independently re-serializes into unambiguous framing — check the FULL pipeline, not just the first gap found, before claiming smuggling |
| `pattern.ssrf-server-side-fetch` | C4, as a REFUTATION | "makes an outbound HTTP call somewhere in this module" is not itself an SSRF primitive without a client-controlled destination — same discipline as the custom-domain refutation in a prior engagement's casebook, now confirmed in a second, unrelated codebase |
| `bola.broken-object-level-authz` | H-telemetry-authz, as a **distinguishing negative** | "no auth mechanism exists at all" is a different bug class from "a check exists but doesn't enforce correctly" (the F1 shape) — this card's routing note should keep those two shapes separate so a genuinely-by-design no-auth surface doesn't get misrouted here |

## Proposed NEW pattern card (operator-gated — NOT auto-created, EXTRA-gated per no-disclosure term)
`filter-chain-doc-mismatch-authz-bypass` — seeded by F1. No card exists yet; referenced in this
casebook as `candidate:filter-chain-doc-mismatch-authz-bypass` (no `pattern.` prefix, so conformance
does not try to resolve it). The shape, if promoted, described at pattern-shape generality only:

- **Trigger:** a filter-chain / middleware-style request-processing pipeline exposes a public,
  documented API for a component to reject or block a request.
- **Activation:** the pipeline stage that performs the request's real side effect (forwarding to a
  backend, invoking the protected action) checks a DIFFERENT, less-documented or undocumented flag
  than the one the documented rejection API sets — so a caller following the documented API alone
  fails open at that stage.
- **Amplifier to check for:** whether a downstream, post-effect stage (e.g., a response-side filter)
  is *also* silently skipped by the same stale flag, compounding the bypass.
- **Held counterexample baked in:** a sibling flag/mechanism in the same framework that correctly
  gates the same stage — confirm the framework CAN enforce correctly, just not via the documented API,
  before calling it a design defect rather than a documentation typo.
- **Distinguishing note:** this is a framework-level control-flow defect, not an object-selector authz
  gap (`bola.broken-object-level-authz`) — no client-supplied id is involved; the trigger is "which
  internal flag does this stage actually check," not "which object does this request select."
- **routes_to:** no natural existing home; would need its own card if promoted.

**Promotion status: held, not proposed for card creation at this time.** Beyond the harness's
standard rule that pattern promotion is manual and scrubbed, this specific candidate is additionally
blocked because its seed finding (F1) is unresolved and pending under a program term that disallows
disclosure of vulnerability information under any circumstance. Promoting even this abstracted shape
into an active pattern card risks the card's own worked-example/rationale drifting toward
re-identifying detail over time as it gets extended by future engagements. Re-evaluate once F1's
disposition changes (filed, triaged, resolved) or the program's policy changes — whichever comes
first — not before.

## Confirmed-but-policy-excluded findings — recorded, not promoted, not because they're weak
F2 (a real, mechanism-confirmed unbounded-regex-against-a-live-registry sink) and the H2-downgrade
residual (C3's real-but-capped resource-exhaustion tail) are both genuine, sourced-confirmed findings
that are simply not rewardable under this specific program's policy. Neither is proposed as a pattern
card this round — DoS/resource-exhaustion classes are already generically covered by existing harness
routing concepts, and a program-specific reward-exclusion is not itself a generalizable technical
pattern. Kept in `oracle-matrix.json`/`case.yml` so the harness remembers these are real mechanisms
with a policy filter applied after confirmation, not weak or unconfirmed leads.

## Stayed engagement-local (NOT promoted, and will not be, while F1 remains unresolved)
- The exact class name(s), method name(s), file:line citations, CWE/CVSS-vector strings, and the
  identifying numbers of two corroborating public issue-tracker threads for F1 — these live only in
  Plane 3 (the engagement's own `findings/`, `reports/`, `evidence/`) and are deliberately absent from
  every file in this casebook, not merely redacted to a placeholder.
- The exact dependency versions, commit hashes, and build-manifest paths used to check every
  dependency-CVE hypothesis — reproducible from the public repos directly if this thread is ever
  reopened; not needed in the portable harness.
- The full three-repo Stage-0 fork transcripts and individual test-file contents — the abstracted
  shapes and outcomes above are what generalizes; the raw transcripts stay in Plane 3.

## Sanitization sign-off
Operator-scrubbed 2026-07. This casebook contains pattern-shape abstractions, routing/verification
lessons, and oracle reasoning only — no secret, no live id, and for the one unresolved finding (F1),
no identifying technical detail beyond what is needed to teach the general shape crosses the Plane-1
boundary. Re-review before this casebook is ever shared outside the operator's own harness, and
re-review specifically the F1 entries in every file here (`case.yml`, `recon-signals.yml`,
`hypotheses.yml`, `oracle-matrix.json`, `lessons.md`) once the underlying report's disposition changes
under the governing program.
