# Humanization Ruleset for HackerOne-Style Vulnerability Reports

Derived from 74 disclosed, verbatim-verified real reports (70 distinct authors) spanning account takeover, RCE (buffer overflow, deserialization, SSTI, ImageMagick/Ghostscript, prototype pollution), SSRF/metadata theft, IDOR, HTTP request smuggling, GraphQL authz bypass, a MakerDAO smart-contract flaw, and multi-stage sandbox/kernel chains. Only rules that survived per-quote verification against the live report text are included below. Quotes are reproduced exactly as they appear in the source, including typos and non-native constructions.

---

## 1. Humanization Ruleset (IN rules only)

### Title

**Rule.** Paste the literal target host, path, endpoint, or a prior report number directly into the title, including words like "again" that only make sense given real engagement history.
**Why it reads human.** A concrete host/path or a back-reference to a specific prior report number is an artifact of an actual ongoing engagement that a model has no way to invent.
**Evidence.**
- "Remote Code Execution on www.semrush.com/my_reports on Logo upload" — @fransrosen, #403417 (https://hackerone.com/reports/403417)
- "Bypass for #488147 enables stored XSS on https://paypal.com/signin again" — @albinowax, #510152 (https://hackerone.com/reports/510152)
- "[CRITICAL] 0-Click Account Takeover via Password Reset [AUTH-3243] /orchestrator/v1/password_reset/start" — @db3wy, #2831902 (https://hackerone.com/reports/2831902)

**Gold exemplar.** @db3wy's title (#2831902) fuses a severity tag, a plain-language impact claim, an internal tracking tag `[AUTH-3243]`, and the literal endpoint `/orchestrator/v1/password_reset/start` — four engagement-specific tokens no synthetic title would assemble.

### Summary

**Rule.** Open the summary with a direct greeting to the named security team, sometimes introducing yourself, before any technical content.
**Why it reads human.** Model summaries jump straight to an abstract one-sentence impact statement; people greet a specific team by name and occasionally self-introduce.
**Evidence.**
- "Hi Slack Security Team!\n\nMy name is Evan and I'm a first time bug hunter to your platform :) Because you guys were running a month long bounty promotion I decided to take a little of my time and gently perform recon on your platform." — @defparam, #737140 (https://hackerone.com/reports/737140)
- "Hi, Uber Security Team\n\nI found an RCE in rider.uber.com." — @orange, #125980 (https://hackerone.com/reports/125980)
- "Heya!\n\nI've been poking at mruby a bit more and I've found a vulnerability that allows an attacker to take control of the instruction pointer." — @h72, #181879 (https://hackerone.com/reports/181879)

**Rule.** Narrate the messy discovery path: what you stumbled onto, seemingly-irrelevant context, files you first skipped, and false leads under their own headers.
**Why it reads human.** People tell the crooked, first-person story with dead ends and initial wrong guesses, where a model presents a clean, already-solved linear account.
**Evidence.**
- "I was reviewing an Electron app made by one of Shopify employees (at the time I didn't know that Shopify was in any way involved), after extracting the app.asar file using npx asar extract path/to/app.asar extracted/path I found a .env file, initially I skipped it because I thought it just contained some app configuration stuff but after taking a look at the source it was clear that the app never loaded it." — @augustozanellato, #1087489 (https://hackerone.com/reports/1087489)
- "## False Starts\n\nI first came across the endpoint via typical subdomain enumeration." — @spaceraccoon, #531051 (https://hackerone.com/reports/531051)

**Rule.** Treat a single flat sentence as an acceptable summary; do not pad it into a paragraph, and leave grammatical roughness in place.
**Why it reads human.** Model summaries default to a padded paragraph that restates impact twice, while human summaries are frequently one blunt, sometimes ungrammatical, line.
**Evidence.**
- "A prototype pollution in Kibana can be used to gain remote code execution." — @alexbrasetvik, #852613 (https://hackerone.com/reports/852613)
- "I got a security issue in reverb ios application which allows an attacker hack all users account." — @sandeep_hodkasia, #314808 (https://hackerone.com/reports/314808)

**Gold exemplar.** @defparam's opening (#737140) greets the team by name, self-identifies ("My name is Evan and I'm a first time bug hunter"), sets a real-world motivation (the month-long promotion), and closes the line with a `:)` — before a single technical detail.

### Root cause

