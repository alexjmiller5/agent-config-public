---
name: chrome-control
description: ALWAYS invoke FIRST for ANY browser task - anything touching Chrome, a web page, a tab, or a localhost dev server - reading/dumping HTML, listing tabs, injecting or executing JS, clicking through or filling pages, E2E-testing a web UI, capturing network traffic with response bodies, reading cookies or console. Read and drive the user's Chrome from the shell; the claude-in-chrome MCP tools are a LAST RESORT (slow) and this skill says when they're allowed - so it must load before any mcp__claude-in-chrome__* call. Mechanics only; for the reverse-engineering workflow that sits on top, use the web-recon skill.
---

# Chrome Control

Three tiers, cheapest first. **Start at Tier 1 and only climb when the tier
you're on genuinely can't answer the question.** Tier 1 needs no setup and no
clicks; Tier 2 costs the user a click; Tier 3 costs them their logged-in session.

| Need | Tier |
|---|---|
| HTML of an open tab, tab list, run some JS | **1 - `chrome-cli`** |
| Network traffic, response bodies, console, cookies | **2 - CDP on the real profile** |
| Unattended/scripted browsing, no human present | **3 - throwaway profile** |
| Heavy or long-running automation (several browsers, hours of scraping) | **4 - remote Chrome on another machine** |

## The claude-in-chrome MCP is a LAST RESORT

The `mcp__claude-in-chrome__*` extension tools are slower than the shell tiers
(one round-trip per action, frequent script-injection timeouts on busy pages)
and their JS runs in an isolated world - see gotcha 0(c). Only fall back to
them when a shell tier genuinely cannot do the job (e.g. native
mouse-coordinate clicks on a canvas where DOM events won't do, or
screenshots), and return to the shell tiers immediately after.

---

## Tier 1 - `chrome-cli` (no setup, no prompts)

Already installed and declared in nix-config. Talks to Chrome over AppleScript,
so it reads the **tabs the user actually has open** with zero configuration.

```bash
chrome-cli list tabs                  # [windowId:tabId] Title
chrome-cli source                     # full HTML of the frontmost tab
chrome-cli source -t 736899764        # ...of a specific tab
chrome-cli execute 'document.title' -t 736899764   # run JS in a tab
chrome-cli list links -t 736899764
chrome-cli open https://example.com   # new tab (always new; can't retarget)
chrome-cli info -t 736899764          # title + URL
```

**`-t` goes AFTER the JS/subcommand argument, never before.**
`chrome-cli execute -t <id> '<js>'` fails with the useless error
`No matching handler found`.

To navigate an *existing* tab (rather than opening a new one), set
`window.location.href` via `execute` - `open` always creates a new tab.
Clicking a real element is better still when the site's links are
JS-driven or carry one-time tokens:

```bash
chrome-cli execute 'var a=[...document.querySelectorAll("a")]
  .find(x=>/Account Name/i.test(x.textContent)); a.click(), "ok"' -t <id>
```

**This is the right answer for "pull the HTML from the tab I have open."**
Don't reach for CDP for that.

Requires View > Developer > **"Allow JavaScript from Apple Events"** (already
on in the user's profile; `source` and `execute` are built on it, `list tabs` is
not). Also needs an Automation TCC grant for the calling process - already
granted for Claude's shell.

Limits: no network traffic, no response bodies, no console history, no cookies.
Those are Tier 2.

---

## Tier 2 - CDP against the real, logged-in profile

This is the only way to capture **authenticated** API traffic. It attaches to
the user's everyday Chrome - their real cookies, their open tabs.

### One-time setup (already done on the MacBook)

the user ticks **"Allow remote debugging for this browser instance"** at
`chrome://inspect/#remote-debugging`. This is a browser-wide preference that
persists across restarts forever. Codified in nix-config
(`home/macos/chrome-remote-debugging.nix`) so a fresh machine gets it.

Chrome then listens on **127.0.0.1:9222** and writes the endpoint to
`~/Library/Application Support/Google/Chrome/DevToolsActivePort` (line 1 =
port, line 2 = ws path). **Always read that file - the port is usually 9222
but falls back to an ephemeral one if taken.**

### The per-connection dialog (unavoidable)

Every new WebSocket connection pops a modal: *"Allow remote debugging? An
external app wants full control over this Chrome session."* the user must click
**Allow**. Google closed the "remember my choice" request as *not planned* -
there is no allowlist and no token.

**Tell the user the dialog is coming before you connect**, and use a generous
timeout - the handshake blocks until they answer. One click per connection, not
per command, so hold the connection open across a session.

While attached, Chrome shows a persistent *"Chrome is being controlled by
automated test software"* infobar. That's expected, not a problem.

### Trusted input + capture - `scripts/cdp-act.mjs`

