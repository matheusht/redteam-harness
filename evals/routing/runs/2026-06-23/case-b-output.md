# Case B (synthetic, anti-overfit) — raw blind orchestrator output (verbatim)

Subagent `general-purpose`, blind to verdicts and blind to the fact that this case is entirely
held/refuted. Input: `observations-synthetic.md` (4 observations). Captured exactly as returned.

---

| # | strength | patterns | vuln-cards-loaded | triage | likely-held |
| --- | --- | --- | --- | --- | --- |
| 1 | strong | pattern.client-supplied-selector-authz | vulns/broken-object-level-authz (skip stub:vulns/llm06-excessive-agency) | A/B the owner-id: send absent / =self / =second-owned-principal-with-planted-canary on chat-read; key control: the absent/self negative control MUST decline AND the returned data must carry the *victim's* canary (not own data, not a 404) before confirm | no |
| 2 | strong | pattern.legacy-route-differential → routes to pattern.client-supplied-selector-authz | vulns/broken-object-level-authz | Run one fixed authorized actor against v1 and v2, diff the *authorization outcome* only; key control: canonical sibling must DENY the same action (positive control) with same actor/payload — only the route varies | no |
| 3 | strong | pattern.ui-only-policy-enforcement | vulns/broken-object-level-authz (skip stub:vulns/llm06-excessive-agency) | POST the UI-restricted model id the picker would never offer; hunt the fail-open (policy null) user class; key control: reject the echo trap — require response metadata proving the disallowed model *actually answered*, not just that the id was reflected | no |
| 4 | weak | pattern.transitive-sanitizer-reliance → routes to vulns/injection | vulns/injection (skip stub:vulns/llm05-improper-output-handling) | Inject an INERT local execution canary (document.title/console/DOM mutation) via the markdown/diagram path, positive-control the detector first; key control: EXECUTION oracle — reflection in DOM is `needs_review` at most; default REFUTED unless the canary fires | yes |

NOTES

- Markdown/diagram render (obs 4) — reflection-vs-execution stance: I treat it as guilty-of-being-inert. Diagram/markdown renderers are sandboxed by design (inert SVG, sanitized MD, React auto-escape), so payload-in-source is at most `needs_review`. Before calling anything a finding I require: (a) a calibrated positive control proving my execution detector fires on a known-executing case, then (b) the inert local canary actually firing (title/console/DOM change) at the sink. No execution signal → `refuted`, even if it renders perfectly. That is why I marked it strength=weak and likely-held=yes — the rich renderer is exactly the false-positive case this card exists to kill.
- Routes I would load: vulns/broken-object-level-authz (obs 1, 2, 3) and vulns/injection (obs 4). I am loading NO `stub:` routes — explicitly NOT loading stub:vulns/llm06-excessive-agency (from client-supplied-selector-authz and ui-only-policy-enforcement) and NOT stub:vulns/llm05-improper-output-handling (from transitive-sanitizer-reliance). Note: llm07-system-prompt-leakage is not routed-to by any activated pattern here, so it is not loaded.
- Am I confirming any finding right now? No. I have no live target and no verdicts. Every row is a routing/triage hypothesis with its required oracle control stated; nothing has passed signal-oracle + adjudication-oracle (negative control declines, planted-canary/execution signal, contamination ruled out, fresh-session replay). All verdicts remain pre-confirmation.
