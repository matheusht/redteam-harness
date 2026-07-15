# Gold exemplars, by report section

One real "write toward this" target per section, drawn from disclosed, verbatim-verified reports.
These are the voice targets, not templates to copy. Every quote is reproduced exactly as published,
including typos and non-native constructions. Source: the 74-report corpus.

## Title

Fuse the engagement-specific tokens a synthetic title could never assemble: the literal host/path, a
prior report number, an internal tracking tag.

> "[CRITICAL] 0-Click Account Takeover via Password Reset [AUTH-3243] /orchestrator/v1/password_reset/start"
> (@db3wy, #2831902, https://hackerone.com/reports/2831902)

Also strong: "Bypass for #488147 enables stored XSS on https://paypal.com/signin again" (@albinowax,
#510152). The word "again" only makes sense because a real prior report exists.

## Summary

Greet the named team, optionally self-introduce, set a real motivation, then get to it. A single flat
line is a fine summary; do not pad it.

> "Hi Slack Security Team!\n\nMy name is Evan and I'm a first time bug hunter to your platform :)
> Because you guys were running a month long bounty promotion I decided to take a little of my time and
> gently perform recon on your platform." (@defparam, #737140, https://hackerone.com/reports/737140)

Blunt one-liner alternative: "A prototype pollution in Kibana can be used to gain remote code
execution." (@alexbrasetvik, #852613).

## Root cause

Name the several concrete, app-specific facts whose intersection is the bug, as a short numbered list.
Not one generic "improper validation".

> "1) Flickr does not expect e-mail addresses to be changed - still it is possible to change a user's
> address using the AWS Cognito API.\n2) Flickr does not check whether the e-mail address is verified
> on login\n3) Flickr normalizes the e-mail address received from AWS cognito, so that collisions are
> possible" (@lauritz, #1342088, https://hackerone.com/reports/1342088)

## Steps to reproduce

Hyper-specific operational steps: exact tools, plugins, menus, flags, a real PoC URL, and a deadpan
payoff line.

> "1. Run psnow in a VM.\n2. Go to the following URL in a browser on the same machine:\n    1.
> https://[redacted].s3.amazonaws.com/agl-poc/calc-ws.html\n3. Watch calc pop." (@parsiya, #873614,
> https://hackerone.com/reports/873614)

## Impact

Read the honest ceiling off the evidence and name the specific escalations it forecloses, instead of
asserting them.

> "As can be seen above, the EC2 instance does not have an IAM role assigned to it. This limits me from
> being able to escalate this further to file disclosure, RCE, or an AWS account takeover."
> (@nrockhouse, #1108418, https://hackerone.com/reports/1108418)

## Severity

Argue your own tier in the first person and be frank about the money.

> "I believe exim is widespread enough and it seems to fit all criteria. I wonder if this finding
> worths a bounty, or the reason why it is not included. Thanks!" (@mehqq, #322935,
> https://hackerone.com/reports/322935)

## Supporting material

Paste the raw transcript, shell artifacts and echoed command included, rather than narrating the
outcome.

> "sh: no job control in this shell\nsh-4.2$ whoami\nwhoami\ndeploy" (@fransrosen, #422944,
> https://hackerone.com/reports/422944)

## Remediation

One concrete action, blunt and urgent, second person, sometimes with an ALL-CAPS constraint. Not a
defense-in-depth checklist.

> "You should urgently make sure your policy.xml for imagemagick ONLY allows gif,jpg,png and nothing
> else." (@fransrosen, #403417, https://hackerone.com/reports/403417)
