---
name: mac-control
description: See and drive a Mac's screen from a shell - screenshots, reading the accessibility tree, clicking, typing as a real keyboard, pressing keys, dismissing dialogs - on the local machine or a remote/headless Mac over ssh. Use for ANY native-app or system-dialog automation outside the browser (browser work goes through chrome-control), and whenever a task on a remote Mac needs eyes or hands on its display. Covers the TCC grants that make it possible, which binary macOS blames, headless-display pitfalls, and when to reach for Claude Code's built-in computer use or Peekaboo instead.
---

# Mac Control

Three tiers, cheapest first. Start at the lowest that fits.

| Need | Use |
|---|---|
| Local Mac, interactive Claude Code session, Pro/Max plan | **Tier 0** - the built-in `computer-use` MCP (section below). Screenshots, clicks, typing, per-app approval. Not available with `-p`, over ssh, on a remote machine, or in background jobs. |
| Any Mac reachable from a shell (ssh to a headless mini, cron, background sessions) | **Tier 1** - stock macOS: `screencapture` for eyes, System Events (osascript) for hands. No install. This skill's core. |
| Heavy or repeated UI work on that machine: annotated screenshots with element IDs, semantic clicks, background delivery without stealing focus | **Tier 2** - [Peekaboo](https://github.com/steipete/Peekaboo) CLI (`brew install openclaw/tap/peekaboo`, macOS 15+, MIT). |

Browser content is never done with any of these - chrome-control (CDP) is
exact and cheaper.

## Tier 0: the built-in computer use (Claude Code)

Tools are `mcp__computer-use__*` (load them all with one ToolSearch:
query `computer-use`, max_results 30). Enable once per project via `/mcp`
→ `computer-use` → Enable. Requires an interactive session on the local Mac.

**Flow, every session:**

1. `request_access` with the list of apps you need - the user approves per
   app, per session (Finder counts as an app: desktop, Dock, Go to Folder).
   Re-request mid-task when a new app comes up. `list_granted_applications`
   tells you what you already have.
2. `screenshot` first; act; `screenshot` again to verify. Screenshots are
   auto-downscaled - never resize the display. Use `zoom` on a region when
   text is too small instead of guessing.
3. Batch a fixed sequence (`left_click`, `type`, `key`, `wait`) with
   `computer_batch` - one round-trip instead of five. Split the batch at any
   point where you must look before continuing.
4. Type with `type`; shortcuts with `key` (`cmd+s`); paste large text via
   `write_clipboard` + `key cmd+v`; `read_clipboard` to get text back out.

**App tiers** (enforced against the frontmost app, the error names the tier):
browsers → *read* (screenshots only - drive them with chrome-control);
terminals/IDEs → *click* (no typing, no right-click - shell work goes
through Bash); everything else → *full*.

**Behaviour to expect:** other apps are hidden while it works and restored
after the turn; your terminal is excluded from screenshots; one session
holds a machine-wide lock until it exits (a second session errors naming
the holder); the user can abort with Esc at any time. It refuses to
execute trades or move money - hand those to the user. Never click links
in mail/messages with it (open the URL through chrome-control instead).

**When Tier 0 is the wrong tool, even locally:**

- the target is a browser tab, a terminal, or an IDE (tier-limited);
- the action must run without hiding the user's apps or grabbing the
  session lock (a background dialog watcher, a launchd job, a cron);
- the session is `-p`/non-interactive, a subagent, or a background job;
- you need a window that is not frontmost, or a precise element by name
  rather than by pixel.

Those are Tier 1 jobs. **Mixing them in one task is normal:** Tier 0 for
the interactive look-and-click parts, a System Events one-liner (or a
spawned script like chrome-control's `cdp-allow`) for the sheet that pops
up behind it. The TCC grants differ: Tier 0's grants belong to the terminal
app running Claude Code; a Bash one-liner's grants belong to that same
terminal app locally, or to `sshd-keygen-wrapper` over ssh (table below).
Granting both once per machine avoids the "it worked from the MCP but not
from Bash" surprise.

## Prerequisites (TCC) - one human grant per machine

macOS attributes a process's permissions to its **responsible process**,
not to the binary that made the call:

| How the code was launched | Binary TCC blames |
|---|---|
| ssh (any ssh-descended shell, incl. an agent started over ssh) | `/usr/libexec/sshd-keygen-wrapper` |
| a terminal app on the machine | that terminal app (Terminal, iTerm, Ghostty...) |
| a launchd agent/daemon | the executable in `ProgramArguments` (or its .app) |
| an MCP server spawned over stdio | the client app that spawned it - adding the server binary itself does nothing |

Grant that binary, once, in System Settings → Privacy & Security:

- **Screen Recording** (Tahoe names the pane *Screen & System Audio
  Recording*) - needed by `screencapture`. Without it: `could not create
  image from display`, or a wallpaper-only/black image, no other error.
- **Accessibility** - needed for every synthetic click/keystroke and for
  reading other apps' UI trees. Without it: `-25211` / "not allowed
  assistive access".
- **Automation** - per (source app, target app) pair, granted by clicking
  Allow on the "X wants to control System Events" dialog that appears on the
  machine's display the first time. Denied → `-1743`; `AppleEvent timed out
  (-1712)` from a fresh ssh shell means that dialog is up on the display
  right now, unanswered.

Rules that bite:

- Hidden paths (`/usr/libexec/...`, Homebrew) are added with **+** → ⌘⇧G.
  macOS 26.1-26.2 had a bug hiding CLI binaries from these panes entirely;
  dragging the binary from Finder onto the list still granted it. Fixed in
  26.3.
- A grant belongs to the binary's code identity: `brew upgrade` or a
  reinstall of an ad-hoc-signed tool changes the hash and macOS asks again.
  Stale rows can show "on" for a path that no longer exists - `tccutil
  reset Accessibility <bundle-id>` / `tccutil reset ScreenCapture
  <bundle-id>` and re-grant (omitting the bundle id wipes every app).
- A running process keeps its cached verdict: after granting, restart the
  responsible process (Screen Recording often needs a full quit).
- The ssh path works when the ssh user is the same user logged into the
  console session (auto-login on a headless machine). Some guides claim ssh
  grants never work; in practice FDA/Accessibility/Screen Recording on
  `sshd-keygen-wrapper` are what CI boxes rely on.
- The display must be awake and unlocked: `caffeinate -u -t 2` wakes it; the
  login/lock screen ignores synthetic input, so a headless Mac needs
  auto-login (or a human once). Apple-silicon minis create a 1080p virtual
  display with no monitor attached; if screenshots come back *empty* rather
  than permission-denied, the machine has no framebuffer - use a virtual
  display (Mirage, BetterDisplay) or an HDMI dummy plug.

Verify:

```bash
screencapture -x -t jpg /tmp/s.jpg && sips -g pixelWidth /tmp/s.jpg   # real size
osascript -e 'tell application "System Events" to get name of every process whose frontmost is true'
```

These grants and anything asking for an admin password are the only steps
that must be a human; afterwards the agent can dismiss later dialogs itself.

## Tier 1: eyes

```bash
screencapture -x -t jpg /tmp/s.jpg          # full screen, silent; jpg ≈ 5x smaller than png
sips -Z 1440 /tmp/s.jpg >/dev/null          # downscale before reading it into context
screencapture -x -R 0,0,800,600 /tmp/r.jpg  # crop to the region you care about (points) - fewer tokens
screencapture -x -l "$(osascript -e 'tell app "System Events" to tell process "Notes" to get id of window 1')" /tmp/w.jpg  # one window
```

**Pixels vs points.** Retina screenshots are 2x the point size (a 1470x956
point display captures as 2940x1912). Every click/coordinate API below takes
**points**: halve what you measure on an unscaled screenshot, or downscale
the image to point width first (`sips -Z <point width>`). Point size:
`osascript -e 'tell application "Finder" to get bounds of window of desktop'`
→ `0, 0, W, H`.

Prefer the accessibility tree over pixels whenever the target has one - it
gives exact positions and names, and costs no image tokens:

```bash
# windows of the frontmost app
osascript -e 'tell application "System Events" to tell (first process whose frontmost is true) to get {name, position, size} of every window'
# buttons of a window, with the names/descriptions you click by
osascript -e 'tell application "System Events" to tell process "System Settings" to get {name, description, position} of every button of window 1'
# whole tree of a window (large - target a sheet/group when you can)
osascript -e 'tell application "System Events" to tell process "Chrome" to get entire contents of window 1'
```

Iterating `entire contents` inline fails with `-1700`; assign it to a
variable first (`set els to entire contents of sh`, then loop `els`).

## Tier 1: hands

```bash
# click a named element (preferred - no coordinates)
osascript -e 'tell application "System Events" to tell process "System Settings" to click button "Allow" of sheet 1 of window 1'
osascript -e 'tell application "System Events" to tell process "Finder" to click menu item "New Folder" of menu "File" of menu bar 1'
# click at a point (points, not pixels)
osascript -e 'tell application "System Events" to click at {640, 400}'
# bring an app forward when it matters
osascript -e 'tell application "Notes" to activate'
```

Typing goes through the same CoreGraphics event path as a physical
keyboard, so apps and web pages cannot distinguish it:

```bash
osascript -e 'tell application "System Events" to keystroke "hello world"'
osascript -e 'tell application "System Events" to keystroke "s" using command down'
osascript -e 'tell application "System Events" to keystroke "t" using {command down, shift down}'
osascript -e 'tell application "System Events" to key code 36'   # return; 53 esc, 48 tab, 51 delete, 49 space, 123-126 arrows
```

`keystroke` is layout-dependent and drops some non-ASCII on non-US layouts;
for arbitrary text, put it on the clipboard and paste (works over ssh when
the ssh user is the console user):

```bash
printf '%s' "$text" | pbcopy && osascript -e 'tell application "System Events" to keystroke "v" using command down'
```

Scrolling: System Events has no scroll verb; use the target's keyboard
(Page Down, arrows) or `scroll area`'s `value of scroll bar`, or Tier 2.

## The loop

Act → wait 0.3-1.5 s for rendering → verify (accessibility query, or a
cropped screenshot) → next. Never fire a sequence of clicks blind, and don't
screenshot in a tight loop to "watch" - poll the accessibility tree.

## Dialogs and prompts

A system or app dialog that blocks an unattended machine is just a window of
some process - find it, click its button by name. Pattern (chrome-control's
`cdp-allow` is a worked example): poll for a sheet/window whose name
matches, `set els to entire contents of it`, click the button whose
`description` (not always `name`) matches, keep watching briefly because
queued dialogs can appear behind the first one.

Since Mojave, synthetic events are ignored unless the sender has
Accessibility, and a few security prompts (TCC's own consent dialogs) reject
synthetic input regardless - those are the human-only bootstrap above.
Dialogs that ask for an **admin password** accept `keystroke` into the
field, but that means the password transits the shell: only with the user's
explicit say-so, never cached.

## Tier 2: Peekaboo

When Tier 1 gets clumsy (deep trees, many round-trips, apps that need
input without being frontmost):

```bash
peekaboo permissions status                      # Screen Recording + Accessibility (+ synthetic input)
peekaboo see --app Notes --annotate --json       # snapshot id + ui_elements with opaque ids, annotated image
peekaboo click "Save" --app Notes                # by label, or by element id from `see`
peekaboo type "text" --app Notes                 # background delivery to the resolved process
peekaboo press Return --app Notes
peekaboo menu click --app Notes --path "File > New Note"
peekaboo dialog                                  # find/dismiss the frontmost dialog
```

Element ids are bound to the `see` snapshot; re-`see` after the UI changes
rather than replaying old bounds. Prefer it over hand-rolled coordinate
math whenever it is installed. Same TCC rules: over ssh the grants belong to
`sshd-keygen-wrapper`, not to `peekaboo`.

## Don'ts

- No `cliclick`, no PyAutoGUI, no compiled Swift helpers for basic
  clicks/keys - System Events covers Tier 1 with zero installs; Peekaboo is
  the one worthwhile install.
- Never hard-code screen coordinates in a script; read positions from the
  accessibility tree at run time (windows move, displays change).
- Never edit `TCC.db` directly (needs SIP off, breaks on updates); grants are
  the human's, MDM profiles are the only codified alternative.
- Browser content: chrome-control (CDP), not clicks on pixels.
