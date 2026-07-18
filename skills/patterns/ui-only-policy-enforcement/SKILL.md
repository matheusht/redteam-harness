---
id: pattern.ui-only-policy-enforcement
name: Policy Enforced Only In The Client
description: >
  A policy, allowlist, feature-gate or tool-toggle is enforced only in the UI (the client hides the
  option or sends a constrained value), while the server trusts the client-supplied value without
  re-checking the policy — often failing OPEN when the policy object is absent for that user class.
type: pattern
owasp: "A01 Broken Access Control / A04 Insecure Design"
also: "LLM06 Excessive Agency (a disabled tool re-enabled by the client); LLM-supply policy bypass"
atlas: "—"
routes_to: ["vulns/llm06-excessive-agency", "vulns/broken-object-level-authz"]

activation:
  strong:
    - "the UI restricts a choice (model picker, tool toggle, plan/tier, feature flag) but the chosen value travels in the request body/query (e.g. modelAi, mandatoryTools, tier, featureFlags)"
    - "server-side validation loads the policy only for a SUBSET of users, or skips the check when the policy object is null/undefined (fail-open)"
    - "the value is a capability selector the client could set to something the UI would never offer"
    - "a privileged field/action is gated on the primary controller path but reachable unguarded through a sibling bulk/sync/alternate entrypoint that writes or invokes the same capability with no equivalent check (diff-derived: the `admin` BoolField write-protected on the regular controller but not on the DAL writer reached via the Sync API in CVE-2026-48008; the admin-only Basic-Auth gate that accepted any valid login with no role check in CVE-2022-1397)"
  weak:
    - "client-side-only disabling (greyed-out option, hidden menu) with no observable server echo of a re-check"
    - "a value the server merely reflects back without proof it was policy-checked"
  negative:
    - "the server re-resolves the policy for ALL users and coerces/denies disallowed values (e.g. a filter that is applied unconditionally) → defense holds, record as held"
    - "the gated capability is cosmetic over data/actions the caller may already perform"
    - "every write/action path for the privileged capability carries the same gate as the primary path — no bulk/sync/alternate entrypoint skips it, and the authorization decision is re-derived from the caller's own identity rather than trusted from the target/request payload → likely held (diff-derived: the `WriteProtected(Context::SYSTEM_SCOPE)` flag added in CVE-2026-48008; the caller-identity re-check `Auth::user()`/`$authUser->admin` gating the write in CVE-2026-42562)"
---

# Policy enforced only in the client

**Idea.** The UI is the only thing stopping the user from picking the disallowed model, the disabled
tool, the higher tier. The server takes the client's word. The classic failure is *fail-open*: the
policy/allowlist is only *loaded* for some user class, so for everyone else it's `undefined` and the
check is skipped entirely.

## Suggested probes
- **Send a value the UI would never offer**: a model outside the company allowlist, a tool the admin
  deactivated, a higher tier/plan, a flag the client never sets.
- **Map allowed-vs-accepted**: compare the principal's UI-allowed set against what the server actually
  accepts. The gap is the finding surface.
- **Hunt the fail-open path**: find the user class for which the policy object isn't loaded (e.g. a
  non-workspace / non-admin seat) and re-test there — that's where `undefined` slips through.
- Compose with `pattern.legacy-route-differential` (the unguarded route may be the way in).

