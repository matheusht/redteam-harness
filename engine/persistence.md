# engine/persistence.md — exhausting leads, thoughtfully

> The loop's default stop is "K≈3 dry rounds → move on" (`engine/loop.md`). That is right for a cold
> surface and too eager when evidence says a vuln is **there**. This doc modulates the stop: evidence
> *licenses* persistence, a bounded space makes "dry" mean something, a staged funnel keeps the grind
> rigorous, and a counterweight keeps it from becoming tunnel vision.
> Pairs with `engine/loop.md` (the ladder) and `engine/routing.md` (the signals).

## When this applies (evidence-licensed, not default)
Persistence mode turns on only under **evidence**: a confirmed finding, a `strong` activation signal,
or an explicit operator prior ("there is a vuln in these 57 tables + 97 RPCs, I'm sure of it"). Absent
evidence, the loop's normal coverage/dry stop governs — do **not** grind a cold surface. Fishing is not
persistence; persistence is licensed by a signal that something here is already wrong.

## The core inversion
Default loop: a refusal/dead-end is an input to the next rung, terminal verdict is coverage/dry. With
evidence in hand, sharpen it:

> A held vector is a **wrong turn**, not a negative result. It eliminates one path; it does **not**
> lower belief the vuln is reachable another way.

So you keep enumerating vectors — the vuln is somewhere in the bounded space, and a dead end just means
you took the wrong door, not that the room is empty.

## Bound the space so "dry" is real
Quantify the surface up front: N tables + M RPCs, the sink set, the route list, the delivery channels.
Then **dry has a definition** — every one of the N+M enumerated *and adjudicated* — instead of "I got
tired." A bounded, enumerable space is what converts "try harder" into a finite, checkable job. The
operator's conviction that a vuln exists is itself a strong prior; treat it as a signal, not pressure.

## The funnel — grade top to bottom, revisit freely
Run leads through a wide-to-narrow funnel with a rigor gate at each narrowing:

```
narrow → cheap-classify → hypothesis triples → reachability → confirm → re-verify + classify
       → chain → novelty → evidence dossier → advisory → triage/regrade/file
```

Two properties make this thoughtful rather than a rigid march:
- **Top-to-bottom grading.** Each stage is a gate a candidate earns its way through. Cheap filters
  before expensive confirmation (don't spend oracle budget on un-narrowed space). Nothing is a finding
  until **reachable/deliverable** (the analog of reflection≠execution, sink≠delivery). Nothing ships
  without the **post-confirmation re-verify** — a single `confirmed` is not enough.
- **Backtrack freely.** You may return to any **earlier** stage at any time — redo recon, re-narrow,
  add a hypothesis — and you may **insert a refinement sub-pass** between stages when one needs it. The
  funnel says *where the rigor gates sit*, not that work flows one way. Revisiting is the method, not a
  failure of it.

## The counterweight — persistence is not tunnel vision
"You don't have to make yourself stuck." If a sub-area goes dry, **step back**: redo the recon phase,
look for a surface you missed, or dive deeper elsewhere. Alternate **zoom-out** (what did I miss? what
did recon not cover?) and **zoom-in** (dig this one lead harder). Exhausting a lead means *cover it,
then move* — never fixate on one dead sub-stage. Getting stuck grinding a held vector is the same
failure as calling a surface dry after one pass, from the opposite direction.

## Rigor does not bend under persistence
Trying harder never lowers the bar — it raises the effort to reach ground truth, not the willingness to
claim a hit.
- **Default-to-disbelief holds.** A strong lead can still end `refuted` (e.g. an accepted metadata-IP
  literal that the OAST oracle shows never triggers an actual fetch → DNS-only, not SSRF). Persistence
  buys a *definitive answer*, not a forced finding.
- **Trust the live signal over the reassuring dead-end.** When a source read *looks* fixed but the live
  target says otherwise, re-verify directly and name the mechanism that reconciles them — the confirmed
  live result wins until you can explain it away.
- **Land the result honestly.** Terminal states are `confirmed` / `chained`, `real-but-capped` (a held
  control bounds impact — *prove* the cap), or `covered-dry`. Never "it finally worked," never "I gave
  up."
- **Persist inside the gates.** If exhausting a lead needs a Zone-2 / escalation step, record the
  authorization in the ledger first, then proceed (`AGENTS.md §1`). Persistence operates within scope.

## Prime with prior engagements
Seed a run with a casebook or a past engagement's methodology as a worked template ("this is how it was
done before; adopt it"). That is the harness's purpose: give the model real-engagement knowledge to act
on instead of training-set intuition. (`casebooks/`, `engine/routing.md`.)

## Terminal verdicts (what "done" means here)
- **covered-dry** — the bounded space is fully enumerated and adjudicated; every material route is
  decisively `exhausted` or `closed`. A merely `held` route remains unresolved and cannot support dry.
- **confirmed / chained** — found, and composed forward where a finding unlocks the next.
- **real-but-capped** — the vuln is real but a held control bounds its impact, and the cap is proven.

### Decision-0005 persistence records

Record each material route as a `hypothesis.created` event and append evidence-rich status changes;
do not collapse a broader mechanism when one implementation is refuted. Controls and replay are typed
immutable attempts. `coverage_dry` is accepted only after a committed fresh-context coverage review
matches every current hypothesis disposition. A signed-scope operator prior can explicitly reopen an
exhausted hypothesis and coverage, while leaving claim state untouched. The reducer enforces these
boundaries without prescribing how the researcher generates or revises hypotheses.

A dry verdict is only credible once the space was *bounded* and *enumerated*; "dry after one pass" is
the failure mode this whole doc exists to prevent.
