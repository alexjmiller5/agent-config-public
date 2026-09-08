---
name: mac-control
description: See and drive a Mac's screen from a shell - screenshots, reading the accessibility tree, clicking, typing as a real keyboard, pressing keys, dismissing dialogs - on the local machine or a remote Mac over ssh (a headless mini). Use for ANY native-app or system-dialog automation outside the browser (browser work goes through chrome-control), and whenever a task on a remote Mac needs eyes or hands on its display. Covers the TCC grants that make it possible and which binary macOS blames.
---

# Mac Control

Everything here is stock macOS: `screencapture` for eyes, System Events
(AppleScript) for hands. No extra tools. Works identically in a local shell
and over ssh - the only difference is which binary needs the TCC grants.

## Prerequisites (TCC) - one human grant per machine

macOS attributes a shell command's permissions to its **responsible
process**, not to the command itself:

| How the shell was reached | Binary TCC blames |
|---|---|
| ssh (any ssh-descended shell) | `/usr/libexec/sshd-keygen-wrapper` |
| a terminal app on the machine | that terminal app |
| a launchd agent/daemon | the executable in `ProgramArguments` (or its .app) |

Grant that binary, once, in System Settings → Privacy & Security:

- **Screen Recording** - needed by `screencapture` (without it you get a
  black or wallpaper-only image, no error).
- **Accessibility** - needed for every synthetic click/keystroke and for
  reading other apps' UI trees (error `-25211` / "not allowed assistive
  access" without it).
- **Automation** - per (source, target app) pair; first use pops a dialog
  "X wants to control System Events" on the machine's display - click Allow
  once. Denied or unseen → error `-1743`.

Hidden system paths (`/usr/libexec/...`) are added with **+** → ⌘⇧G in the
file picker. These grants and anything asking for an admin password are the
only steps that must be a human; after them the agent can dismiss later
dialogs itself. Verify:

```bash
screencapture -x -t jpg /tmp/s.jpg && sips -g pixelWidth /tmp/s.jpg   # real size, not 0
osascript -e 'tell application "System Events" to get name of every process whose frontmost is true'
```

The display must be awake and unlocked: `caffeinate -u -t 2` wakes it; the
login/lock screen ignores synthetic input, so a locked headless Mac needs
auto-login (or a human once).

## Eyes

```bash
# full screen, no shutter sound, jpg is 5x smaller than png
screencapture -x -t jpg /tmp/s.jpg
sips -Z 1440 /tmp/s.jpg >/dev/null        # downscale before reading it into context
# a region (points) / a window by id
screencapture -x -R 0,0,800,600 /tmp/r.jpg
```

**Pixels vs points.** Retina screenshots are 2x the point size (a 1470x956
point display captures as 2940x1912). Every click/coordinate API below takes
**points**: halve what you measure on an unscaled screenshot, or downscale
the image to point size first (`sips -Z <point width>`). Get the point size:
`osascript -e 'tell application "Finder" to get bounds of window of desktop'`
→ `0, 0, W, H`.

Prefer the accessibility tree over pixels whenever the target has one - it
gives exact positions and names:

```bash
# windows of the frontmost app
osascript -e 'tell application "System Events" to tell (first process whose frontmost is true) to get {name, position, size} of every window'
# buttons of a window, with the names/descriptions you click by
osascript -e 'tell application "System Events" to tell process "System Settings" to get {name, description, position} of every button of window 1'
# whole tree of a window (can be large - target a sheet/group when you can)
osascript -e 'tell application "System Events" to tell process "Chrome" to get entire contents of window 1'
```

Iterating `entire contents` inline fails with `-1700`; assign it to a
variable first (`set els to entire contents of sh`, then loop `els`).

## Hands

```bash
# click a named element (preferred - no coordinates)
osascript -e 'tell application "System Events" to tell process "System Settings" to click button "Allow" of sheet 1 of window 1'
osascript -e 'tell application "System Events" to tell process "Finder" to click menu item "New Folder" of menu "File" of menu bar 1'
# click at a point (points, not pixels)
osascript -e 'tell application "System Events" to click at {640, 400}'
# focus an app first when it matters
osascript -e 'tell application "Notes" to activate'
```

Typing goes through the same event path as a physical keyboard, so apps
(and web pages) cannot distinguish it:

```bash
osascript -e 'tell application "System Events" to keystroke "hello world"'
osascript -e 'tell application "System Events" to keystroke "s" using command down'
osascript -e 'tell application "System Events" to keystroke "t" using {command down, shift down}'
osascript -e 'tell application "System Events" to key code 36'     # return; 53 esc, 48 tab, 51 delete, 49 space, 123-126 arrows
```

`keystroke` is layout-dependent and drops some non-ASCII on non-US layouts;
for arbitrary text, put it on the clipboard and paste:

```bash
printf '%s' "$text" | pbcopy && osascript -e 'tell application "System Events" to keystroke "v" using command down'
```

Over ssh `pbcopy` writes the console session's pasteboard only if the ssh
session is the same user - it is, for a single-user Mac.

## Dialogs and prompts

A system or app dialog that blocks an unattended machine is just a window
of some process - find it, click its button by name. The pattern (see
chrome-control's `cdp-allow` for a worked example): poll for a sheet/window
whose name matches, `set els to entire contents of it`, click the button
whose `description` (not always `name`) matches, keep watching briefly
because queued dialogs can appear behind the first one.

Dialogs that ask for an **admin password** (Privacy toggles, installers)
accept `keystroke` into the password field, but that means the password
transits the shell - only with the user's explicit say-so, never cached.

## Don'ts

- No `cliclick`, no Python `pyautogui`, no Hammerspoon dependency for
  this - System Events does it all and needs no install.
- Never hard-code screen coordinates in a script; read positions from the
  accessibility tree at run time (windows move, displays change).
- Don't screenshot in a loop to "watch" - poll the accessibility tree; it's
  cheaper and exact.
- Browser content: chrome-control (CDP), not clicks on pixels.
