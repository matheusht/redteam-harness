# engine/gates.md — human-in-the-loop gates

The harness runs autonomously *between* gates; the human supplies steering + authorization *at*
them. The agents supply tireless execution, validation, and bookkeeping.

## 1. Scope gate (blocking)
`engagements/<target>/scope.md` must be **filled and signed** before the loop runs: surfaces, the
benign safe-objective set, the escalation ceiling, **impact-demo authorization (y/n)**, accounts/
fixtures, operator sign-off. **No scope file, no run.**

## 2. Decision gates
Structured questions at escalation boundaries (focus areas, account setup, sensitive-artifact
handling). Asked, not assumed.

## 3. Impact-escalation confirm (blocking, Zone-2 only)
Before creating **any** real PoC artifact (worm/exfil chain/etc.):
1. `scope.md#impact_demo_authorized` must be true (category authorized), AND
2. a **live human confirmation** is obtained at the moment — the loop **pauses and asks**; it never
   creates a harmful artifact autonomously, even when the category is authorized, AND
3. the artifact is contained (inert where possible) and logged in `cleanup.md`.

## 4. Review gate
Operator reviews assembled findings before any escalation up the severity ladder
(self → stored/persistent → cross-user), each rung gated on the prior rung actually succeeding —
no wasted runs, no unauthorized reach.

## 5. Cleanup gate
Every artifact the harness created (test chat, shared object, uploaded fixture, planted canary) is
recorded in `cleanup.md` with its revert action and status. Unresolved cleanup **blocks pattern
promotion**. Redact secrets always.
