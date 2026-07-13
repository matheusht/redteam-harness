# Decision 0005 research-kernel telemetry

Generate a deterministic, complete-funnel export from authoritative engagement records:

```sh
python3 tools/run-engagement.py export-telemetry \
  --engagement engagements/<id> --output /tmp/<id>-telemetry.json
python3 tools/run-engagement.py score-telemetry --file /tmp/<id>-telemetry.json
```

The versioned contract is `schemas/research-telemetry.schema.json`. Export walks every
`candidate.proposed` event; callers cannot supply a selected-only denominator. Candidate outcome
reviews must be independent, fresh, and later than ex-ante confidence before the export is called
`calibration`. Otherwise it is routing/performance `telemetry`, and Brier score remains null.

Wall, model, tool, target-call, token/cost, and human-review fields remain separate. Small samples are
reported as such. Output never deletes cards, changes prompts, promotes memory, or enables a bandit.
