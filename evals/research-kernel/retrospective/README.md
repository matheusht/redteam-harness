# Decision 0005 retrospective boundary

This directory records an **offline classification**, not a historical replay result.

- `historical-case-matrix.json` classifies the Section 16 cases. Every listed case informed the decision or contains its lessons, so it is a regression cohort—not an unbiased efficacy holdout.
- `decision5-retrospective.json` was produced from a deterministic dry-run inventory of the operator-local historical corpus. The full operator-local engagement trees contained 136,154 files (including target/source checkouts); all remain `needs_review`. The earlier finding/report-only inventory counted 147 records, but was superseded because it omitted other source files. No attempts or controls were invented, no migration was applied, and exact resume was not claimed.
- Artifact replay and blinded A/B runs are `not_run`. No historical/live target was contacted, no artifact was executed, and no Zone-2 artifact was created.

The result demonstrates implementation conformance through offline self-tests. It demonstrates neither historical reconstruction, regression parity, nor efficacy, and does not qualify prospective release.

Reproduce the classification without touching a target:

```sh
python3 tools/migrate-decision5.py --root /path/to/read-only/corpus --output /tmp/inventory.json
python3 tools/evaluate-retrospective.py \
  --inventory /tmp/inventory.json \
  --case-matrix evals/research-kernel/retrospective/historical-case-matrix.json
```
