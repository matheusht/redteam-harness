# engine/routing.md — recon → activation signals → card selection

The connective tissue between recon and the loop. Recon does not hand the orchestrator a target; it
hands it a set of **activation signals**, and those signals select which `skills/patterns/` and
`skills/vulns/` cards come into play. This is what makes "the orchestrator chooses" a *recorded,
reviewable* skill instead of relying on the model's training intuition.

## The flow
```
recon observations
  → activation signals        (name what you saw; match against pattern cards' `activation` blocks)
  → matching pattern / vuln cards   (load the exact cards by id)
  → orchestrator chooses probes     (use, ignore, or override — but record why for strong signals)
  → loop + oracle               (engine/loop.md; adjudicate every result, default-skeptical)
  → pattern-candidates / casebook   (after the engagement, scrubbed promotion)
```

## Recon must emit activation signals (before card selection)
During recon (runbook step 3), for each surface, write down the concrete observations and which
pattern cards they activate. A signal is `strong | weak | negative`:
- **strong** — matches a card's `activation.strong`; load that card and plan its probes.
- **weak** — worth a cheap look; do not over-invest.
- **negative** — the *defense is present* here (matches `activation.negative`); record it as a likely
  **held** control and a positive-control candidate, not a finding.

A `negative` signal is as valuable as a strong one: a correctly-enforced sibling is the tell that an
unguarded sibling nearby is the bug (see `pattern.legacy-route-differential`).

## Not a checklist — guided, overridable
The orchestrator MAY use, ignore, or override an activated card. But for any **strong** signal on a
**high-impact** path, record one line on why if you skip it. The point is a reviewable reasoning trail,
not a rigid gate. Selection stays deterministic (load the exact card by id, per `AGENTS.md §3`); what
routing adds is *which* ids, justified by what recon saw.

## Where the signals come from / go
- **Cards** declare their `activation` block (`strong/weak/negative`) in front matter.
- **Casebooks** (`casebooks/<id>/recon-signals.yml`) hold worked examples — observation → activation —
  that seed and calibrate this step.
- **Fixtures** (`fixtures/*routing*`) assert the harness *would* activate the right cards for a known
  casebook (e.g. an owner-id field → `pattern.client-supplied-selector-authz`).

## Hard gates still apply
Routing changes *what you consider*, never the gates. Scope, `safe_signal`, Zone-2 human-confirm,
redaction, and oracle-before-`confirmed` are unchanged (`AGENTS.md §1`). A strong activation never
authorizes an impact artifact on its own.