**Rule.** Decompose the root cause into the several independent, app-specific preconditions that combine, as a short numbered list, rather than one generic "improper validation" statement.
**Why it reads human.** Real chained bugs are explained as the concrete conditions that had to co-occur; a model collapses this into a single abstract cause.
**Evidence.**
- "1) Flickr does not expect e-mail addresses to be changed - still it is possible to change a user's address using the AWS Cognito API.\n2) Flickr does not check whether the e-mail address is verified on login\n3) Flickr normalizes the e-mail address received from AWS cognito, so that collisions are possible" — @lauritz, #1342088 (https://hackerone.com/reports/1342088)
- "1. The local websocket server at `localhost:1235` does not check the origin of incoming requests.\n    1. This allows websites loaded in browsers on the same machine to send requests to the websocket server.\n    2. Websockets are not bound by the Same-Origin Policy so the websocket server has to do this manually." — @parsiya, #873614 (https://hackerone.com/reports/873614)

**Gold exemplar.** @lauritz's three-line conclusion (#1342088) names three separate Flickr-specific facts (unexpected email mutation via Cognito, no verification check on login, collision-producing normalization) whose intersection is the bug — not a reusable abstraction.

### Steps to reproduce

**Rule.** Give hyper-specific operational steps naming the exact tools, plugins, menus, and flags used in the session.
**Why it reads human.** Chrome like "install the Content-Type Converter plugin from the BApp Store" or "--tamper htmlencode" comes from an actual keyboard session; a model gives generic "intercept the request" steps.
**Evidence.**
- "Then right-click on the HTTP Editor inside Burp Suite and select Extensions -> Content-Type Converter -> Convert to JSON (make sure to have the Content-Type Converter plugin installed from the BApp Store)" — @asterion04, #2293343 (https://hackerone.com/reports/2293343)
- "1) Open up a fresh Burp\n2) Open up a fresh Collaborator by going to menu: `Burp->Burp Collaborator Client`\n3) In the Collaborator Client click on `Copy to clipboard` for the server URL" — @defparam, #737140 (https://hackerone.com/reports/737140)

**Rule.** Drop conversational second-person asides into the middle of the mechanical step list.
**Why it reads human.** People break the formal register mid-procedure with encouragement or a payoff line; a model keeps every numbered step uniformly clinical.
**Evidence.**
- "All done now, grab a coffee, sit back and relax, watch some YouTube videos and wait for an email to go to your email attacker@gmail.com" — @ngalog, #791775 (https://hackerone.com/reports/791775)
- "1. Run psnow in a VM.\n2. Go to the following URL in a browser on the same machine:\n    1. https://[redacted].s3.amazonaws.com/agl-poc/calc-ws.html\n3. Watch calc pop." — @parsiya, #873614 (https://hackerone.com/reports/873614)
- "6. Bingo!" — @boy_child_, #3178999 (https://hackerone.com/reports/3178999)

**Rule.** Use your own real, named test accounts, domains, IPs, and testing dates in the repro instead of generic placeholders like attacker@example.com.
**Why it reads human.** Real handles, IPs, and dates are engagement artifacts; a model defaults to sanitized example.com placeholders.
**Evidence.**
- "All tests were performed against my user accounts. The user account patterns used were as follows:\n* lauritz+*@wearehackerone.com\n* *@lauritz-holtmann.de" — @lauritz, #1342088 (https://hackerone.com/reports/1342088)
- "I think I should stop testing to avoid any further potential incidences. I did all the tests above on gitlab.com on 16-17 August 2022 from IP `51.75.74.52`" — @yvvdwf, #1672388 (https://hackerone.com/reports/1672388)

**Gold exemplar.** @parsiya's steps (#873614) combine all three: a named binary run in a real VM, a literal (redacted) S3 PoC URL, and the deadpan payoff "Watch calc pop."

### Impact

**Rule.** When genuinely unsure the bug is fully exploitable, hedge the impact downward in the impact section itself, with a shrug or a sad emoticon, rather than inflating it.
**Why it reads human.** A model always maximizes claimed severity; people openly qualify uncertainty and use emoticons to mark it.
**Evidence.**
- "Could be a Server Side template injection that can be used to take over the server ¯\_(ツ)_/¯" — @zombiehelp54, #423541 (https://hackerone.com/reports/423541)
- "I think it can be a Remote Code Execution vulnerability but there is a length limit :(" — @orange, #125980 (https://hackerone.com/reports/125980)

