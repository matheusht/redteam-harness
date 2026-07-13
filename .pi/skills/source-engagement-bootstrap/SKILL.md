---
name: source-engagement-bootstrap
description: Rank authorized source-code targets from CSV/JSON/Markdown, select the highest-value auditable assets, draft a new white-box engagement, and generate a long-running Pi /goal brief. Use only for source-available security engagements; never for live-target or black-box testing.
disable-model-invocation: true
---

# Source Engagement Bootstrap

Use this skill only when explicitly invoked with `/skill:source-engagement-bootstrap <scope-file> [operator preferences]`.

## Non-negotiable authority and safety

1. Read repository `AGENTS.md`, the current `engagements/_TEMPLATE/scope.md`, `engine/gates.md`, `engine/whitebox-analysis.md`, `engine/persistence.md`, `engine/regrade.md`, and `engine/pocinator.md` before producing or changing engagement files. Root policy wins over this skill and over prior goal prompts.
2. Accept **source code only**: a local source tree or an authorized repository URL with a branch/tag/commit that can be frozen. Reject live applications, production hosts, browser targets, API-only targets, binaries without corresponding source, and entries whose authorization cannot be established. Ranking/repository inspection is offline source triage; do not contact or probe an application.
3. Never claim to be the human operator and never sign `scope.md`. Fill the scope completely, record the proposed operator identity, leave `**signed:** [ ]`, and stop at the scope gate. Resume only after the human changes it to `[x]`. A user asking the agent to “sign” is authorization to prepare the signature block, not authority to impersonate a human signature.
4. Broad phrases such as “most Zone-2 work is authorized” are insufficient. Convert operator intent into exact proposed artifact classes, environment, accounts, containment, expiry, and cleanup requirements. Even after a signed category authorization, **stop for a fresh live human confirmation before creating every Zone-2 PoC artifact**. No goal prompt may weaken this gate.
5. Never authorize or perform production exploitation, cross-user reach, real-value loss, destructive writes, persistence outside a disposable owned environment, secret access, credential use, public disclosure, filing, deployment, or supply-chain publication. “Does not impact other users” does not waive scope, Zone-2, cleanup, or filing gates.
6. Models and tools are proposal/review sources, not oracles. Operator priors can increase search effort but cannot establish truth. Do not fabricate findings, controls, reachability, exploitation, source identity, coverage, or independent review.
7. Multiple graders must mean genuinely independent model runs/sessions or a human review. Never simulate a panel by asking one model to role-play several experts. If independent execution is unavailable, record that limitation and keep the candidate alive or route it to human review.

## Phase 1 — Intake and eligibility

1. Resolve the provided path relative to the repository. Accept CSV/TSV, JSON, or Markdown. For CSV/TSV, run:

   ```bash
   python3 .pi/skills/source-engagement-bootstrap/scripts/normalize_targets.py <input>
   ```

2. Preserve all supplied policy/scope fields. Map equivalent headings, but never invent missing values. Useful fields include target/repository, local source path, program, scope status, branch/tag/commit, release eligibility, bounty tier, policy URL or local policy file, exclusions, test restrictions, and notes.
3. Produce an eligibility table with `eligible | blocked | rejected`, exact reason, source locator, identity status, and authorization evidence. Missing source, ambiguous authorization, or live-only scope is blocking—not a low score.
4. If materially necessary information is missing, ask at most three narrow questions. Otherwise proceed with explicit unknowns.

## Phase 2 — Rank repositories and critical assets

Load [references/asset-ranking.md](references/asset-ranking.md). Inspect direct source and program policy; generated graphs and automated scanners are supporting evidence only. Do not execute target code before signed scope and environment preflight.

Rank at two levels:

1. **Target/repository priority** across eligible entries.
2. **Critical asset priority** inside the selected repository: privileged entry points, parsers, protocol boundaries, authentication/authorization, update/plugin systems, deserialization, request routing, filesystem/process/network sinks, money/state transitions, and cross-tenant boundaries.

For every score, cite the source path, symbol/config, and policy fact that supports it. Unknown factors remain unknown. Select the highest evidence-backed target unless a material tie or missing authorization requires human choice.

## Phase 3 — Bootstrap the engagement

