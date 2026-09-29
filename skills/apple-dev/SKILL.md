---
name: apple-dev
description: Build, run, test, verify and install iOS and macOS apps as an agent - the just verbs of the Apple templates, the verification ladder (unit tests, SwiftUI preview render, simulator drive with taps and the accessibility tree, physical-device install, macOS app on screen), Apple's Xcode MCP call order, raw xcodebuild/simctl/devicectl fallbacks, and the gotchas. Use for ANY task touching an Xcode project, a simulator, a physical iPhone or Mac app build, SwiftUI previews, .xcresult bundles, or the Xcode MCP server.
---

# Apple Dev

How an agent works on an Xcode project without a human at the keyboard. The
machine sheet (loaded at session start) says which Mac is the **build host**
(Xcode 27, simulators, the `xcode` MCP server) and which is the **phone
installer** (the Mac the owner's iPhone is paired to). This skill is the
procedure; it names no machine.

## Verbs

Every Apple template (`ios-app`, `appstore-app`, `macos-app`) ships the same
`just` interface; a project's justfile is the truth for its own extras.

| Verb | Does | Needs |
|---|---|---|
| `just gen` | XcodeGen regenerates the `.xcodeproj` from `project.yml` (every other verb runs it first) | `xcodegen` |
| `just check` | Unsigned build - the CI gate | nothing |
| `just test` | Unit tests on a simulator (iOS) or the Mac (macOS) | a simulator runtime |
| `just run` | Debug build, boot the simulator if needed, install, launch; prints `bundle=<id> simulator=<udid>` (macOS: opens the app from `build/`) | a simulator runtime |
| `just build` | Debug build + install on the phone (automatic signing, readable logs) | `IOS_DEVELOPMENT_TEAM`, `IOS_DEVICE_ID`, Xcode signed into the team |
| `just deploy` | Release Ad Hoc `.ipa` in `build/` + install on the phone (`ios-app` only; the other two deploy through CI) | `+ IOS_PROFILE`, the Apple Distribution identity in the keychain |
| `just logs` | Five minutes of device logs into `logs/` (Debug installs only) | `IOS_DEVICE_ID` |

Environment interface: `IOS_TEST_DESTINATION` (simulator, default in the
justfile), `IOS_DERIVED_DATA` (keep it outside any cloud-synced folder),
`IOS_INSTALL_HOST` (ssh host of the phone installer; unset = this Mac
installs). Raw `xcodebuild` output is long: pipe it through `xcbeautify`
when you read it yourself.

## Verification ladder

Cheapest rung that proves the change, then stop.

1. **Logic**: `just test`. Write the test first; mutation-test it.
2. **A view**: `RenderPreview` through the Xcode MCP on the `#Preview` of the
   changed view - an image without booting anything.
3. **The running app on a simulator**: `just run`, then a device-interaction
   session through the Xcode MCP (below). Every capture returns a PNG and the
   accessibility hierarchy (label, frame, a precomputed point to tap); find
   controls by label, never by guessed coordinates. Read `GetConsoleOutput`
   for OSLog and crashes.
4. **Hardware-only behavior** (camera, microphone, ShazamKit, push, HealthKit,
   real network conditions): `just build` (Debug, logs readable) or `just
   deploy` on the phone, then ask the owner for the one check only a human
   can do.
5. **A macOS app**: `just run` opens it from `build/`; look at it and drive it
   with the `mac-control` skill (screenshot, accessibility tree, clicks).

Regression-lock a flow only when the project has one worth locking: add an
XCUITest target then, not by default.

## The Xcode MCP server

Declared as `xcode` (`xcrun mcpbridge`), backed by Xcode's headless
`mcp-server` daemon, so no Xcode window is needed. The tool list is the same
(54 tools) whatever the state; a short list means the server is broken, not
that a workspace is missing.

Call order for a project:

1. `XcodeOpenWorkspace` on the `.xcodeproj` (after `just gen`) and keep its
   `workspaceIdentifier`: headless calls take it explicitly, every time.
2. `XcodeListSchemes` / `XcodeListRunDestinations` once, then `BuildProject`;
   errors come from `GetBuildLog` (filter to errors) rather than the raw log.
3. `RunAllTests` / `RunSomeTests`; `GetTestList` to pick.
4. `RenderPreview` for a view; `RunCodeSnippet` to evaluate an expression in a
   file's context.
5. `DeviceInteractionStartWorkspaceSession` → `DeviceInteractionInstallAndRun`
   → `DeviceInteractionSynthesize` (tap, swipe, type, press, capture) →
   `DeviceInteractionEndSession`. Physical devices work here too when the
   session's Mac has the device paired.
6. `GetConsoleOutput` (regex filter) while the app runs;
   `InvokeDebuggerCommand` for LLDB against the running process.
7. `DocumentationSearch` before guessing an API; `XcodeGrep` / `XcodeRead`
   for project-aware search.

Rules:

- **"Waiting for the user to approve this request"** on the first
  workspace call: the agent's code signature is not approved yet. `xcrun
  mcp-server status` lists it under *Pending approvals* with an id; the
  owner runs `sudo xcrun mcp-server approve <id>` once. Report the id and
  stop; never retry in a loop. Workspaces outside the permitted folders need
  the same kind of grant (`allow-folder`).
- **Every call hangs, `status` says "the service is running but did not
  answer"**: a windowed Xcode is running on the host and shadows the
  headless server. Quit it (`osascript -e 'tell application "Xcode" to
  quit'`), `xcrun mcp-server stop`, call again. Anything that launches the
  Xcode app (`xcrun agent skills export`, `open *.xcodeproj`, `just dev`)
  recreates the problem on a build host.
- `xcrun mcp-server show-logs` prints the path of the agent activity log:
  every connection, refusal and tool call, with the reason.
- The MCP closes the build and runtime loop; it does not see a 10-pixel
  layout mistake for you - capture and look.

## Raw fallbacks (no MCP, CI, scripts)

```bash
xcodebuild -project App.xcodeproj -scheme App -destination "platform=iOS Simulator,name=iPhone 17" test 2>&1 | xcbeautify
xcrun xcresulttool get test-results summary --path build/App.xcresult   # or: get --format json --path
xcrun simctl list devices available --json | jq '.devices[][] | select(.name=="iPhone 17") | .udid'
xcrun simctl boot <udid>; xcrun simctl install <udid> path/to/App.app; xcrun simctl launch <udid> <bundle-id>
xcrun simctl io <udid> screenshot shot.png
xcrun simctl spawn <udid> log stream --predicate 'subsystem == "<bundle-id>"' --style compact
xcrun devicectl list devices
xcrun devicectl device install app --device <udid> build/App.ipa
xcrun devicectl device process launch --device <udid> --console <bundle-id>
```

## Phone install from the build host

The build host has no phone; the phone installer does. `IOS_INSTALL_HOST`
makes `just build` / `just deploy` do the hop: build and sign here, `scp`
the artifact to that host, run `devicectl device install app` there. The
phone must be on the same Wi-Fi as the installer (pairing happened once by
cable). When the installer is asleep or unreachable the recipe prints the
artifact path and the exact install command and exits non-zero: report that
line to the owner and continue with what does not need the phone. No
retries, no polling.

## Gotchas

- **Derived data outside cloud-synced folders** (`IOS_DERIVED_DATA` or the
  justfile default under `~/Library/Developer`): resource forks from a sync
  client break code signing with opaque `codesign` errors.
- **Simulator Keychain needs an identity**: `CODE_SIGN_IDENTITY=-` with
  signing allowed (the `ios-app` `just test` does this); a fully unsigned
  build reads and writes no Keychain items.
- **`xcodegen` behind a package-manager symlink** cannot find its bundled
  settings presets; resolve the real executable (`realpath "$(command -v
  xcodegen)"`) - the templates' `just gen` already does.
- **Cloud-evicted inputs**: a project under a synced folder can have
  dataless files; empty reads and "no such module" in a clean tree mean
  eviction, not a code problem. Materialize the tree first.
- **Only Debug installs have readable logs**: Release strips
  `get-task-allow`; `just logs` on a Release install returns nothing.
- **MCP grants are per code signature**: the approved binary is the agent
  itself; a wrapper (`timeout`, a shell script) gets approved instead and
  the agent stays blocked. Unsigned binaries get 24-hour grants only.
- **Signing from a shell without a desktop login** (ssh, a headless build
  host): the login keychain refuses with "User interaction is not allowed"
  on import and `errSecInternalComponent` on codesign. Signing identities
  for such a host live in a dedicated keychain that the shell unlocks
  itself, as CI does.
- **App Store installs need root**: `mas install` cannot run inside a
  non-interactive switch; the first install of Xcode comes from the App
  Store app, and an installed Xcode with an unaccepted license stops
  Homebrew entirely until `xcodebuild -license accept` runs as root.
- **"Profile doesn't match" / "no identity found"** on `just deploy`: the
  Apple Distribution identity or the Ad Hoc profile is not installed on this
  Mac; both are machine setup, not a project bug.
- **Full rebuilds per MCP call**: the server does not track incremental
  state between invocations; batch edits before rebuilding.
