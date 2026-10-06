---
name: apple-dev
description: Build, run, test, verify and install iOS and macOS apps as an agent - the just verbs of the Apple templates, the verification ladder (unit tests, SwiftUI preview render, simulator drive with taps and the accessibility tree, physical-device install, macOS app on screen), Apple's Xcode MCP call order, raw xcodebuild/simctl/devicectl fallbacks, and the gotchas. Use for ANY task touching an Xcode project, a simulator, a physical iPhone or Mac app build, SwiftUI previews, .xcresult bundles, or the Xcode MCP server.
---

# Apple Dev

How an agent builds, verifies, and delivers an Xcode project. Local
development uses the **build host** named in the machine sheet (Xcode,
simulators, the `xcode` MCP server). The sheet also identifies the **phone
installer**, the Mac paired to the owner's iPhone. Personal Ad Hoc release
signing runs on a macOS CI runner.

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
| `just deploy` | Local Release Ad Hoc export + phone install (`ios-app` fallback with a stated reason) | `+ IOS_PROFILE`, the Apple Distribution identity in the keychain |
| `just ota` | Serve `build/<App>.ipa` as a tailnet install page (`ios-app` only; blocks while serving) | a verified, decrypted CI IPA or local export; Tailscale with HTTPS certificates |
| `just logs` | Five minutes of device logs into `logs/` (Debug installs only) | `IOS_DEVICE_ID` |

Environment interface: `IOS_TEST_DESTINATION` (simulator, default in the
justfile), `IOS_DERIVED_DATA` (keep it outside any cloud-synced folder),
`IOS_INSTALL_HOST` (ssh host of the phone installer; unset = this Mac
installs). Raw `xcodebuild` output is long: pipe it through `xcbeautify`
when you read it yourself.

## Personal Ad Hoc CI

`ios-app` uses a manual `workflow_dispatch` signing workflow; ordinary
validation runs do not need signing secrets. CI archives and exports for
registered devices, with installation as a separate step. TestFlight and
App Store submission belong to `appstore-app`.

The signing helper accepts `--project`, `--scheme`, and `--output`, with
`IOS_CERTIFICATE_P12_BASE64`, `IOS_CERTIFICATE_PASSWORD`, `IOS_PROFILE_BASE64`,
and optional `IOS_DEVICE_ID`. Credentials come from the project's configured
secret manager. CI imports into a temporary keychain, restores the previous
keychain search list, and removes temporary signing material even on failure.
A runner does not need a desktop login or the phone paired to it.

Generate a temporary age identity in private local scratch for each dispatch.
Supply only its **public** key as `artifact_recipient`; keep the private
identity locally until download/decryption is complete. Watch the workflow,
then download its encrypted `.ipa.age` artifact within the one-day retention
period. Decrypt locally, verify the exported app's signature, bundle/team and
device profile, and place the IPA at the path expected by the project's
install/OTA helper. Remove the temporary identity after decryption and the
decrypted transfer copy when installation no longer needs it.

Public-repository Actions artifacts are not private. Upload only the
encrypted IPA, never standalone profiles, P12 files, private keys, keychains,
or plaintext IPAs. The IPA necessarily contains an embedded provisioning
profile with device IDs; retain it for installation and keep it out of logs.
No persistent encryption key or recipient repository variable is needed.

## Verification ladder

Choose the cheapest sufficient evidence for each affected behavior. A passing
mock does not discharge a separate hardware or interaction requirement.

1. **Logic**: `just test`. Write the test first; mutation-test it.
2. **A view**: `RenderPreview` through the Xcode MCP on the `#Preview` of the
   changed view - an image without booting anything.
3. **The running app on a simulator**: `just run`, then a device-interaction
   session through the Xcode MCP (below). Every capture returns a PNG and the
   accessibility hierarchy (label, frame, a precomputed point to tap); find
   controls by label, never by guessed coordinates. Read `GetConsoleOutput`
   for OSLog and crashes.
4. **Hardware-only behavior** (camera, microphone, ShazamKit, push, HealthKit,
   real network conditions): `just build` (Debug, logs readable) or install
   the verified CI Ad Hoc IPA, then ask the owner for the one check only a
   human can do.
5. **A macOS app**: `just run` opens it from `build/`; look at it and drive it
   with the `mac-control` skill (screenshot, accessibility tree, clicks).

Regression-lock a flow only when the project has one worth locking: add an
XCUITest target then, not by default.

## Deterministic tests and hardware boundaries

Keep business logic independent of transport, clocks and recording devices.
Use the project's existing injection seams; add a small protocol or closure
only where a concrete test needs it. Test fixtures contain synthetic data or
licensed sample audio, never a user's recordings, credentials or identifiers.

| Behavior | Deterministic evidence | Separate acceptance |
|---|---|---|
| Connectivity and retry | Inject timeout, offline and server rejection into the real request path; assert pending/error state, cancellation, retry after recovery and no duplicate submission. Restart and verify recovery when persistence is promised. | Exercise the running app's offline/reconnect UI; real service access and OS background delivery need their own check. |
| Audio processing | Feed a prerecorded fixture through the production decoding/signature/processing path; assert useful output and malformed/empty-input handling. | A fixture proves processing, not microphone access, route selection, capture quality or recognition by a live service. |
| Recording | Inject permission outcomes, interrupted capture and input failure; assert state, duration and cleanup using a controlled clock. | Verify actual permission denied/granted behavior, microphone capture and relevant interruptions on the device that provides them. |
| Taps, swipes and drags | Use current screenshot and accessibility hierarchy to target the running view; perform the gesture and assert its visible result, boundary behavior and cancellation. | A preview or a model method call does not prove hit targets, scrolling or gesture conflicts; capture the resulting UI. |

