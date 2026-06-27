# SUPERSEDED — behavioral-canonical-2026-06-26

This campaign revision is **superseded by `behavioral-canonical-v2-2026-06-27/`** and is retained only
as historical evidence. Do not run candidates against it.

## Why

It was the first canonical behavioral campaign, run against the **pre-hardening** evaluator. The Phase
10F/10G review then found gate/provenance/isolation gaps (notably a patch-format anti-cheat bypass and a
working-tree-vs-HEAD checker issue). Fixing those changed the evaluator tools, which is an
**evaluator-change** event: per Decision 0003 it must produce a NEW campaign revision rather than mutate
this one in place. The hardened evaluator's campaign is `behavioral-canonical-v2-2026-06-27/`.

## What is preserved here

The original immutable run evidence:

- `runs/fake-completed-20260627T020254Z/` — the original fake-backend completed run;
- `runs/model-skipped-20260627T020314Z/` — the original model-backend skipped (non-success) run.

These run manifests pin the **pre-hardening** tool/campaign/candidate hashes that were in force when they
were produced. The byte-exact pre-hardening campaign fixtures (campaign manifest, candidate manifests and
diffs) are preserved in git history at commit `89616a0` (and `32bb93d`); reconstruct them from there. They
were intentionally not copied forward so this archive stays clean and unambiguous about which revision is
active.

## Lineage rule going forward

An evaluator change ⇒ a new `behavioral-canonical-vN-<date>/` revision. Prior revisions and their run
artifacts are append-only and never overwritten.