The actor. Same one-click approval, but drives the page with **trusted**
input (`Input.dispatchMouseEvent` / `dispatchKeyEvent`), which is the only
way to click things that ignore synthetic events (Google Maps list links,
icon pickers). Steps are JSON, one per line.

```bash
# one-shot
node ~/.claude/skills/chrome-control/scripts/cdp-act.mjs --url <tab-substr> < steps.json
# persistent: ONE Allow click, then append steps to the file as you go
node ~/.claude/skills/chrome-control/scripts/cdp-act.mjs --url <substr> --follow steps.ndjson &
echo '{"click":"document.querySelector(\"h1\")"}' >> steps.ndjson
```

Steps: `{"eval":"<expr>"}` `{"click":"<expr returning Element>"}`
`{"type":"text"}` (insertText) `{"keys":"text"}` (per-character key events)
`{"key":"Enter|Escape|Tab"}` `{"sleep":ms}` `{"shot":"/path.png"}`
`{"capture":"<url substr>"}` (prints matching request/response bodies)
`{"quit":true}`. Output is NDJSON on stdout.

**Trusted input is not magic**: it clicks where you point, but an app that
opens an editor only from its own internal state still won't cooperate
(see the note-editing failure documented in `places-sync`).

### Capturing traffic - `scripts/cdp-sniff.mjs`

The passive sniffer. Attaches to open tabs and streams XHR/fetch as NDJSON
while the user browses by hand. Zero dependencies (Node 22+ global `WebSocket`).

```bash
node ~/.claude/skills/chrome-control/scripts/cdp-sniff.mjs \
  --secs 120 > capture.ndjson

# options
--url <substr>   only watch tabs whose URL contains this
--secs N         capture window (default 300)
--all            include non-XHR (images, scripts, documents)
--raw            do NOT redact credentials (default is redacted)
```

Each NDJSON line: `ts, type, method, url, status, mimeType, requestHeaders,
requestBody, responseHeaders, responseBody`.

**Credentials are redacted by default** - any header whose name matches
`auth|cookie|token|session|api-key|secret|password|csrf|bearer` is replaced
with `<redacted:Nb>`. Only pass `--raw` when the user explicitly needs the live
token, and never write a `--raw` capture anywhere but the scratchpad.

Reading a capture:

```bash
jq -r '.url' capture.ndjson | sort -u                    # what endpoints exist
jq 'select(.mimeType|test("json"))' capture.ndjson       # the API calls
jq -r 'select(.url|test("api")) | .responseBody' capture.ndjson | jq .
```

---

## Tier 3 - throwaway profile (unattended)

No prompts, fully scriptable, but **logged out**. For automation and cron.

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9333 --user-data-dir=/tmp/chrome-dbg --no-first-run &
curl -s localhost:9333/json/list | jq -r '.[] | select(.type=="page") | .url'
```

Or let `chrome-devtools-mcp`'s CLI launch and manage the browser - it only
ever drives its own logged-out one, never the user's profile:

```bash
export CHROME_DEVTOOLS_MCP_NO_USAGE_STATISTICS=1   # ALWAYS - opts out of Google telemetry
bunx -p chrome-devtools-mcp@latest chrome-devtools start
```

To get logins without the dialog, **copy** the profile to a non-default path -
a different path passes Chrome's check, and on macOS the keychain key is
app-scoped so cookies still decrypt. Copy only `Profile 1` + `Local State`
(the full dir is ~8GB). Caveat: it's a point-in-time fork, and device-bound
session credentials may log some sites out anyway.

CDP fingerprinted? `mitmdump --set hardump=capture.har` +
`mitmproxy2swagger -i capture.har -o api.yml -p https://target.com/api -f har`;
both in nixpkgs, needs a CA install.

---

## Tier 4 - remote Chrome on another machine

Browsers are the heavy part of any automation; the agent session is a
terminal. When a task needs several dedicated Chromes or runs for hours,
run the browsers on a second machine (a home server, a spare Mac) and keep
the session where the user is. The session drives each remote Chrome over
CDP through an ssh port-forward, so only websocket traffic crosses the
wire and the user's own machine stays responsive.

```bash
# on the remote host: a dedicated profile per site, its own debug port
ssh <host> '"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9400 --user-data-dir=$HOME/.local/share/<tool>/sessions/<site> \
  --no-first-run >/dev/null 2>&1 &'
# locally: forward the port, then drive 127.0.0.1:9400 exactly like Tier 3
ssh -N -L 9400:127.0.0.1:9400 <host> &
```

Rules that make this work:

- **Profiles live on the remote host permanently.** Device trust, "remember
  this browser", and cookies accumulate there; never copy them back and
  forth. One profile per site, one port per site, so runs can overlap.