**Rule.** Document the exact ceiling where escalation stopped and the negative results, rather than implying full compromise you did not achieve.
**Why it reads human.** People state honest caps on how far they got; model impact sections push toward maximal claimed damage.
**Evidence.**
- "As can be seen above, the EC2 instance does not have an IAM role assigned to it. This limits me from being able to escalate this further to file disclosure, RCE, or an AWS account takeover." — @nrockhouse, #1108418 (https://hackerone.com/reports/1108418)
- "Since the attack code can be sent as a GET request, an attacker can attack a device running a test server for ujs from the external network by inducing a trap site. However, since this is a server used for testing rails development, it does not seem to have a significant impact on users." — @ooooooo_q, #942103 (https://hackerone.com/reports/942103)

**Gold exemplar.** @nrockhouse (#1108418) reads the absence of an IAM role off the metadata output and names the three specific escalations it forecloses — file disclosure, RCE, account takeover — instead of asserting any of them.

### Severity

**Rule.** Argue your own severity or bounty tier in the first person and speak candidly about the money.
**Why it reads human.** People are frank about compensation, claiming a tier or openly wondering whether a finding warrants a bounty; a model stays detached and never negotiates its own payout.
**Evidence.**
- "Given the above I understand the issue has Critical severity, and fully qualifies for the corresponding bounty." — @lucash-dev, #684092 (https://hackerone.com/reports/684092)
- "I believe exim is widespread enough and it seems to fit all criteria. I wonder if this finding worths a bounty, or the reason why it is not included. Thanks!" — @mehqq, #322935 (https://hackerone.com/reports/322935)

**Gold exemplar.** @mehqq (#322935) argues the finding's merit ("exim is widespread enough... fits all criteria") and then, in the same breath, asks whether it "worths a bounty" — self-advocacy and candor in one line.

### Supporting material

**Rule.** Paste raw, unpolished command output as proof, redaction bars and shell artifacts included, instead of narrating "I ran whoami and got X."
**Why it reads human.** A real transcript keeps the doubled command echo and full raw listings; a model summarizes the outcome in prose.
**Evidence.**
- "sh: no job control in this shell\nsh-4.2$ whoami\nwhoami\ndeploy" — @fransrosen, #422944 (https://hackerone.com/reports/422944)
- "$ id\nuid=998(git) gid=998(git) groups=998(git)" — @vakzz, #658013 (https://hackerone.com/reports/658013)

**Rule.** Reference an attached PoC file or video by its actual filename or test-function name and say what it shows.
**Why it reads human.** A named artifact maps to a real upload; model output has no attachments to name.
**Evidence.**
- "**Steamclient_POC_Windows10.mp4**: Contains a video of the exploit being triggered on Windows 10 via manual interaction with the Steam server browser" — @vinnievan, #470520 (https://hackerone.com/reports/470520)
- "I've attached to this report a modified version of `end.t.sol` which contains a test (`test_steal_all_collateral_using_flipper`) that reproduces the attack." — @lucash-dev, #684092 (https://hackerone.com/reports/684092)

**Rule.** Defer full detail to your own external blog or writeup with a real personal link, sometimes treating the H1 body as a stub.
**Why it reads human.** Real researchers point to their own published content on medium/portswigger/personal domains; a model has no personal blog to cite.
**Evidence.**
- "For more information you can read my writeup: https://medium.com/@dPhoeniixx/vimeo-upload-function-ssrf-7466d8630437" — @dphoeniixx, #549882 (https://hackerone.com/reports/549882)
- "This bug is simple, but can be leverage to gain remote code execution, using skillful heap exploitation. Details are here: https://devco.re/blog/2018/03/06/exim-off-by-one-RCE-exploiting-CVE-2018-6789-en/" — @mehqq, #322935 (https://hackerone.com/reports/322935)

**Gold exemplar.** @fransrosen's raw shell paste (#422944) keeps "sh: no job control in this shell", the echoed `whoami\nwhoami`, and the bare result `deploy` — the literal terminal state, not a narrated outcome.

### Remediation

**Rule.** Give blunt, urgent, second-person fix advice naming one concrete action, occasionally with ALL-CAPS emphasis on the constraint.
**Why it reads human.** People give a direct, alarmed imperative; a model produces a hedged, comprehensive defense-in-depth bullet list.
**Evidence.**
- "You should urgently make sure your policy.xml for imagemagick ONLY allows gif,jpg,png and nothing else." — @fransrosen, #403417 (https://hackerone.com/reports/403417)
- "The only and simplest way to solve this problem is to upgrade your SSL VPN to the [latest version](https://kb.pulsesecure.net/articles/Pulse_Security_Advisories/SA44101)!" — @orange, #591295 (https://hackerone.com/reports/591295)

**Gold exemplar.** @fransrosen (#403417) names exactly one fix (`policy.xml` allowlist), scopes it with the capitalized constraint "ONLY allows gif,jpg,png and nothing else", and marks it "urgently" — no supplementary checklist.

### VOICE

**Rule.** Sign off with your real first name and a casual closing, or an offer to help.
**Why it reads human.** Model reports end at impact/remediation with no personal sign-off; people close like an email with their actual name.
**Evidence.**
- "Please let me know if you have any questions.\nPete" — @yaworsk, #164224 (https://hackerone.com/reports/164224)
- "Please fix it.\n\nThanks,\nYash :)" — @yashrs, #489146 (https://hackerone.com/reports/489146)

**Rule.** Scatter plain-text emoticons through even critical-severity technical content.
**Why it reads human.** ASCII emoticons in a serious disclosure are a strong human signal a model almost never emits in a formal report.
**Evidence.**
- "Thanks for your patience for reading my report. : )" — @orange, #125980 (https://hackerone.com/reports/125980)
- "Wow, thanks a lot for the bounty and bonus :) Happy to retest when you're ready. :)" — @alexbrasetvik, #852613 (https://hackerone.com/reports/852613)

**Rule.** Express raw personal reactions to the outcome, including disbelief at the bounty or what the money means to you.
**Why it reads human.** Genuine affect about payout and personal circumstances is something a model does not produce about its own compensation.
**Evidence.**
- "Ok, I'm officially speechless, I wasn't expecting a bounty so big! Big thanks to all the Shopify security team, looking forward to open more reports here!" — @augustozanellato, #1087489 (https://hackerone.com/reports/1087489)
- "Hi @jobert -- Thanks for the bounty! This is a very large sum for me.\nMy PayPal has in my country a certain limit per month, if I can not get the whole amount at once, it will be possible to divide it into several parts in the future?" — @Haxta4ok00, #745324 (https://hackerone.com/reports/745324)

**Rule.** For two-person work, use "we" and sign off naming both real collaborators by handle or name.
**Why it reads human.** Named co-authors with real handles map to actual people; model output is a single de-personalized narrator.
**Evidence.**
- "Best regards,\nVinnie Vanhoecke @vinnievan and André Baptista @0xacb" — @vinnievan, #470520 (https://hackerone.com/reports/470520)
- "Hi, we(Orange Tsai and Meh Chang) are the security research team from DEVCORE. Recently, we are doing a research about SSL VPN security, and found several critical vulnerabilities on Pulse Secure SSL VPN!" — @orange, #591295 (https://hackerone.com/reports/591295)

**Gold exemplar.** @augustozanellato (#1087489) reacts to the payout itself — "officially speechless, I wasn't expecting a bounty so big" — the kind of affect about one's own compensation that has no synthetic analog.

### ANTI-TELLS

**Rule.** Never use the typographic em-dash; where a dash is wanted, reach for ASCII "--", an en dash "–", or a period.
**Why it reads human.** The em-dash is one of the strongest model stylistic fingerprints, and its total absence across all 74 reports is itself the marker.
**Evidence.**
- "The implementation of that method, however, completely lacks access control and has very little validation -- in particular, it's possible to execute the method even during the liquidation phase." — @lucash-dev, #684092 (https://hackerone.com/reports/684092)
- "IDOR: Account Deletion via Session Misbinding – Attacker Can Delete Victim Account" — @z3phyrus, #3154983 (https://hackerone.com/reports/3154983)

**Rule.** Leave real typos and slips in place — doubled words, misspellings, dropped articles — instead of proofreading them out.
**Why it reads human.** Uncorrected errors are near-impossible to fake convincingly, and model output is essentially perfectly proofread by default.
**Evidence.**
- "An attacker can can view any hacker email via  /SaveCollaboratorsMutation operation name " — @0xrayan1996, #2032716 (https://hackerone.com/reports/2032716)
- "Hoewever, some common deployement scenarios (using Amazon EC2 or OpenStack) include a \"metadata\" web server listening on a multicast IP (169.254.169.254):" — @agarri_fr, #53088 (https://hackerone.com/reports/53088)

**Rule.** Let non-native English constructions — dropped articles, tense and agreement slips — coexist with precise, correct exploit logic.
**Why it reads human.** A default model produces idiomatic native English, so consistent ESL patterns alongside technically flawless reasoning signal a real non-native researcher.
**Evidence.**
- "Apart form all above issue, attacker can do following things as well.\n+ Creating fake login page for credentials harvesting.\n+ Sharing malicious files using roblox.\n+ Creating mail account using GSuite to send and recived emails on behalf of `*@devrel.roblox.com`" — @geekboy, #335330 (https://hackerone.com/reports/335330)
- "Notice an attacker replaced user_id with victim's user_id and the server responded with victim's user_id and given us otp token. Now let's login with the token." — @korniltsev, #921780 (https://hackerone.com/reports/921780)

**Rule.** Narrate candid operational-safety and ethical judgment calls — turning an exploit off on production, confessing to cracked test software, apologizing for potential harm.
**Why it reads human.** In-the-moment restraint on live infrastructure reflects a person weighing real consequences, which a model does not roleplay.
**Evidence.**
- "Please forgive me to use a crack on my self hosted testing purpose GitLab EE instance :)" — @saltyyolk, #733072 (https://hackerone.com/reports/733072)
- "This means that I have the full control on the redis. After seeing the pings, I immediately turned off the replication by executing the redis command `REPLICAOF no one`." — @yvvdwf, #1672388 (https://hackerone.com/reports/1672388)

**Gold exemplar.** @Haxta4ok00 (#745324) stacks four anti-tells in two sentences: the ASCII "--", a missing space ("by it.I reported"), a contraction ("didn't"), and unforced ethical restraint — "I did it to show the impact. I didn't mean any harm by it.I reported it to you at once."

---

## 2. Contested / Distribution Notes

**Contested rules.** None. No rule in this batch produced a mixed or contradictory verdict; every rule either cleared all verification gates (IN) or failed on idiosyncrasy or an unverifiable quote (REJECTED, Section 4).

**Voice distribution (n = 74 reports, 70 distinct authors).**

| Dimension | Value | Share |
|---|---|---|
| First person "I" (dominant) | 48 | 65% |
| Mixed (I + impersonal/we) | 12 | 16% |
| Impersonal only | 11 | 15% |
| "We" only (co-authored) | 3 | 4% |
| Reports containing contractions | 42 | 57% |
| Reports containing a typographic em-dash | 0 | 0% |

Reading the table: first person is present in 60 of 74 reports (81%, "I"-dominant plus mixed); a purely impersonal register is a 15% minority and pure "we" is confined to the three genuinely co-authored reports. Contractions appear in a majority (57%). The em-dash count is exactly zero across the entire corpus — the single most consistent signal here.

**Author and class spread.** 70 distinct authors across 74 reports means these conventions are cross-author, not one writer's habit. They hold across the full difficulty and class range represented: 0-click account takeover and password-reset logic, HTTP request smuggling to mass ATO, stored XSS via cache poisoning, memory-corruption RCE (Exim off-by-one, Steam A2S_PLAYER buffer overflow), insecure-deserialization RCE (pickle, Sawyer::Resource, Telerik, DotNetNuke), SSTI (Jinja2, ERB, Smarty, Handlebars, lodash), SSRF to cloud-metadata theft (AWS/GCP/EC2), IDOR families, GraphQL authorization bypass, a MakerDAO smart-contract validation flaw, and chained sandbox/kernel escapes (PS4/PS5 bd-j, mruby type confusion). The style markers are independent of vuln class and of author skill level.

---

## 3. Debunked Heuristics

Each popular AI-avoidance heuristic is tested against the corpus stats and quotes above. Six of the eight are contradicted by elite real reports; two hold, but only with a mechanism the naive version gets wrong.

**"Avoid leverage/utilize" — debunked.** A top RCE report uses "leverage" as a verb: "This bug is simple, but can be leverage to gain remote code execution" (@mehqq, #322935). The word is not an AI tell; banning it removes vocabulary real researchers use.

**"No rule-of-three lists" — debunked.** Three-item enumerations are a normal root-cause and impact device. @lauritz's root cause is exactly three numbered conditions ("1) ... 2) ... 3) ...", #1342088), and @geekboy lists three attacker capabilities ("+ Creating fake login page... + Sharing malicious files... + Creating mail account", #335330). The structure carries the concrete conditions of the bug; avoiding it would suppress a genuinely human explanatory pattern.

**"Always hedge (could potentially)" — debunked.** Elite reports assert bluntly and reserve hedging only for genuine uncertainty. Remediation is imperative: "You should urgently make sure your policy.xml for imagemagick ONLY allows gif,jpg,png and nothing else" (@fransrosen, #403417); "The only and simplest way to solve this problem is to upgrade your SSL VPN" (@orange, #591295). Impact is stated in absolutes: "steal ALL collateral" and "fully qualifies for the corresponding bounty" (@lucash-dev, #684092). Where humans do hedge, they hedge downward with an emoticon ("but there is a length limit :(", @orange #125980) — the opposite of reflexive upward "could potentially" padding.

**"Avoid contractions" — debunked.** Contractions appear in 42 of 74 reports (57%). Examples: "I'm officially speechless, I wasn't expecting a bounty so big" (@augustozanellato, #1087489); "I've been poking at mruby" (@h72, #181879); "it's possible to execute the method" (@lucash-dev, #684092); "I'm a first time bug hunter" (@defparam, #737140). Stripping contractions moves text away from the corpus norm.

**"No first person" — debunked.** First person is the dominant register: "I" leads 48 of 74 reports and appears in 60 of 74. "I found an RCE in rider.uber.com" (@orange, #125980); "I was reviewing an Electron app" (@augustozanellato, #1087489); "My name is Evan and I'm a first time bug hunter" (@defparam, #737140). An impersonal-only voice is the 15% minority.

**"Uniform sentence length" — debunked.** Real reports swing between one-word steps and long run-ons. Terse extreme: "6. Bingo!" (@boy_child_, #3178999); "3. Watch calc pop." (@parsiya, #873614); the one-line summary "A prototype pollution in Kibana can be used to gain remote code execution." (@alexbrasetvik, #852613). Long extreme: @augustozanellato's ~60-word single discovery sentence beginning "I was reviewing an Electron app... initially I skipped it because I thought it just contained some app configuration stuff but after taking a look at the source it was clear that the app never loaded it." (#1087489). The variance is the signal.

**"Signpost every section (Let us walk through)" — debunked, with nuance.** Humans signpost constantly, but with section headers, not narrative connective tissue. The corpus is full of headers — "## False Starts" (@spaceraccoon, #531051), "## Conclusion" (@lauritz, #1342088), "## Impact" (@zombiehelp54, #423541), "## PoC" (@vinnievan, #470520). What is absent is the prose walk-through phrasing ("Let us walk through the following steps"); reports instead open with a greeting ("Hi Slack Security Team!", @defparam #737140) or a cold blunt statement ("I got a security issue in reverb ios application which allows an attacker hack all users account.", @sandeep_hodkasia #314808). So header-signposting is human and ubiquitous; only the narrative-signpost register is a tell.

**"Never use em dashes" — holds, but the naive version is wrong.** The corpus contains zero typographic em-dashes across all 74 reports, so the direction is correct. But humans do not delete the dash function; they downgrade it to ASCII "--" ("very little validation -- in particular", @lucash-dev #684092; "Hi @jobert -- I did it to show the impact", @Haxta4ok00 #745324) or an en dash "–" ("Account Deletion via Session Misbinding – Attacker Can Delete Victim Account", @z3phyrus #3154983). Simply removing the em-dash without substituting "--"/"–" would still miss the human pattern, which keeps the dash and changes only the glyph.

---

## 4. Rejected Pile (OUT rules)

- **title-understated** — reason_code: idiosyncrasy.
- **title-hedge-urgency** — reason_code: idiosyncrasy.
- **rootcause-paste-code** — reason_code: idiosyncrasy.
- **impact-emotion** — reason_code: unverifiable-quote.
- **supporting-crypto-proof** — reason_code: idiosyncrasy.
- **remediation-oneliner-opinion** — reason_code: unverifiable-quote.
- **voice-lowercase-i** — reason_code: idiosyncrasy.
- **voice-deadpan-humor** — reason_code: idiosyncrasy.
- **antitell-mid-exploitation** — reason_code: idiosyncrasy.
- **antitell-draft-placeholder** — reason_code: idiosyncrasy.
- **antitell-self-deprecation** — reason_code: unverifiable-quote.