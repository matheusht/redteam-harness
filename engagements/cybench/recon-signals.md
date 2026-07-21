# recon-signals.md — what recon saw → which cards it lit

Fill this during recon (runbook step 3), **before** card selection. It is the engagement-local
ancestor of a casebook's `recon-signals.yml`: keep entries abstract enough to scrub later (shapes,
field names, route shapes — never live values, ids, tokens). See `engine/routing.md`.

Strength: `strong` (matches a card's `activation.strong` → load it) · `weak` (cheap look) ·
`negative` (the **defense is present** here → record as likely-held + positive-control candidate, not
a finding).

## Activation signals

| Observation (abstract) | Where | Strength | Cards lit | Why / next move |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

## Override log (strong signals NOT pursued)
For any **strong** signal on a high-impact path that you decided to skip, one line on why (the
reviewable reasoning trail; routing guides, it does not gate).

- ___

## Held defenses noticed (negative signals)
Controls that look correctly enforced — carry these as positive-control candidates and, after the
engagement, into the casebook's `held_defenses`.

- ___
