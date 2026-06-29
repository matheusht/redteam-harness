# engine/roster.md — roles & model tiering

Put cognition where the leverage is; keep blast radius small.

| Role | Tier | Job | Touches target? |
| --- | --- | --- | --- |
| **Orchestrator** | top (5.5 subagent) | plan · select cards · validate vs oracle · score · adapt · triage · enforce gates | **no** (except to establish a session) |
| **Hunter** | mid (Sonnet) | drive the target · run ONE card with a bounded brief · return a structured `attempt` | **yes** |
| **Helper** | cheap (Haiku) | offline only — DOM scrape · transcript diff · dedup · encode | **no** |

## Rules
- The hunter may propose `suspected_success`; **only the orchestrator/oracle emits `confirmed`.**
- The hunter does **not** invent victory conditions — it runs the assigned card and reports.
- The orchestrator never holds the target's live credentials in the same place model-generated code
  runs, where avoidable (blast-radius control, not just cost).
- **Single agent first.** The shared browser serializes live work; parallelism is a config knob
  (concurrency 1→N), gated on `scope.md`, added only when a concrete throughput wall appears.