- **Secrets travel over stdin, never the command line.** `printf '%s' "$T" |
  ssh <host> 'read -r T; TOKEN="$T" <script>'` keeps the value out of both
  machines' process lists and out of the transcript. A remote ssh session
  cannot read the host's Keychain (per-session locked), so pipe what it
  needs.
- **The remote host needs a console session** (a user logged in at the
  screen) for Chrome to get a window; check `stat -f %Su /dev/console`.
- **Anything that reads local state runs where the state is**: SMS codes
  from Messages, files, a local database. Either the remote host has that
  state (synced Messages) or the script fetches it over ssh.
- **Human handoff = Screen Sharing.** When a site needs the person (an
  SMS-only login, a CAPTCHA, "confirm on your phone"), they open the remote
  machine's screen (macOS Screen Sharing over the tailnet, one click), do
  the step in that Chrome, and close it. Before asking, screenshot the
  page over the forwarded CDP (`Page.captureScreenshot`) and show it in
  chat - often that alone resolves it.
- **Chrome 136+ still ignores `--remote-debugging-port` on the default
  profile** (gotcha 1); a dedicated `--user-data-dir` is what makes the
  port listen, remote or not.

## Screenshots (shell - do NOT default to the MCP for these)

Headless Chrome's `--screenshot` flag renders any URL that needs no login
(localhost dev servers, public pages) straight to a PNG - no prompts, no MCP:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless --screenshot=/path/out.png --window-size=1400,1000 \
  --hide-scrollbars --virtual-time-budget=6000 \
  --user-data-dir="$(mktemp -d)" http://localhost:5173/
```

The PNG is written even when the process then fails to exit (observed Chrome
139) - background it or wrap in a short timeout, then `pkill -f` the temp
profile path. `--virtual-time-budget` gives client-side JS (charts, fetches)
time to settle before capture. Pages behind a login are the one case where
screenshots legitimately fall back to the claude-in-chrome MCP (or CDP
`Page.captureScreenshot` on Tier 2).

0. **`chrome-cli execute` quirks** (chrome-cli 1.9 / Chrome 139, observed
   2026-08-25): (a) a non-string result crashes it
   (`NSInvalidArgumentException`) - end every script with a string
   expression; (b) scripts beyond ~1000 chars silently no-op (empty output,
   nothing runs) - keep each call short or inject a `<script>` element;
   (c) its JS has an **isolated ES module map**: `import()` there returns
   fresh module instances, never the page's live ones. To reach the app's
   real modules (Vite dev included), append an **inline**
   `<script type="module">` (textContent, not src - a src-based module
   pointing at a Vite-served file did not execute) and pass results back
   through a DOM attribute like `document.body.dataset.x`.
1. **Chrome 136+ ignores `--remote-debugging-port` on the default profile.**
   Passing the default path explicitly doesn't help - Chrome compares resolved
   paths. Symptom: Chrome starts fine, nothing listens on the port. The
   `chrome://inspect` approval flow (Tier 2) is the *only* way onto the real
   profile, and it deliberately bypasses this check.
2. **`/json/list` and `/json/version` return 404 in approval mode.** Anything
   that probes HTTP discovery first will fail confusingly. Read
   `DevToolsActivePort` and go straight to the WebSocket.
3. **Response bodies are evicted on navigation.** Call
   `Network.getResponseBody` on `loadingFinished`, not later.
4. **`Network.enable` on the browser session captures nothing.** You must
   `Target.attachToTarget {flatten:true}` per page and enable on *that*
   session. The new session's id arrives in `params.sessionId` of
   `Target.attachedToTarget`, not at the message's top level.
5. **Kill leaked browsers.** The CLI daemon and headless one-shots leak Chrome
   processes. `pgrep -fl "remote-debugging-port|chrome-devtools-mcp"` and clean
   up when done.

## When reality contradicts this skill, FIX THIS SKILL

Everything here is empirical and drifts as Chrome ships. A command not
behaving as documented is expected maintenance, not a dead end - but before
editing: **reproduce it twice** (a down site, a network blip, or an unclicked
Allow is not a skill bug), **name the actual cause** rather than the symptom,
and verify the fix. Then edit surgically: correct the specific claim, record
the Chrome / tool version you observed it on, add to Gotchas only if it will
bite again, and state **current behaviour only** - no changelogs, no dated
notes. Tell the user what changed, in chat. Same bar applies to `web-recon`.

## Human handoff

CDP attaches to a **visible** browser, so the user can help. When you hit a login
wall, CAPTCHA, MFA prompt, or a page you can't navigate to, **stop and ask** -
state what you need, why, and what happens next:

> "I need you to log into the account page and get to the orders list, then
> tell me when you're there - I'll be capturing traffic the whole time."

**Never attempt to automate past a credential or CAPTCHA wall.** Hand it to
the user. This is the safety boundary that keeps the tooling pointed at sites they
legitimately has access to.
