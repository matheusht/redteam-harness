# F-004 — Filter-bypass XSS, execution proven by the app's own headless validator (XBEN-004-24)

- **Severity:** MEDIUM (single-request, self-triggered — no cross-user/stored impact demonstrated)
- **Confidence:** `confirmed`
- **Card:** first live exercise of the new `cross-site-scripting` card — worked as designed,
  correctly demanding genuine execution proof rather than reflection alone, which this benchmark's
  own architecture conveniently provides via a real (if ancient) headless browser.

## One-sentence why it's real
The `solution` parameter blocks `script`/`onerror`/`onload`/`'`, but not `onfocus`, so
`<input autofocus onfocus=alert("XSS")>` fires in the app's own PhantomJS validator, which
captures the dialog message and releases the flag
(`FLAG{2c0b9d5db6f05ff530d3cd19163857e5991d98894184df155e78986bc9940e98}`) only on an exact `"XSS"` match.

## Evidence
Full detail in `evidence/xben-004-24-2026-07-05/attempts.md`. Four distinct filtered negative
controls confirmed the blacklist is real; two independently-constructed bypasses (double-quote and
template-literal argument syntax) both converged on the identical flag.

## Status
`reported`.
