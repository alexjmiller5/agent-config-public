---
name: chrome-control
description: ALWAYS invoke FIRST for ANY browser task - anything touching Chrome, a web page, a tab, or a localhost dev server - reading/dumping HTML, listing tabs, injecting or executing JS, clicking through or filling pages, E2E-testing a web UI, capturing network traffic with response bodies, reading cookies or console, screenshots. Drives the shared agent Chrome on the configured host (never the local laptop's), every session in its own window + tab group; the claude-in-chrome MCP tools are a LAST RESORT and this skill says when they're allowed - so it must load before any mcp__claude-in-chrome__* call. Mechanics only; for the reverse-engineering workflow that sits on top, use the web-recon skill.
---

# Chrome Control

## The browser runs on the agent-Chrome host, not on this machine

When `$CHROME_CONTROL_HOST` is set (your machine config exports it), EVERY
browser task drives that host's shared agent Chrome - Tier 4 below: a
headed Chrome on its own data dir, fixed remote-debugging port, kept alive
as a login item, holding every login ever done in it. The Chrome on the
machine you are running on is off limits: driving it slows the user's own
laptop down. The ONE exception is a task literally about a tab the user
has open in front of them ("pull the HTML of this tab", "what does my
current tab say") - then Tier 1/2, locally, and nothing more.

```bash
H="$CHROME_CONTROL_HOST"; P="${CHROME_CONTROL_PORT:-9222}"
ssh -N -L 9223:127.0.0.1:$P "$H" &                 # once per session; 9223 locally so this machine's own Chrome (9222) is untouched
curl -s 127.0.0.1:9223/json/version | head -2      # alive?
S=~/.claude/skills/chrome-control/scripts
node $S/cdp-group.mjs "claude: <task>" https://example.com --port 9223         # your tabs (next section)
node $S/cdp-eval.mjs 9223 'document.title' --target <targetId>                  # = chrome-cli source/execute
node $S/cdp-eval.mjs 9223 --shot /path.png --target <targetId>                  # = screenshot
curl -s 127.0.0.1:9223/json/list | jq -r '.[]|select(.type=="page")|.id+" "+.url'   # = list tabs
```

There is no `chrome-cli` on the host - `cdp-eval.mjs --port` covers
source/execute/shot/trusted-click, `/json/list` covers tab listing. A dev
server on THIS machine is reachable from the host through a reverse
forward in the same ssh (`-R 5173:127.0.0.1:5173`, then open
`http://127.0.0.1:5173` there). A job that must outlive this session, or
the user stepping away, runs its driver on the host (Tier 4 rules). Human
steps (logins, CAPTCHAs) happen over Screen Sharing on the host, and stick.

## Every session gets its own window + tab group (MANDATORY)

Every tab you open lives in a window created for this session, inside a
tab group named after the session. Popups, OAuth redirects and
`target=_blank` pages spawned from those tabs land in the same window and
group (Chrome keeps a tab's children with it), so the user sees one
labelled cluster per agent session and never finds strays mixed into their
own windows. `scripts/cdp-group.mjs` does all of it:

```bash
G=~/.claude/skills/chrome-control/scripts/cdp-group.mjs   # add --port 9223 on the agent host; without it: local real profile (Tier 2)
node $G "claude: <task>" https://a.com https://b.com   # first call creates window + group, later calls add tabs to it
# -> window=<id> group=<id> tabs=<id,...> targets=<targetId,...>   tabs = Chrome/chrome-cli tab ids, targets = CDP ids, same order
node $G "claude: <task>"                                # no urls: sweep strays in the session window into the group
node $G "claude: <task>" --close                        # end of task: closes the whole session window
```

The name is `claude: <short task>`, the same string on every call. One
window per session is the rule; parallel drivers that genuinely need a
window each (several Maps windows at once) use one name per driver - that
is the only reason to have more than one.

How it works: CDP has no tab-group API, so the script opens a hidden
target on an installed extension's origin and calls `chrome.tabs` /
`chrome.tabGroups` from there. The profile needs an extension holding the
`tabGroups` permission - Claude in Chrome (the default `--ext`) does. A
dedicated agent profile gets it through Chrome policy (`ExtensionSettings`
in a root-owned plist under `/Library/Managed Preferences` on macOS, which
is Mandatory; the same key in the user's defaults domain is only
Recommended and ignored). Signing into the extension is a one-time human
step in that browser's window. Without `--port` the call goes through
the real profile (Tier 2, one auto-approved Allow sheet, ~2 s); with
`--port` it is prompt-free.

## Local tiers (the exception above, and the mechanics Tier 4 reuses)

Cheapest first; climb only when the tier you're on genuinely can't answer.
Tier 1 needs no setup and no clicks; Tier 2 costs an auto-approved sheet;
Tier 3 costs the logged-in session.

| Need | Tier |
|---|---|
| HTML of the user's open tab, tab list, run some JS there | **1 - `chrome-cli`** |
| Network traffic, response bodies, console, cookies of the user's session | **2 - CDP on the real profile** |
| Unattended/scripted browsing with no agent host configured | **3 - throwaway profile** |
| Everything else - the default whenever `$CHROME_CONTROL_HOST` is set | **4 - the agent-Chrome host** |

## The claude-in-chrome MCP is a LAST RESORT

The `mcp__claude-in-chrome__*` extension tools drive the LOCAL Chrome, one
slow round-trip per action, with JS in an isolated world (gotcha 0(c)).
With an agent host configured they are not an option at all: screenshots
are `cdp-eval.mjs --shot`, coordinate clicks are `cdp-eval.mjs --click`.
Only in the local exception may they fill a gap a shell tier can't (native
mouse clicks on a canvas), and any tab they open is closed by you, not the
user - see "Close what you open".

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

### The per-connection dialog - auto-approved

Every new WebSocket connection pops a modal: *"Allow remote debugging? An
external app wants full control over this Chrome session."* Google closed
the "remember my choice" request as *not planned* - there is no allowlist
and no token. The sheet is titled `Allow remote debugging?` and its Allow
button is an `AXButton` whose *description* (not name) is `Allow`, nested in
groups.

`scripts/cdp-allow [secs] [grace]` answers it for you: it polls for that sheet
via macOS UI scripting (System Events) for up to `secs` (default 20), clicks
Allow on every matching sheet it sees (Chrome queues one sheet per pending
connection, so a stale one from an earlier attach must not steal the click),
keeps watching `grace` more seconds (default 5) after a click, then exits 0. `cdp-act.mjs` and `cdp-sniff.mjs` spawn it
automatically right after opening their WebSocket, so a Tier 2 attach needs
no human. Any other CDP client does the same: open the socket, then run
`cdp-allow` (or spawn it just before connecting). It only approves while it
runs - it is not a standing allowlist, and other processes' connections
still prompt.

One-time requirement: **Accessibility** permission for the process that
runs `osascript` (System Settings > Privacy & Security > Accessibility - the
terminal or agent app). Without it the click silently no-ops and the
human must click within the timeout. A GUI session must exist (the sheet
is rendered in a window).

While attached, Chrome shows a persistent *"Chrome is being controlled by
automated test software"* infobar. That's expected, not a problem.

### Trusted input + capture - `scripts/cdp-act.mjs`

The actor. Same one-click approval, but drives the page with **trusted**
input (`Input.dispatchMouseEvent` / `dispatchKeyEvent`), which is the only
way to click things that ignore synthetic events (Google Maps list links,
icon pickers). Steps are JSON, one per line.

```bash
# one-shot (add --port 9223 on the agent host: no Allow sheet there)
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

**Click the settled element.** Both actors scroll the clickable element
into view, wait for its rectangle to stop moving, and hit-test its center
before sending input. A layout can move after scrollIntoView; an old
coordinate can activate a neighboring control. Select the clickable
ancestor when a label has pointer-events disabled. Obscured targets fail
without sending a click. Check with `node scripts/test-click-target.mjs`.
If loading inserts rows above the target and pushes it outside the
viewport, the helper scrolls it into view again within the bounded wait.

### One-shot eval / trusted click / screenshot - `scripts/cdp-eval.mjs`

For scripts that make many small calls (a Tier 3/4 driver): one process
per call, exits immediately (~70 ms).

```bash
node cdp-eval.mjs <port> '<expr>' [--url <substr>]            # prints the value
node cdp-eval.mjs <port> --click '<expr returning Element>'   # trusted click at its centre (brings page to front first)
node cdp-eval.mjs <port> --shot /path.png                     # Page.captureScreenshot
node cdp-eval.mjs <port> - --target <id> < expression.js       # JS via stdin
```

Gotchas learned the hard way: a `setTimeout` safety timer must be
`.unref()`ed or every call idles until it fires; `--click` takes an
EXPRESSION - wrap statement blocks in `(function(){ …; return el })()`;
a `hidden` page (`document.visibilityState`) drops all input, so keep the
remote display awake and launch Chrome with backgrounding disabled
(`--disable-backgrounding-occluded-windows --disable-renderer-backgrounding
--disable-features=CalculateNativeWinOcclusion`).

**Explicit targets are strict.** `--target` fails if that page no longer
exists; it never falls back to a different page. Callers must check the
exit status and stop on bridge failures. A missing target otherwise lets
parallel drivers navigate or click each other's windows. Check with
`node scripts/test-cdp-target.mjs`.

Use stdin for expressions containing sensitive values or large payloads,
so they do not appear in process arguments. The bridge drains stdout before
exiting; an immediate process.exit can truncate a large result at a pipe
buffer boundary. Live smoke check:
`node scripts/test-cdp-output.mjs <port> <targetId>`.

### Capturing traffic - `scripts/cdp-sniff.mjs`

The passive sniffer. Attaches to open tabs and streams XHR/fetch as NDJSON
while the user browses by hand. Zero dependencies (Node 22+ global `WebSocket`).

```bash
node ~/.claude/skills/chrome-control/scripts/cdp-sniff.mjs \
  --secs 120 > capture.ndjson

# options
--url <substr>   only watch tabs whose URL contains this
--port N         a dedicated-profile Chrome (the agent host over its forward) instead of the real one
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

`$CHROME_CONTROL_HOST` (ssh host) and `$CHROME_CONTROL_PORT` (default 9222)
name this machine's agent Chrome; the top of this skill is the day-to-day
recipe, this section is why it is shaped that way. `cdp-eval.mjs`,
`cdp-group.mjs`, `cdp-act.mjs` and `cdp-sniff.mjs` all take `--port` for it.

Browsers are the heavy part of any automation; the agent session is a
terminal. So the browser runs on a second machine (a home server, a spare
Mac) with the session staying where the user is, driving it over CDP
through an ssh port-forward: only websocket traffic crosses the wire and
the user's own machine stays responsive.

**One shared agent Chrome per remote machine.** Declare it as a login item
(a launchd user agent on macOS): a headed Chrome on its own data dir with a
fixed `--remote-debugging-port`, kept alive. Every job attaches to that
one endpoint and opens its own tab (`Target.createTarget`), and every login
done in its window - by a job, or by the user over Screen Sharing - is
there for every later run of every tool. A browser that holds all the
user's logins also looks like a person's browser; a fresh single-site
profile per tool looks like automation. Give a site its own profile and
port only when isolation between sites is actually wanted.

```bash
# the remote host runs one Chrome at login, e.g. (macOS launchd agent):
#   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
#     --user-data-dir=$HOME/.local/share/agent-chrome --remote-debugging-port=9222 --no-first-run
# locally: forward the port, then drive 127.0.0.1:9222 exactly like Tier 3
ssh -N -L 9222:127.0.0.1:9222 <host> &
```

Rules that make this work:

- **The profile lives on the remote host permanently.** Device trust,
  "remember this browser", and cookies accumulate there; never copy them
  back and forth.
- **Your tab is yours, the browser is not.** Other jobs may be attached at
  the same time: create your own target, never act on "the active tab",
  and close what you opened.
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
  SMS-only login, a CAPTCHA, "confirm on your phone", a "Continue with
  Google" that needs the account signed in), they open the remote
  machine's screen (macOS Screen Sharing over the tailnet, one click), do
  the step in the shared Chrome, and close it - it persists for everything
  after. Before asking, screenshot the page over the forwarded CDP
  (`Page.captureScreenshot`) and show it in chat - often that alone
  resolves it.
- **Chrome 136+ still ignores `--remote-debugging-port` on the default
  profile** (gotcha 1); the dedicated `--user-data-dir` is what makes the
  port listen, remote or not, and what keeps the per-connection Allow
  sheet away.
- **If the user might close or leave the laptop, the driver moves too.**
  An ssh port-forward dies with the laptop's session, so a job that must
  survive the user stepping away runs its driver ON the remote host,
  talking to `127.0.0.1:<port>` there, with its log on that host. The
  session then only checks in over ssh (`tail` the log, `pgrep` the
  driver). Do this BEFORE the user leaves; keep any local run going until
  the remote one is confirmed writing, then stop the local one.
- **Plain `ssh host 'nohup cmd &'` is NOT enough on macOS** - the process
  dies with the ssh session (so did a `screen -dmS` session, observed
  2026-09-06). What survives: a declared launchd agent for anything
  permanent (the shared Chrome itself), and for a one-off driver a
  transient launchd job: `launchctl submit -l <label> -- /bin/bash
  <script>`. launchd jobs start with a bare PATH - `export PATH=…` at the
  top of the script or every nix/homebrew binary (node!) silently fails
  as "" output. Check the job with `launchctl list | grep <label>`, remove
  with `launchctl remove <label>`. (`open -na "Google Chrome" --args …`
  also survives and gets a window, but a browser started that way is not
  declared - prefer the launchd agent.)

## Screenshots

On the agent host: `cdp-eval.mjs <port> --shot /path.png --target <id>`
(`Page.captureScreenshot`), no prompts. With no host configured, a URL that
needs no login (a localhost dev server, a public page) renders straight to
a PNG with headless Chrome - a short-lived process, not the user's browser:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless --screenshot=/path/out.png --window-size=1400,1000 \
  --hide-scrollbars --virtual-time-budget=6000 \
  --user-data-dir="$(mktemp -d)" http://localhost:5173/
```

The PNG is written even when the process then fails to exit (observed Chrome
139) - background it or wrap in a short timeout, then `pkill -f` the temp
profile path. `--virtual-time-budget` gives client-side JS (charts, fetches)
time to settle before capture. A page behind a login on the local real
profile is `cdp-act.mjs`'s `{"shot":...}` step (Tier 2).

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

## Close what you open (MANDATORY)

Every tab or window you create is yours to close - the user otherwise inherits
a browser full of leftovers from every agent session. Before ending the task
(and before answering any "done" message), close everything you opened:

- The session window: `cdp-group.mjs "<name>" --close` (add `--port` on the
  agent host) - one call takes every tab of the session with it, strays
  included. This is the normal case; the rest are for tabs opened some
  other way.
- `chrome-cli open` prints `Id: <tab>` / `Window id: <win>` - keep them and
  run `chrome-cli close -t <id>` (or `close -w <win>` for an `open -n` window)
  when finished with it. A tab you navigated but did not create stays open.
- MCP `tabs_create_mcp` → `tabs_close_mcp` on that same tab id.
- Tier 3 throwaway Chromes → kill the process (gotcha 5), which takes its
  windows with it. The agent host's Chrome is never killed - it is shared.
- CDP scripts (`cdp-act.mjs` / `cdp-sniff.mjs`) → `{"quit":true}` / let the
  capture window end, then close any tab you opened for them.

Track ids as you go; do not rely on a tab listing at the end to guess which
were yours. Leaving a tab open is only acceptable when the user asked to see
it, and then say so in chat.

## Human handoff

CDP attaches to a **visible** browser, so the user can help. When you hit a login
wall, CAPTCHA, MFA prompt, or a page you can't navigate to, **stop and ask** -
state what you need, why, and what happens next:

> "I need you to log into the account page and get to the orders list, then
> tell me when you're there - I'll be capturing traffic the whole time."

**Never attempt to automate past a credential or CAPTCHA wall.** Hand it to
the user. This is the safety boundary that keeps the tooling pointed at sites they
legitimately has access to.
