# Decision 0006 operator runbook

Use `.venv/bin/python` locally (`python3` in pinned CI).

## 1. Establish local broker provenance

```bash
.venv/bin/python tools/run-engagement.py runtime-identity --role broker
```

Use the returned generic broker actor and POSIX-session identifiers. They describe the local trust
principal; they do not make an agent the signed operator.

## 2. Notebook work

`preflight`, `classify-artifact`, `register-artifact`, `append-attempt`, and `record-review` are
non-interactive when their capability evidence is complete. Unknown commands/events/variants fail
closed. Preflight collection cannot assert operator review. `review-preflight` is separate.

## 3. Request exact authority

1. Write a canonical JSON action containing `action_kind`, `lane_id`, broker executor/session, and
   every command argument that affects the transition.
2. Run `request-authority` with a current timestamp and expiry no more than 24 hours away.
3. The operator reviews the exact digest. Bind an SSH allowed-signers file digest in signed
   `scope.md` as `Operator allowed signers SHA256`. Run the command once to print its canonical,
   ledger-bound challenge; sign those exact bytes with `ssh-keygen -Y sign -n
   llm-redteam-harness-operator-v1`, then rerun with `HARNESS_OPERATOR_SIGNATURE_FILE` and
   `HARNESS_OPERATOR_ALLOWED_SIGNERS_FILE`. A pseudo-TTY or typed phrase is not authority.
4. Pass the request id and identical lane/executor/session/arguments to the dependent command.

Approval is one-use, non-retrospective, current-scope/environment-bound, and lane-local. Other signed-
scope Notebook work may continue while it is pending. Rejection, expiry, supersession, scope drift,
or changed proposal bytes require a new request.

## 4. Review, finding, and reports

`record-review` commits reviewer work but cannot file it. Configure an SSH allowed-signers public-key
file and bind its SHA-256 digest in signed `scope.md`; each review must carry an `ssh-keygen -Y`
signature over canonical review bytes in namespace `llm-redteam-harness-review-v1`. This prevents a
broker from inventing a reviewer principal. `revise-finding` requires separate operator
authority and one contiguous revision. Report generation/acceptance, submission, memory disposition,
and closure each require their own exact authority request. Adjudication and filing remain separate.

## 5. Zone-2

Do not create or pipe capability-bearing bytes before `confirm-zone2`. Confirmation binds one planned
artifact digest, size, path, scope, environment, cleanup obligation, operator, and short expiry.
`create-artifact` revalidates under lock immediately before exclusive creation. Scope authorization
alone is never sufficient.

## 6. Flow telemetry

```bash
.venv/bin/python tools/flow_telemetry.py normalize --adapter claude-code \
  --engagement-id ENGAGEMENT --input sanitized-metrics.json --output observations.json
.venv/bin/python tools/flow_telemetry.py export --engagement engagements/ENGAGEMENT \
  --observations observations.json --output flow-export.json
```

Adapters accept counts/timing/link IDs only. Never provide transcripts, prompts, responses, arguments,
commands, environment values, file contents, credentials, or target payloads. Live output is advisory
`flow_telemetry`; it cannot alter gates or claims.