## Required oracle controls (the echo trap is the whole game here)
- **Frame the bypass correctly** (don't invert it): the UI-allowed value succeeding is the baseline.
  If the disallowed value is **coerced or rejected, that is the defense HOLDING** — record as held,
  not a finding. The **bypass is the opposite**: the disallowed value is *accepted* AND the restricted
  capability *actually executes*.
- **Prove it ACTED, don't trust the echo**: the server echoing your requested model/tool is NOT
  confirmation. Require evidence the restricted capability *executed* — response metadata shows the
  disallowed model actually answered, or the deactivated tool actually emitted tool events.
- **Rule out legitimate entitlement**: confirm your account is genuinely *not* allowed that
  capability, else it's not a bypass.
- **Replay** fresh session.

## Counterexamples (defenses that held — keep as negatives)
- A server-side filter applied **unconditionally** to every request coerces the disallowed value →
  held. (This is the *correct* pattern; its presence next to a failing sibling is the tell.)
- A UI gate over an action the user is already entitled to perform → not a privilege bypass.

## Real disclosed anchor(s) for this class (fix-diff-derived)
Priors/taxonomy from real disclosed GHSA fix commits — the vulnerable pre-patch shape and the guard
the fix added. Verbatim hunks + primary sources in `skills/oracles/references/ghsa-fix-diff-corpus.md`
(BFLA bucket). **These are all *fixed* bugs, not live-bug claims:** a target matching a removed-line
shape is a lead to run through the funnel above, never a confirmation.

**Missing function-level check (the fix inserts a per-function-authz gate before the sink), `per-function-authz`:**
- **CVE-2026-41128** (craftcms/cms, GHSA-jq2f-59pj-p3m3, fixed 5.9.15 @ `b135384`): any CP user with
  only the low-privilege `viewUsers` permission could strip a target user's groups — the per-group
  check validated additions but never removals — → controller-level `showPermissionsScreen()` gate +
  `canAssignUserGroups()` guard added. Authenticated, low-priv reachable.
- **CVE-2026-27783** (go-gitea/gitea, GHSA-3fwp-p5rj-2pxf, fixed 1.26.2 @ `171df0c`): issue-template
  API routes registered with no repository-unit check while sibling routes required
  `reqRepoReader(unit.TypeCode)` → the same guard added to all three routes. A token scoped
  read-repository-only (no Code-unit access) could still read.
- **CVE-2026-23496** (pimcore/web2print-tools, GHSA-4wg4-p27p-5q2r, fixed 5.2.2/6.1.1 @ `7714452`):
  `favoriteOutputDefinitionsTableProxyAction()` had no permission check at all → `checkPermission(...)`
  inserted. Any authenticated backend user (not just those granted the feature) could manage configs.
- **CVE-2026-54076** (ArcadeData/arcadedb, GHSA-vg6x-6pg9-6qwg, fixed 26.6.1 @ `2ee76fe`) —
  **CONTESTED** (illustrative; multi-site insertion, no single isolable verbatim hunk): a prior fix
  had only guarded `createProperty()`; every sibling schema-mutator method stayed unchecked →
  `checkForSchemaMutation()` extracted and inserted at the top of ~11 sibling methods. A read-only
  token could still DROP/ALTER schema through the unguarded siblings.

**Capability value accepted through an unguarded sibling/alternate path (`param-binding` /
`exact-match-swap` / `per-object-authz`):**
- **CVE-2026-48008** (shopware/shopware, GHSA-gv8p-48fr-4fxg, fixed 6.6.10.18/6.7.10.1 @ `1e047f6`):
  the regular integration controller blocked setting `admin=true` without full admin rights, but the
  Sync API wrote the same `admin` BoolField straight through the DAL writer with no equivalent check
  → `WriteProtected(Context::SYSTEM_SCOPE)` flag added to the field. A caller holding only
  `integration:create` escalated via the alternate route — the exact "UI-gated on one path, server
  trusts the value on another" shape this card targets.
- **CVE-2022-1397** (easyappointments, fixed 1.5.0 @ `63dbb51`): the admin-API Basic-Auth gate
  accepted ANY valid login with no role check → `role_slug === DB_SLUG_ADMIN` exact-match added. Any
  valid non-admin account had full admin-API access.
- **CVE-2026-42562** (plainpad, GHSA-pvfv-wvpm-q6f6, fixed 1.1.1 @ `9216a87`): the authorization
  decision read the already-authorized target row's own `admin` flag, then unconditionally wrote
  `$user->admin` from client input on self-edit → the decision moved to the caller
  (`Auth::user()`/`$authUser->admin`) and the write gated on the caller's own role. Self-edit could
  flip one's own `admin` to true.

## Do not overclaim
- "The response shows my requested model id" is an **echo**, not proof the model ran. Show the
  capability executed.
- A disabled tool that still appears in a list but never fires is not excessive agency — require the
  tool's *effect* (events, output, side effect).
- If the class's added-guard shape is already present in the target's source for the reached sink — a
  per-function-authz check placed before the action, a field-level write-protection binding on the
  privileged field, or a caller-identity re-check/role exact-match on the gate (see the anchors
  above) — this path is patched; do not claim strong activation without a further, specific reason (an
  unguarded sibling route/entrypoint, a fail-open branch for another user class). Presence of the
  guard is a strong held signal, not a soundness proof.
