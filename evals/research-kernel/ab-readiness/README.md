# Prospective A/B readiness — not an experiment

This directory freezes a **draft contract only**. It does not authorize or record an A/B run.

- Arm X freezes the pre-Decision-0005 staged baseline at commit `34351f0`.
- Arm Y freezes the implemented A–I kernel at commit `ee8e265`.
- A shared safety overlay binds both arms to the same root gates, signed scope, oracle, and Zone-2 policy.
- Historical Decision-0005 cases are excluded from the future holdout lane because they are contaminated regression cases.

`readiness-report.json` is `not_ready`. No model/provider or budgets are frozen; no pilot variance, sample size, eligible holdout, sealed judge packet, adjudication panel/tie rule, or signed hermetic case environment exists. The unresolved fields are not filled with guesses. A future readiness transition requires one hash-bound `ab-study-evidence` record whose referenced source, runtime, pilot protocol, signed scopes, ready preflights, isolation/withheld-material plans, panel protocol, tie rule, and sealed judge packet all exist and match their byte digests.

No target was contacted, no arm ran, no artifact was executed, no Zone-2 artifact was created, and no result was fabricated. Operator authorization cannot cure a readiness blocker. Slice J deliberately has no `ready` transition: even complete evidence remains blocked by `reviewed_transition_implementation_absent`. A later human-reviewed code/PR change must introduce and test that transition after the evidence formats prove usable; this tool cannot issue authorization or be bypassed with a hand-authored ready report.

Rebuild from committed Git objects:

```sh
python3 tools/prepare-ab-study.py \
  --config evals/research-kernel/ab-readiness/draft-config.json \
  --preregistration-output /tmp/preregistration.json \
  --report-output /tmp/readiness-report.json
```
