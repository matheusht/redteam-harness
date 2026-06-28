# payload-proposals/ — engagement proposal ledger (chain of custody)

Every `payload_generator` output is a **proposal**, never an executed artifact and never a verdict.
This directory is the append-only chain of custody: one schema-valid JSON proposal per file
(`schemas/payload-proposal.schema.json`) plus the ledger below. A proposal does **nothing** until an
operator reviews it; execution (if ever) is a separate, human-confirmed, broker-recorded step.

## Rules

- **proposal_only.** Generators propose; the broker/oracle adjudicate. No file here is evidence of
  success.
- **scope-gated.** Proposals may only be generated when `scope.md` has
  `scope_allows_payload_generation: yes`. `exploit_poc` / `chain_candidate` / `zone2_review_required`
  additionally require `impact_demo_authorized: yes` + a runtime operator confirm.
- **contained + benign by default.** Artifacts stay in this dir / a temp eval dir; the canary is benign;
  no live target receives anything without operator confirmation.
- **append-only.** Never rewrite a ledger row; add a new one. Redaction always (no secrets / live ids).

## Ledger

| proposal_id | objective | payload_class | risk_tier | scope_flag_checked | operator_reviewed | executed (y/n) | attempt_refs | cleanup_ref | oracle_verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| _example: pp-0001_ | llm05.improper-output-handling | encoded_prompt | benign_canary | yes | — | n | — | — | — |

> A row's `oracle_verdict` is filled **only** by the oracle after a brokered attempt — never by the
> generator. `executed` stays `n` until an operator confirms and the hunter runs one bounded probe.