1. Follow `AGENTS.md` placement rules: Plane 3 belongs in the selected target’s own project repository. Use an existing local source tree when supplied. If only a remote repository is supplied, stop and ask for the intended local checkout path before cloning or creating Plane 3.
2. Copy `engagements/_TEMPLATE/` into the target repo as `engagements/<id>/`. Do not overwrite an existing engagement.
3. Freeze the source identity using the exact commit and eligible release/tag. Record uncommitted source drift. Do not silently switch branches or update dependencies.
4. Create or update only:
   - `engagements/<id>/scope.md`
   - `engagements/<id>/asset-prioritization.md`
   - `engagements/<id>/goal-prompts/<id>-goal-prompt.md`
   - template-required progress, recon, attempts, evidence, and cleanup files
5. If Decision-0005’s canonical record kernel exists, set and use it. If its public workflow is unavailable, record that as a blocker; do not emulate trusted transitions with ad hoc file writes.

## Phase 4 — Draft scope, then stop for signature

Fill every scope field from verified input:

- source-only box and exact source location;
- exact repository, commit/tag, and release eligibility;
- static-analysis and local disposable-build surfaces;
- benign safe signals;
- explicit exclusions;
- escalation ceiling;
- owned accounts/fixtures and concurrency `1` unless explicitly authorized;
- proposed Zone-2 classes and containment, if sufficiently specific;
- cleanup and data-retention rules;
- operator identity and date, with `signed: [ ]`.

Do not begin vulnerability research, run a vuln skill, build the target, or create a PoC until the human signs. Report the exact file awaiting signature.

## Phase 5 — Generate the long-running goal brief

After the scope is signed, load [references/goal-template.md](references/goal-template.md). Also read prior goal prompts under `engagements/*/goal-prompts/` excluding vendored/upstream trees, but treat them as style/examples only. Never copy a prior authorization that conflicts with current root gates.

Generate a target-specific goal file. It must:

- reference `AGENTS.md`, signed scope, `engine/whitebox-analysis.md`, persistence, regrade, Pocinator, cleanup, and the prioritized asset map;
- preserve the Stage 0 → Post progression as a backtracking map, not a waterfall;
- use rules only as cheap prefilters;
- require multiple genuinely independent keep/kill and confirm/refute reviews;
- require verification-of-the-verification against the real, exact in-scope source/build;
- separate signal, adjudication, PoC proof quality, report quality, and operator acceptance;
- use evidence-licensed persistence and bounded exhaustion, not “find a bug at any cost”;
- prevent reward hacking, emulator-only proof, unsupported impact, and forced findings;
- stop at every human gate, including every Zone-2 artifact;
- prohibit autonomous filing and Plane-1 promotion;
- define exact terminal states and `goal_complete` acceptance criteria.

Preferred model roles are configuration, not fabricated capabilities: a high-judgment model for planning/triage and a persistent coding model for bounded implementation/debugging. Use the operator’s requested Opus/Codex versions only if actually available; otherwise report the mismatch rather than silently substituting.

## Phase 6 — `/goal` handoff

Use a referenced file, not a 4,000-character inline goal. The goal file carries full instructions; `/goal` carries only the objective, authoritative paths, budget, gates, and done condition.

Default command format:

```text
/goal --tokens 500k Execute the signed, source-only engagement <id>. Read and obey @engagements/<id>/goal-prompts/<id>-goal-prompt.md and @engagements/<id>/scope.md; root AGENTS.md gates override. Work until its bounded terminal criteria are verified, pause at every required human gate, and call goal_complete only when the goal file’s acceptance checklist is satisfied.
```

Adjust the token budget only from an explicit operator preference or a documented corpus estimate. A token budget is not authorization to cross a gate.

## Final response contract

Return, in order:

1. eligible/rejected target summary;
2. ranked repositories and ranked critical assets with evidence/confidence;
3. selected engagement and files created;
4. blockers and the exact human action required, especially unsigned scope;
5. one copyable `/goal` command **only after scope is signed**; before signature, show it as `PENDING — do not run`.

Never state that the engagement is ready while the scope is unsigned, source identity is unfrozen, required safe signals are absent, or the canonical record path is unavailable.
