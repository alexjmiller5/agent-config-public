---
name: bug-hunt
description: Use when asked to bug-hunt, dogfood, exploratory-test, or check a website for broken interactions and responsive UI problems, especially without an existing end-to-end test suite.
---

# Bug hunt

Explore a website, gather reproducible evidence, and manually verify candidate
bugs. A seeded walk supplies breadth; it does not prove the site is correct.

## Before walking

- Confirm the authorized origin, starting routes, production versus fixture,
  and any excluded paths. Prefer a local fixture or staging with synthetic data.
  Existing authorization counts; do not repeatedly ask for it.
- Follow the host environment's browser policy. Have the caller create/group a
  disposable tab and supply its **exact target ID** and CDP endpoint. Never
  choose the first tab, create an ungrouped tab, or close a shared browser.
  Do not attach to a tab with work the caller needs to preserve.
- Inspect the app's analytics endpoints and sensitive GET routes when source is
  available. The walker blocks all other origins and recognizable telemetry,
  auth and mutation paths, but custom same-origin endpoints need manual review.
  If those rules cannot cover the authorized scope, use a fixture instead.
- Keep artifacts outside source control in a private directory. Screenshots,
  URLs, labels and console messages can contain sensitive data. Redact before
  sharing; never include session credentials in a report.

## Run

Requires Python 3.11+, `uv`, and an already running Chrome CDP endpoint. The
PEP 723 script resolves Playwright; it does not install or launch a browser.
Run `--help` for the complete interface. Substitute caller-provided values:

```bash
uv run --script <skill-dir>/scripts/walk.py 'https://example.com/' \
  --cdp http://127.0.0.1:9222 --target <existing-target-id> \
  --output <new-private-artifact-directory> \
  --seed 17 --steps 30 --seconds 90
```

Default widths are phone 390, laptop 1366 and desktop 1920 CSS pixels.
`--widths` overrides them. These are viewport checks, not touch/device emulation.
Steps and time are **total across widths**; cleanup gets at most five additional
seconds: four for normal cleanup, with the remaining second reserved for a
shielded emergency close. A time limit can prevent later widths from being visited. Use separate
runs with fresh output directories for important deep links and different seeds.
A seed repeats choices only when the rendered state and timing match.

The walker prefers unvisited controls, then revisits randomly. It follows
same-origin links, clicks visible controls, selects options and enters synthetic
search text (`--query`). It skips forms, downloads, new-tab links and controls
with recognizable risky labels. It stops at a visible login wall; do not sign
in, bypass a CAPTCHA, or expand scope as part of the walk.

## Guard limits

The selected target intercepts requests before sending them, including redirect
hops. It blocks non-GET/HEAD/OPTIONS methods, other origins, common analytics
paths and auth/mutation hints. It bypasses service workers for the target and
suppresses new popups, workers, WebSockets and WebRTC in guarded documents.

**This is not a read-only guarantee.** GET can mutate state, trigger a cache
write, log visits or send telemetry. Application code can persist selections or other data in localStorage, cookies
and IndexedDB. The walker does not isolate or restore this state: restoring
shared-origin storage could overwrite another tab's changes. Use synthetic
state and a separate caller-managed profile when state preservation matters.
The guard cannot undo prior requests or pre-existing background channels.
It is not a security sandbox for adversarial JavaScript. Third-party assets and
legitimate POST-based reads are blocked too, so the guard may break the UI.
Asset blocks (including fonts and logos) can change layout. Include them as
explicit test limitations using `guard_resource_types` and the blocked records'
`resource_type`/URL fields; do not report their resulting layout as a confirmed
site bug. Do not weaken the guard on production simply to improve coverage.

Cleanup navigates the supplied tab to `about:blank` while the guard is active,
waits for navigation commit, verifies that document, removes interception/hooks,
restores viewport metrics
where possible, then disconnects. **Normal cleanup leaves the existing tab and
shared Chrome open.** The caller owns grouping, final viewport resets and cleanup.

If normal blank navigation fails, cleanup reports `cleanup_error`, freezes the
target and retries blank navigation through CDP. Freeze alone is not sufficient:
Chrome can thaw the page when the connection ends. A verified committed blank
is required; otherwise cleanup emergency-closes only the exact supplied
disposable target through a browser-scoped CDP session, checks Chrome's success
response, and verifies that the target disappeared. It never closes the
browser or other tabs. `cleanup_freeze`, `cleanup_recovered` and
`cleanup_emergency_close` record the outcome. If the connection cannot blank or
close the target, the page may still execute; the report states this explicitly.
Inspect/reset an affected target before reuse; never kill shared Chrome.

## Read and replay

| Artifact | Purpose |
| --- | --- |
| `coverage.json` | Visited URLs/widths, action types/counts, unique controls, guard skips and stopping reason |
| `events.ndjson` | Ordered actions, selectors, URLs, seed metadata, observations and candidates |
| `*.png` | Viewport screenshots before/after actions, keyed by step and width |
| `summary.json` | Compact run outcome; not a bug count |

A screenshot timeout is a candidate observation; it does not abort the walk.
The overall deadline still applies, and snapshots without a screenshot record
`screenshot: null`.

Blocked operations have `classification: guard_skip`: **they are not bugs**.
Console/page errors, HTTP failures, overflow, clipping, overlap and dead clicks
are `candidate` records until replayed. A dead click only means the sampled
DOM/form state did not change; downloads, canvas work and delayed feedback can
look identical. Clipping may be intentional ellipsis, and overlap may be an
expected overlay. The DOM scan inspects at most 5,000 elements; it does not walk
shadow roots or frame documents. Screenshots need human visual inspection.

Replay promising candidates through the same guard and exact action sequence.
Separate guard-induced failures from site defects. Deduplicate by root cause.
Report confirmed issues with severity, route, width, seed, minimal reproduction,
expected/actual behavior and screenshot evidence. List unreproduced candidates
separately. Include coverage and exclusions even when no bugs are confirmed.
Do not equate a zero exit code with a clean site: it means the bounded run ended
normally, including a login stop. Fix only within the caller's authorized scope.

## Verify changes to this skill

```bash
uv run --script <skill-dir>/scripts/test_walk.py \
  --cdp http://127.0.0.1:9222 --target <disposable-grouped-target-id> -v
```

Tests serve local synthetic fixtures and require a locally reachable browser.
They reuse and leave open the supplied tab. They check prohibited requests at
the server, UI signals, login stops, budgets, strict target selection and cleanup.

## Upstream ideas and credits

Discovered through [skills.sh webapp-testing](https://skills.sh/anthropics/skills/webapp-testing)
and [agent-browser](https://skills.sh/vercel-labs/agent-browser/agent-browser);
no upstream skills were installed or copied.

- [Anthropic webapp-testing](https://github.com/anthropics/skills/blob/main/skills/webapp-testing/SKILL.md): inspect rendered state before acting; use Python Playwright and capture console evidence.
- [Vercel dogfood](https://github.com/vercel-labs/agent-browser/blob/main/skill-data/dogfood/SKILL.md): collect reproduction evidence as issues appear and distinguish exploration from confirmed findings. Its authentication and broad interaction workflow is intentionally not adopted here.
- [Playwright Route](https://playwright.dev/python/docs/api/class-route) and [Chrome Fetch protocol](https://chromedevtools.github.io/devtools-protocol/tot/Fetch/): request interception and redirect constraints inform the target-scoped guard.
