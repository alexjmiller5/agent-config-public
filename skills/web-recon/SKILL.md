---
name: web-recon
description: Reverse-engineer a website's structure and its backend APIs - find the undocumented JSON endpoints behind a page, extract the auth it needs, and drive them directly from the shell to get data the UI never renders. Use when the user wants to scrape a site, pull data off a service with no public API, understand how a web app talks to its backend, or asks to "figure out how this site works" / "find the API behind this". Builds on the chrome-control skill for all browser mechanics.
---

# Web Recon

Find the JSON API the page already calls, then call it yourself: **the browser
is scaffolding, not the destination**, and the backend routinely returns far
more than the UI displays.

Browser mechanics (attaching, capturing, tab reading) and the human-handoff
rule all live in the **`chrome-control`** skill. This skill is the workflow.

## The arc

```
scope -> capture -> identify -> extract auth -> LEAVE THE BROWSER -> probe -> client
```

---

## 1. Scope

Before touching anything, establish with the user:

- **What data do they actually want?** The answer decides which page to drive.
- **Do they have legitimate access?** This skill is for sites they can already
  reach - their own accounts, their own data, public data. If it needs credentials
  they doesn't have, stop.
- **Check for a real API first.** A documented API, an RSS feed, a `.json`
  suffix, or a `/api/` path in `robots.txt` beats reverse engineering. Also
  check `sitemap.xml` and any `__NEXT_DATA__` / `window.__INITIAL_STATE__`
  blob in the HTML - sometimes the whole dataset is already inline and there
  is nothing to reverse engineer:

  ```bash
  chrome-cli source | grep -oE '__(NEXT_DATA|INITIAL_STATE|NUXT)__' | head
  ```

## 2. Capture

Capture per `chrome-control` Tier 2 (`--url target.com --secs 180`), then
drive the page - by hand, by `chrome-cli execute`, or by asking the user.

Exercise the behaviour you want to replicate: load the list, page to page 2,
open a detail view, use the search box, change a filter. **Each interaction
you trigger is an endpoint you learn.** Pagination and search are the two
highest-value things to exercise - they reveal the query parameters.

Login, CAPTCHA, MFA, or a flow you can't navigate → hand off to the user per
`chrome-control`'s human-handoff rule; tell them capture is running.

## 3. Identify the API

```bash
jq -r '.url' capture.ndjson | sed 's/?.*//' | sort | uniq -c | sort -rn
jq -r 'select(.mimeType|test("json")) | "\(.method) \(.status) \(.url)"' capture.ndjson
```

You're looking for JSON responses whose shape matches what's on screen. Note
for each candidate: method, path, query params, request body shape, and which
UI action triggered it. GraphQL shows up as repeated POSTs to one `/graphql`
path - there the *operation name and query body* are the real endpoint.

## 4. Extract auth - carefully

Work out the **minimum** the endpoint needs. Usually one of: a session cookie,
a `Authorization: Bearer` header, an API key header, or a CSRF token paired
with the cookie. Often much of what the browser sends is irrelevant.

**Secrets rules (non-negotiable):** raw captures stay in the scratchpad; live
tokens live in the shell env for the session. Anything durable goes through
the `1password` skill. Session cookies expire - note the expiry so the client
fails loudly rather than silently returning empty results.

### Not every site has a JSON API

Plenty of older/enterprise sites (banks especially) are **server-rendered** -
the data arrives in the HTML document, not an XHR. Signs: `.go`/`.do`/`.aspx`
URLs, full page loads on every filter change, and a capture whose only JSON is
telemetry and widgets.

Don't keep hunting for an endpoint that isn't there. The equivalent win is the
**URL pattern plus its opaque tokens** - usually sitting in a `<select>`, a
hidden form field, or a link's query string. Dump the selectors; they often
enumerate every filter/date/statement the account has:

```bash
chrome-cli execute '[...document.querySelectorAll("select")].map(s=>({
  id:s.id, opts:[...s.options].map(o=>o.value+" :: "+o.text.trim())}))' -t <id>
```

Those tokens are typically **session-bound and one-time** - a URL copied from
one session will bounce back to a landing page in the next. So the client has
to re-scrape the token each run rather than hardcode it. Note that in the
report; it's the difference between a working scraper and a mystery.

## 5. Leave the browser

This is the step that matters. Replay the endpoint with `httpx`, minus the
browser:

```bash
curl -s 'https://target.com/api/items?page=1' -H "Cookie: $SESSION" | jq .
```

Then **strip it down** - remove headers one at a time until it breaks. What
remains is the real contract. A request that needs only a cookie is a far
better client than one carrying 30 browser headers.

If it fails outside the browser but worked inside, the usual causes are:
`Referer`/`Origin` checks, a `User-Agent` filter, a CSRF token bound to the
session, or TLS fingerprinting (if it's the last one, fall back to driving the
browser, or the mitmproxy fallback in `chrome-control`).

## 6. Probe for hidden data

The UI is a client of this API, not its definition:

- **Page size**: the UI asks for 20; try `limit=1000`. Find the server's cap.
- **Undocumented params**: try `?fields=`, `?include=`, `?expand=`,
  `?sort=`, `?since=`. REST frameworks commonly support more than the UI uses.
- **Unrendered fields**: diff the JSON keys against what's on screen. Internal
  ids, timestamps, flags, and relations are often there and unused.
- **Adjacent endpoints**: if `/api/items/{id}` exists, try `/api/items`,
  `/api/items/{id}/history`, `/api/users/me`.
- **Version bumps**: `/v1/` -> `/v2/` sometimes exposes a richer shape.
- **Verb changes**: an endpoint that GETs may also accept HEAD or OPTIONS,
  and `OPTIONS` sometimes lists allowed methods.

**Rate-limit yourself.** Probe slowly, back off on 429, and don't hammer a
site the user has an account on - an account ban is a real cost. A `sleep` between
requests is cheaper than losing access.

## 7. Write the client

Only once the contract is understood. Per AGENTS.md's stack: a PEP 723
standalone script, `httpx` + `pydantic`, one function per endpoint, a
generator for pagination, config from env vars - **never hardcoded**. Leave
one assert on a known field of a known record, so a shape change fails loudly.

## Deliverable

Report to the user in chat:

- The endpoints found: method, path, params, what each returns
- What auth is actually required, and when it expires
- **What's available that the UI doesn't show** - this is usually the
  interesting part
- Rate limits observed
- Where the client script lives and how to run it

## Keep this skill true

A step here that misleads you on a real target gets fixed after the job, under
`chrome-control`'s maintenance bar - and browser mechanics that turn out wrong
get fixed in `chrome-control`, not duplicated here.

## Boundaries

Reverse-engineer sites the user has legitimate access to (credential walls are their
per `chrome-control`). Don't build credential stuffing, don't defeat CAPTCHAs
or bot detection to gain access they doesn't have, and don't scrape at volumes
that amount to abuse. If a site's ToS is the live question rather than the
mechanics, say so and let the user decide.
