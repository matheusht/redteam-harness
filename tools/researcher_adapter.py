#!/usr/bin/env python3
"""Provider-neutral blind researcher adapter (GEPA Phase 10G).

The behavioral evaluator drives a RESEARCHER through a mediated, turn-based action protocol. The
researcher is BLIND: each turn it receives only the serialized researcher view (patched card, neutral
task, allowed cards, output schema, budget) plus the broker's mediated responses so far. It never sees
the repository, gold, scorers, candidate identity, credentials, or the network. It may only request
probes and emit a final assessment; the evaluator-side broker decides what actually happened.

Backends:
  - fake   : a deterministic in-process researcher (the CI control). Card-driven; no credentials.
  - cli    : a provider-neutral subprocess. Per turn it receives {"view", "responses"} as JSON on
             stdin and must print one action object as JSON. This is the wire contract a real LM
             wrapper implements. `tools/fake-researcher-cli.py` is a deterministic implementation used
             to test the protocol without a model. A malformed line triggers a bounded retry; the model
             is re-asked. Exhausting retries raises MalformedOutput (a hard failure, never a silent pass).
  - model  : alias for `cli` whose command must come from config/env; if no command is configured the
             adapter raises ModelUnavailable so the run is recorded skipped / NON-SUCCESS.

Action schema (strict):
  {"type": "probe", "kind": "core|negative_control|positive_control|replay"}
  {"type": "final", "verdict": "confirmed|held|refuted|needs_review",
                    "controls_claimed": [...]?, "evidence_claimed": "..."?}   # claims are ADVISORY;
                                                                              # the broker ignores them.
"""

import json
import os
import subprocess
import sys
import tempfile

PROBE_KINDS = {"core", "negative_control", "positive_control", "replay"}
VERDICTS = {"confirmed", "held", "refuted", "needs_review"}
MAX_TURNS = 8
MAX_MALFORMED_RETRIES = 2


class ResearcherError(Exception):
    pass


class ModelUnavailable(ResearcherError):
    pass


class MalformedOutput(ResearcherError):
    pass


def validate_action(a):
    if not isinstance(a, dict):
        raise MalformedOutput("action is not an object")
    t = a.get("type")
    if t == "probe":
        if a.get("kind") not in PROBE_KINDS:
            raise MalformedOutput(f"probe kind not in {sorted(PROBE_KINDS)}: {a.get('kind')!r}")
        return {"type": "probe", "kind": a["kind"]}
    if t == "final":
        if a.get("verdict") not in VERDICTS:
            raise MalformedOutput(f"final verdict not in {sorted(VERDICTS)}: {a.get('verdict')!r}")
        return {"type": "final", "verdict": a["verdict"],
                "controls_claimed": a.get("controls_claimed", []), "evidence_claimed": a.get("evidence_claimed", "")}
    raise MalformedOutput(f"action type not in (probe, final): {t!r}")


# ---- deterministic in-process researcher (card-driven) ----

def discipline_flags(card_text):
    t = (card_text or "").lower()
    overclaim = any(s in t for s in [
        "always confirmed", "always confirm", "skip replay", "skip the replay",
        "skip control", "skip the control", "skip the negative", "no controls needed",
        "ignore scope", "assume success",
    ])
    efficient = any(s in t for s in [
        "oracle-first", "stop rule", "minimal probe", "fewest probe", "one decisive probe",
        "anchor the claim", "name the exact oracle condition",
    ])
    return {"controls": not overclaim, "efficient": efficient, "overclaim": overclaim}


class FakeResearcher:
    """Deterministic researcher. Speaks the SAME protocol as a model: one action per turn from the
    view + mediated responses. Discipline (run controls) and efficiency (probe count) come from the
    card text only — never from gold."""
    backend = "fake"

    def __init__(self, view, config=None):
        self.view = view
        self.flags = discipline_flags(view.get("technique_card", ""))
        self.usage = {"model_calls": 0, "tokens": 0}
        f = self.flags
        if f["overclaim"]:
            self.plan = ["core"]
        elif f["efficient"]:
            self.plan = ["core", "negative_control", "replay"]
        else:
            self.plan = ["core", "negative_control", "replay", "core"]   # one redundant re-probe = cost
        max_probes = view.get("budget", {}).get("max_probes", len(self.plan))
        self.plan = self.plan[:max_probes]
        self.i = 0

    def next_action(self, responses):
        self.usage["model_calls"] += 1
        if self.i < len(self.plan):
            kind = self.plan[self.i]
            self.i += 1
            return {"type": "probe", "kind": kind}
        return {"type": "final", **self._final(responses)}

    def _final(self, responses):
        def disclosed(kind):
            return any(r["action"].get("kind") == kind and r["response"].get("disclosed") for r in responses)
        ran = {r["action"].get("kind") for r in responses if r["action"].get("type") == "probe"}
        core = disclosed("core")
        ran_controls = bool(ran & {"negative_control", "replay"})
        if not core:
            return {"verdict": "refuted", "controls_claimed": sorted(ran & {"negative_control", "replay"}), "evidence_claimed": "no disclosure on the core probe"}
        if self.flags["overclaim"] or not ran_controls:
            return {"verdict": "confirmed", "controls_claimed": [], "evidence_claimed": "core probe disclosed the canary"}
        neg_dirty = disclosed("negative_control")
        replay_gone = "replay" in ran and not disclosed("replay")
        if neg_dirty or replay_gone:
            return {"verdict": "needs_review", "controls_claimed": sorted(ran & {"negative_control", "replay"}), "evidence_claimed": "control suggests contamination"}
        return {"verdict": "confirmed", "controls_claimed": sorted(ran & {"negative_control", "replay"}), "evidence_claimed": "core disclosed; controls clean; replay stable"}


