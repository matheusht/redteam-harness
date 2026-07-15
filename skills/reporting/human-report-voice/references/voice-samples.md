# Voice samples, grouped by device

Real excerpts from the corpus, organized by the human move they illustrate. Reproduced verbatim.
Use these to calibrate the register. The register moves (openers, sign-offs, blunt lines, dash
handling) are safe to emulate. The authentic markers (emoticons, personal asides, real test data) are
only for when they are genuinely yours; do not manufacture them. See the SKILL "honesty line".

## Openers (greet the named team, get to the point)

- "Hi, Uber Security Team\n\nI found an RCE in rider.uber.com." (@orange, #125980)
- "Heya!\n\nI've been poking at mruby a bit more and I've found a vulnerability that allows an attacker
  to take control of the instruction pointer." (@h72, #181879)
- "I got a security issue in reverb ios application which allows an attacker hack all users account."
  (@sandeep_hodkasia, #314808) — cold, blunt, non-native, and completely human.

## Sign-offs and offers to help

- "Please let me know if you have any questions.\nPete" (@yaworsk, #164224)
- "Please fix it.\n\nThanks,\nYash :)" (@yashrs, #489146)
- For co-authored work, name both: "Best regards,\nVinnie Vanhoecke @vinnievan and André Baptista
  @0xacb" (@vinnievan, #470520)

## Blunt short sentences (rhythm and variance)

- "6. Bingo!" (@boy_child_, #3178999)
- "3. Watch calc pop." (@parsiya, #873614)
- "A prototype pollution in Kibana can be used to gain remote code execution." (@alexbrasetvik,
  #852613)

Contrast these with a long discovery sentence in the same register: "I was reviewing an Electron app
made by one of Shopify employees ... initially I skipped it because I thought it just contained some
app configuration stuff but after taking a look at the source it was clear that the app never loaded
it." (@augustozanellato, #1087489). The swing between the two lengths is the human signal.

## Contractions (natural rate, ~57% of corpus)

- "I'm officially speechless, I wasn't expecting a bounty so big" (@augustozanellato, #1087489)
- "I've been poking at mruby" (@h72, #181879)
- "it's possible to execute the method" (@lucash-dev, #684092)

## Dash handling (the corpus keeps the function at a low rate; the em-dash glyph never appears)

The corpus has zero `—`. Where a dash appears at all it is ASCII `--` or an en dash `–`, and it is
rare, not the default aside device. Reduce dashes; vary punctuation.

- ASCII, mid-sentence, used once: "very little validation -- in particular, it's possible to execute
  the method even during the liquidation phase." (@lucash-dev, #684092)
- En dash in a title: "IDOR: Account Deletion via Session Misbinding – Attacker Can Delete Victim
  Account" (@z3phyrus, #3154983)

Anti-pattern to avoid: putting a dash on every aside. That is over-uniform and reads AI even with the
"correct" glyph. Most asides should be a separate sentence, a comma clause, parentheses, or a colon.

## Blunt, urgent remediation (second person, one action)

- "The only and simplest way to solve this problem is to upgrade your SSL VPN to the latest version!"
  (@orange, #591295)
- "You should urgently make sure your policy.xml for imagemagick ONLY allows gif,jpg,png and nothing
  else." (@fransrosen, #403417)

## Authentic-only markers (keep if real, never fabricate)

- Honest downward hedge with an emoticon: "I think it can be a Remote Code Execution vulnerability but
  there is a length limit :(" (@orange, #125980)
- Left-in typo: "An attacker can can view any hacker email" (@0xrayan1996, #2032716)
- In-the-moment operational restraint: "After seeing the pings, I immediately turned off the
  replication by executing the redis command `REPLICAOF no one`." (@yvvdwf, #1672388)
- Real test data: "I did all the tests above on gitlab.com on 16-17 August 2022 from IP `51.75.74.52`"
  (@yvvdwf, #1672388)