For a bug, reproduce the user-visible failure before the fix. Test the expected
behavior, then temporarily remove the fix or break the relevant transition to
prove the test detects it. Keep fake services confined to previews/tests or an
explicit development entry point; normal app launches use production services.
Never disable host networking, revoke shared permissions or disturb another
agent's simulator to simulate failure. Use an isolated test instance.

Record which evidence came from a unit test, fixture, simulator, Mac or physical
device. Finish all available programmatic checks before asking for one precise
human-only check. Unavailable microphone, phone, push or signing acceptance
stays unverified with its required action; do not replace it with a mock pass.

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
   file's context. File arguments are project-organization paths
   (`<Project>/App/ContentView.swift`, found with `XcodeGlob`), never
   filesystem paths. "Not built with -Onone" means the Debug configuration
   is optimized: set `SWIFT_OPTIMIZATION_LEVEL: "-Onone"` for Debug in
   `project.yml` (XcodeGen does not) and `just gen`.
5. `DeviceInteractionStartWorkspaceSession` → `DeviceInteractionInstallAndRun`
   → `DeviceInteractionSynthesize` (tap, swipe, type, press, capture) →
   `DeviceInteractionEndSession`. The command grammar for `Synthesize`
   (`t x y` to tap, capture, type, swipe) is in Apple's `device-interaction`
   skill; read it before the first call. Physical devices work here too
   when the session's Mac has the device paired.
6. `GetConsoleOutput` (regex filter) while the app runs;
   `InvokeDebuggerCommand` for LLDB against the running process.
7. `DocumentationSearch` before guessing an API; `XcodeGrep` / `XcodeRead`
   for project-aware search.

Rules:

- **"Waiting for the user to approve this request"** on the first
  workspace call: the agent's code signature is not approved yet. `xcrun
  mcp-server status` lists it under *Pending approvals* with an id. Where
  the machine sheet names an approve helper, run it and retry once;
  otherwise the owner runs `sudo xcrun mcp-server approve --always <id>`.
  Report the id and stop; never retry in a loop. Workspaces outside the permitted folders need
  the same kind of grant (`allow-folder`).
- **Every call hangs, `status` says "the service is running but did not
  answer"**: a windowed Xcode is running on the host and shadows the
  headless server. Quit it (`osascript -e 'tell application "Xcode" to
  quit'`), `xcrun mcp-server stop`, call again. Anything that launches the
  Xcode app (`xcrun agent skills export`, `open *.xcodeproj`, `just dev`)
  recreates the problem on a build host. Apple's skills come headless from
  `xcrun agent plugin path --plugin-format claude` instead.
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

## Phone install

CI produces the artifact; the paired phone installer or an OTA page delivers
it. Download, decrypt, and verify a CI IPA before these steps. Local Debug
builds remain useful for readable device logs. Three install paths:

1. **Local network (default, try it first).** `IOS_INSTALL_HOST` makes `just
   build` / local `just deploy` do the hop. For a CI IPA, use the project's
   install helper on the downloaded artifact without rebuilding or signing
   it again. Copy the artifact to the paired host and run
   `devicectl device install app` there. The phone must be
   on the same network as the installer and visible to it (pairing happened
   once by cable). `devicectl` finds the phone by local discovery, so this
   fails on networks that isolate clients (train, hotel, guest Wi-Fi):
   `devicectl list devices` then shows the phone `unavailable`, its
   `tunnelState` unavailable. It cannot be aimed at a VPN address.
2. **Tailnet install link.** `just ota` (`scripts/ota-install.sh`) serves the
   verified Ad Hoc `.ipa` on the serving Mac's tailnet name over
   HTTPS and prints a URL; the owner opens it in Safari on the phone and taps
   Install. Any network, one tap. It blocks while serving (`OTA_TTL`, default
   900 s): run it in the background, hand over the URL, and confirm with the
   owner that the app updated.
3. **Cable.** The owner plugs the phone into the installer; the install
   command the failed recipe printed then works.

When the local-network install fails because the phone is unreachable, **ask
the owner which of 2 and 3 they prefer** - neither is the default, and both
need them. When the installer itself is asleep or unreachable, report the
artifact path and the install command in one line and continue with what
does not need the phone. No retries, no polling.

Installing an already signed IPA does not require a signing identity on the
installer. Local signing needs an accessible signing keychain: a locked login
keychain can cause `errSecInternalComponent` over SSH. Use the configured
signing setup; CI uses its temporary keychain instead of a desktop session.

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
- **XCUITest cannot read the app's clipboard from the runner**: reading
  `UIPasteboard.general` there hits the cross-app paste permission and never
  returns the copied text. Write a sentinel from the runner (writes are
  allowed), then paste through the OS edit menu into a field of the app
  under test and read that field's value.
- **Read-only SwiftUI rows expose one combined label**: `LabeledContent`
  appears as a single static text `"Label, Value"`. Exact
  `staticTexts["Value"]` lookups never match, so negative checks on them pass
  vacuously; match with `label CONTAINS`.
- **iOS 27 `confirmationDialog` is a popover with no cancel button**: only
  the destructive action is a button. Dismiss by tapping a point outside the
  popover's frame, then assert the sheet is gone.