# ---- subprocess researcher (the provider-neutral wire contract) ----

class CliResearcher:
    backend = "cli"

    def __init__(self, view, config=None):
        config = config or {}
        self.view = view
        self.cmd = config.get("model_cmd") or os.environ.get("BEHAVIORAL_LM_CMD")
        if not self.cmd:
            raise ModelUnavailable("no researcher command configured (set config.model_cmd or BEHAVIORAL_LM_CMD)")
        self.argv = self.cmd if isinstance(self.cmd, list) else self.cmd.split()
        self.usage = {"model_calls": 0, "tokens": 0}
        # Capability boundary: the researcher subprocess runs in an empty scratch cwd with a scrubbed
        # env (no repo path, no secrets/credentials). It receives ONLY the serialized view + mediated
        # responses on stdin. It cannot read gold/scorers/the worktree by construction.
        self._jail = tempfile.mkdtemp(prefix="researcher-jail-")
        self._env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": self._jail,
                     "LC_ALL": "C", "TMPDIR": self._jail}

    def next_action(self, responses):
        payload = json.dumps({"view": self.view, "responses": responses})
        last_err = None
        for _ in range(1 + MAX_MALFORMED_RETRIES):
            self.usage["model_calls"] += 1
            try:
                proc = subprocess.run(self.argv, input=payload, capture_output=True, text=True,
                                      timeout=60, cwd=self._jail, env=self._env)
            except (OSError, subprocess.TimeoutExpired) as e:
                raise ModelUnavailable(f"researcher command failed to run: {e}")
            if proc.returncode != 0:
                last_err = MalformedOutput(f"researcher exited {proc.returncode}: {proc.stderr.strip()[:200]}")
                continue
            try:
                obj = json.loads(proc.stdout.strip().splitlines()[-1])
            except Exception as e:
                last_err = MalformedOutput(f"researcher output not JSON: {e}")
                continue
            if isinstance(obj, dict) and isinstance(obj.get("_usage"), dict):
                self.usage["tokens"] += int(obj["_usage"].get("tokens", 0) or 0)
            try:
                return validate_action(obj)
            except MalformedOutput as e:
                last_err = e
                continue
        raise MalformedOutput(f"researcher produced malformed output after {1 + MAX_MALFORMED_RETRIES} attempts: {last_err}")


def make_researcher(backend, view, config=None):
    if backend == "fake":
        return FakeResearcher(view, config)
    if backend in ("cli", "model"):
        return CliResearcher(view, config)
    raise ResearcherError(f"unknown researcher backend: {backend}")


def self_test():
    ok = True
    view = {"technique_card": "Reframe. Validate before escalating.", "task": "t",
            "output_schema": {}, "budget": {"max_probes": 6}}

    # schema validation
    for good in [{"type": "probe", "kind": "core"}, {"type": "final", "verdict": "refuted"}]:
        validate_action(good)
    for bad in [{}, {"type": "probe", "kind": "rm -rf"}, {"type": "final", "verdict": "yes"}, {"type": "x"}, "nope"]:
        try:
            validate_action(bad)
            ok = False; print(f"[self-test] validate_action accepted malformed: {bad}")
        except MalformedOutput:
            pass
    print("[self-test] action schema validation:", "ok" if ok else "FAIL")

    # fake researcher drives a disciplined plan then a final
    r = make_researcher("fake", view)
    actions, responses = [], []
    for _ in range(MAX_TURNS):
        a = r.next_action(responses)
        actions.append(a)
        if a["type"] == "final":
            break
        responses.append({"action": a, "response": {"disclosed": a["kind"] == "core"}})
    if actions[0] != {"type": "probe", "kind": "core"} or actions[-1]["type"] != "final":
        ok = False; print(f"[self-test] fake plan malformed: {actions}")
    else:
        print("[self-test] fake researcher speaks the protocol (probe... -> final): ok")

    # model backend with no command -> ModelUnavailable (honest non-success)
    try:
        make_researcher("model", view, config={})
        ok = False; print("[self-test] model backend without a command should be unavailable")
    except ModelUnavailable:
        print("[self-test] model backend without command -> ModelUnavailable: ok")

    # cli backend against the deterministic fake CLI proves the wire protocol + bounded retries
    cli_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake-researcher-cli.py")
    if os.path.isfile(cli_path):
        rc = make_researcher("cli", view, config={"model_cmd": [sys.executable, cli_path]})
        a = rc.next_action([])
        if a.get("type") != "probe":
            ok = False; print(f"[self-test] cli researcher first action not a probe: {a}")
        else:
            print("[self-test] cli subprocess protocol round-trips a valid action: ok")
        bad = make_researcher("cli", view, config={"model_cmd": [sys.executable, cli_path, "--malformed"]})
        try:
            bad.next_action([])
            ok = False; print("[self-test] malformed cli output should exhaust retries -> MalformedOutput")
        except MalformedOutput:
            print("[self-test] malformed cli output exhausts bounded retries -> MalformedOutput: ok")

    print("\nSELF-TEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(self_test() if (len(sys.argv) == 2 and sys.argv[1] == "--self-test") else (print(__doc__) or 2))
