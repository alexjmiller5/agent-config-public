# /// script
# requires-python = ">=3.11"
# dependencies = ["playwright>=1.48,<2"]
# ///
"""Bounded exploratory walk on one caller-owned Chrome target. No tabs are created."""

import argparse
import asyncio
import json
import math
import random
import re
import time
from collections import Counter
from contextlib import suppress
from pathlib import Path
from urllib.parse import unquote, urlsplit

from playwright.async_api import Error, async_playwright
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

RISK = re.compile(
    r"(?:^|[^a-z])(auth|oauth|login|log[-_ ]?out|sign[-_ ]?(in|out|up)|checkout|purchase|pay|delete|remove|save|submit|send|subscribe|unsubscribe|export|download|upload|invite|publish|reset|revoke)(?:$|[^a-z])",
    re.IGNORECASE,
)
ANALYTICS = re.compile(
    r"analytics|telemetry|posthog|segment|amplitude|mixpanel|google-analytics|/collect(?:[/?]|$)|/capture(?:[/?]|$)|/track(?:[/?]|$)",
    re.IGNORECASE,
)


def origin(url):
    value = urlsplit(url)
    return (
        value.scheme.lower(),
        value.hostname,
        value.port or (443 if value.scheme == "https" else 80),
    )


def block_reason(method, url, base):
    if method not in {"GET", "HEAD", "OPTIONS"}:
        return "write_method"
    if origin(url) != origin(base):
        return "other_origin"
    decoded = unquote(unquote(url))
    if ANALYTICS.search(decoded):
        return "analytics"
    if RISK.search(urlsplit(decoded).path + "?" + urlsplit(decoded).query):
        return "auth_or_mutation_hint"
    return None


def choose(items, visited, rng):
    fresh = [item for item in items if item["key"] not in visited]
    return rng.choice(fresh or items)


class Log:
    def __init__(self, directory):
        directory.mkdir(parents=True, exist_ok=False, mode=0o700)
        self.directory = directory
        self.file = (directory / "events.ndjson").open("x")
        self.counts = Counter()
        self.urls = set()
        self.guard_skips = Counter()
        self.guard_resource_types = Counter()
        self.action_types = Counter()
        self.step = 0
        self.width = None

    def write(self, kind, **data):
        self.counts[kind] += 1
        classification = "observation"
        if kind == "blocked_request":
            classification = "guard_skip"
            self.guard_skips[data["reason"]] += 1
            self.guard_resource_types[data["resource_type"]] += 1
        elif kind in {"console_error", "page_error", "action_error"} and re.search(
            r"(?:^|Error: )bug-hunt blocked (?:channel|worker)(?:$|\n)",
            data.get("text", ""),
        ):
            classification = "guard_skip"
            self.guard_skips["blocked_channel_or_worker"] += 1
        elif kind in {
            "console_error",
            "page_error",
            "http_error",
            "overflow",
            "possible_clipping",
            "possible_overlap",
            "possible_dead_click",
            "action_error",
            "screenshot_timeout",
        }:
            classification = "candidate"
        if kind == "snapshot":
            self.urls.add(data["url"])
        if kind == "action":
            self.action_types[data["type"] or data["tag"]] += 1
        self.file.write(
            json.dumps(
                dict(
                    ts=time.time(),
                    step=self.step,
                    width=self.width,
                    kind=kind,
                    classification=classification,
                    **data,
                )
            )
            + "\n"
        )
        self.file.flush()

    def close(self):
        self.file.close()


# Applied before the first guarded navigation, and removed on disconnect.
# This reduces accidental new channels; it is not a sandbox against hostile JS.
INIT = r"""(() => {
  if (window.__bugHuntRestore) return;
  const undo = [];
  const replace = (o, k, v) => { const old = o[k]; try {o[k] = v; undo.push(()=>o[k]=old)} catch {} };
  replace(window, 'open', () => null);
  for (const key of ['WebSocket', 'Worker', 'SharedWorker', 'RTCPeerConnection'])
    replace(window, key, function(){throw new Error('bug-hunt blocked channel')});
  if (navigator.serviceWorker)
    replace(navigator.serviceWorker, 'register', () => Promise.reject(new Error('bug-hunt blocked worker')));
  const click = e => {
    const a = e.target.closest?.('a');
    if (a && (a.hasAttribute('download') || (a.target && a.target !== '_self'))) {
      e.preventDefault(); e.stopImmediatePropagation();
    }
  };
  const submit = e => {e.preventDefault(); e.stopImmediatePropagation()};
  document.addEventListener('click', click, true);
  document.addEventListener('submit', submit, true);
  window.__bugHuntRestore = () => {
    undo.reverse().forEach(fn=>fn());
    document.removeEventListener('click', click, true);
    document.removeEventListener('submit', submit, true);
    delete window.__bugHuntRestore;
  };
})()"""


class Guard:
    def __init__(self, page, cdp, base, log):
        self.page, self.cdp, self.base, self.log = page, cdp, base, log
        self.pending = set()
        self.script_id = None
        self.listeners = []
        self.error = None
        self.target_id = None

    async def install(self):
        def paused(event):
            task = asyncio.create_task(self.handle(event))
            self.pending.add(task)
            task.add_done_callback(self.pending.discard)

        self.paused = paused
        self.target_id = (await self.cdp.send("Target.getTargetInfo"))["targetInfo"][
            "targetId"
        ]
        self.cdp.on("Fetch.requestPaused", paused)
        await self.cdp.send("Page.enable")
        await self.cdp.send("Network.enable")
        await self.cdp.send("Network.setBypassServiceWorker", {"bypass": True})
        await self.cdp.send(
            "Fetch.enable",
            {"patterns": [{"urlPattern": "*", "requestStage": "Request"}]},
        )
        self.script_id = (
            await self.cdp.send(
                "Page.addScriptToEvaluateOnNewDocument", {"source": INIT}
            )
        )["identifier"]
        await self.page.evaluate(INIT)
        for event, callback in [
            (
                "console",
                lambda msg: (
                    self.log.write("console_error", text=msg.text)
                    if msg.type == "error"
                    else None
                ),
            ),
            ("pageerror", lambda err: self.log.write("page_error", text=str(err))),
            (
                "response",
                lambda response: (
                    self.log.write(
                        "http_error", url=response.url, status=response.status
                    )
                    if response.status >= 400
                    else None
                ),
            ),
            ("dialog", lambda dialog: asyncio.create_task(dialog.dismiss())),
        ]:
            self.page.on(event, callback)
            self.listeners.append((event, callback))

    async def handle(self, event):
        request = event["request"]
        reason = block_reason(request["method"], request["url"], self.base)
        try:
            if reason:
                self.log.write(
                    "blocked_request",
                    reason=reason,
                    method=request["method"],
                    url=request["url"],
                    resource_type=event.get("resourceType", "Other"),
                )
                await self.cdp.send(
                    "Fetch.failRequest",
                    {"requestId": event["requestId"], "errorReason": "BlockedByClient"},
                )
            else:
                await self.cdp.send(
                    "Fetch.continueRequest", {"requestId": event["requestId"]}
                )
        except Error as error:
            self.error = str(error)
            self.log.write("guard_error", text=self.error)

    async def emergency_close(self):
        session = None
        try:
            async with asyncio.timeout(0.8):
                if not self.target_id:
                    raise Error("Exact supplied target identity unavailable")
                session = await self.page.context.browser.new_browser_cdp_session()
                response = await session.send(
                    "Target.closeTarget", {"targetId": self.target_id}
                )
                if not response.get("success"):
                    raise Error("Chrome did not confirm target closure")
                targets = (await session.send("Target.getTargets"))["targetInfos"]
                if any(target["targetId"] == self.target_id for target in targets):
                    raise Error("Supplied target still exists after close")
                self.log.write(
                    "cleanup_emergency_close", closed=True, target_id=self.target_id
                )
        except (Error, TimeoutError) as error:
            self.log.write(
                "cleanup_emergency_close",
                closed=False,
                target_id=self.target_id,
                manual_reset_required=True,
                text=f"Emergency close failed; target may still execute: {type(error).__name__}: {error}",
            )
        finally:
            if session:
                with suppress(Error, TimeoutError):
                    await asyncio.wait_for(session.detach(), 0.1)

    async def finish_emergency_close(self):
        # Shield protects the child, but cancellation still interrupts its waiter.
        # Retain and finish the bounded child before allowing caller disconnect.
        task = asyncio.create_task(self.emergency_close())
        cancelled = False
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                cancelled = True
        task.result()
        if cancelled:
            raise asyncio.CancelledError

    async def close(self):
        for event, callback in self.listeners:
            self.page.remove_listener(event, callback)
        try:
            await self.cdp.send("Page.stopLoading")
            await self.page.goto("about:blank", wait_until="commit", timeout=2000)
            if self.page.url != "about:blank" or not await self.page.evaluate(
                "location.href === 'about:blank' && document.body.childElementCount === 0"
            ):
                raise Error("Cleanup could not verify a blank document")
        except asyncio.CancelledError:
            await self.finish_emergency_close()
            raise
        except Error:
            try:
                await asyncio.wait_for(
                    self.cdp.send("Page.setWebLifecycleState", {"state": "frozen"}), 0.5
                )
                self.log.write(
                    "cleanup_freeze", frozen=True, manual_reset_required=True
                )
                # Freeze can end on disconnect. Require a committed blank or close.
                navigation = await asyncio.wait_for(
                    self.cdp.send("Page.navigate", {"url": "about:blank"}), 0.5
                )
                if navigation.get("errorText"):
                    raise Error(navigation["errorText"])
                async with asyncio.timeout(0.5):
                    while True:
                        frame = (await self.cdp.send("Page.getFrameTree"))["frameTree"][
                            "frame"
                        ]
                        if frame["url"] == "about:blank" and frame.get(
                            "loaderId"
                        ) == navigation.get("loaderId"):
                            break
                        await asyncio.sleep(0.02)
                await self.cdp.send("Page.setWebLifecycleState", {"state": "active"})
                self.log.write("cleanup_recovered", blank_verified=True)
            except (Error, TimeoutError, asyncio.CancelledError) as recovery_error:
                self.log.write(
                    "cleanup_freeze",
                    frozen=False,
                    manual_reset_required=True,
                    text=f"Freeze/blank recovery failed: {type(recovery_error).__name__}: {recovery_error}",
                )
                await self.finish_emergency_close()
                if isinstance(recovery_error, asyncio.CancelledError):
                    raise
            raise
        if self.script_id:
            await self.cdp.send(
                "Page.removeScriptToEvaluateOnNewDocument",
                {"identifier": self.script_id},
            )
            self.script_id = None
        with suppress(Error):
            await self.page.evaluate("window.__bugHuntRestore?.()")
        await self.cdp.send("Fetch.disable")
        if self.pending:
            await asyncio.gather(*self.pending)
        self.cdp.remove_listener("Fetch.requestPaused", self.paused)
        await self.cdp.send("Network.setBypassServiceWorker", {"bypass": False})


SCAN = r"""() => {
 const visible = e => {const r=e.getBoundingClientRect(); const s=getComputedStyle(e);
   return r.width>0 && r.height>0 && s.visibility!=='hidden' && s.display!=='none'};
 const selector = e => {const p=[]; while(e && e.nodeType===1) {
   let n=1; for(let s=e.previousElementSibling;s;s=s.previousElementSibling) if(s.tagName===e.tagName)n++;
   p.unshift(e.tagName.toLowerCase()+':nth-of-type('+n+')'); e=e.parentElement;
 } return p.join(' > ')};
 const nodes=[...document.querySelectorAll('body *')].slice(0,5000).filter(visible);
 return {
  login: nodes.some(e=>e.matches('input[type=password]')) ||
    /^(sign in|log in|authentication required|access denied|verify you are human)$/im.test(document.querySelector('h1')?.innerText.trim() || ''),
  overflow: Math.max(document.documentElement.scrollWidth,document.body?.scrollWidth||0)>innerWidth+2,
  clipping: nodes.filter(e=>{const s=getComputedStyle(e); return e.innerText?.trim() &&
    ((['hidden','clip'].includes(s.overflowX) && e.scrollWidth>e.clientWidth+3) ||
    (['hidden','clip'].includes(s.overflowY) && e.scrollHeight>e.clientHeight+3))
  }).slice(0,20).map(selector),
  overlap: nodes.filter(e=>{
    if (!e.matches('a[href],button,input,select,summary,[role=button]')) return false;
    const r=e.getBoundingClientRect(), x=r.x+r.width/2, y=r.y+r.height/2;
    if(x<0 || y<0 || x>=innerWidth || y>=innerHeight) return false;
    const hit=document.elementFromPoint(x,y); return hit && hit!==e && !e.contains(hit);
  }).slice(0,20).map(selector),
  items: nodes.filter(e=>e.matches('a[href], button, [role=button], input[type=search], input[type=checkbox], select, summary') &&
    !e.disabled && e.getAttribute('aria-disabled')!=='true' && !e.closest('form') &&
    !e.hasAttribute('download') && (!e.target || e.target==='_self'))
   .map(e=>({selector:selector(e), label:(e.getAttribute('aria-label')||e.innerText||e.name||'').trim().slice(0,160),
     tag:e.tagName.toLowerCase(), type:e.type, href:e.href||null,
     options:e.tagName==='SELECT'?[...e.options].filter(o=>!o.disabled && o.value).map(o=>o.value):[]}))
 }
}"""
STATE = "() => JSON.stringify([location.href, document.body.innerText, [...document.querySelectorAll('input,select,[aria-expanded],[aria-selected]')].map(e=>[e.value,e.checked,e.getAttribute('aria-expanded'),e.getAttribute('aria-selected')])])"


async def inspect(page, log, label):
    state = await page.evaluate(SCAN)
    shot = f"{log.step:04d}-{log.width or 0}-{label}.png"
    try:
        await page.screenshot(path=str(log.directory / shot), timeout=3000)
    except PlaywrightTimeoutError as error:
        log.write("screenshot_timeout", url=page.url, text=str(error))
        shot = None
    log.write("snapshot", url=page.url, screenshot=shot)
    if state["overflow"]:
        log.write("overflow", url=page.url, screenshot=shot)
    for selector in state["clipping"]:
        log.write("possible_clipping", selector=selector, url=page.url, screenshot=shot)
    for selector in state["overlap"]:
        log.write("possible_overlap", selector=selector, url=page.url, screenshot=shot)
    return state


async def find_page(browser, target):
    for context in browser.contexts:
        for page in context.pages:
            cdp = await context.new_cdp_session(page)
            info = await cdp.send("Target.getTargetInfo")
            if info["targetInfo"]["targetId"] == target:
                return page, cdp
            await cdp.detach()
    raise ValueError("Requested target does not exist; refusing to use another tab")


async def run(page, cdp, opts):
    reason = block_reason("GET", opts.url, opts.url)
    if reason:
        raise ValueError(f"Starting URL refused: {reason}")
    log = Log(opts.output)
    guard = Guard(page, cdp, opts.url, log)
    rng, visited = random.Random(opts.seed), set()
    result = {"seed": opts.seed, "actions": 0, "viewports": [], "stop": "step_budget"}
    old_viewport = page.viewport_size
    log.write(
        "start",
        url=opts.url,
        seed=opts.seed,
        steps=opts.steps,
        seconds=opts.seconds,
        widths=opts.widths,
    )
    try:
        async with asyncio.timeout(opts.seconds):
            await guard.install()
            for width in opts.widths:
                log.width = width
                await page.set_viewport_size(
                    {"width": width, "height": 900 if width >= 1000 else 844}
                )
                await page.goto(opts.url, wait_until="domcontentloaded", timeout=5000)
                await asyncio.sleep(opts.settle_ms / 1000)
                result["viewports"].append(width)
                while True:
                    state = await inspect(page, log, "state")
                    if guard.error:
                        result["stop"] = "guard_error"
                        return result
                    if state["login"]:
                        log.write("login_wall", url=page.url)
                        result["stop"] = "login_wall"
                        return result
                    if result["actions"] >= opts.steps:
                        break
                    items = [
                        dict(item, key=f"{width}:{page.url}:{item['selector']}")
                        for item in state["items"]
                        if not RISK.search(item["label"])
                        and not (
                            item["href"] and block_reason("GET", item["href"], opts.url)
                        )
                    ]
                    if not items:
                        break
                    item = choose(items, visited, rng)
                    visited.add(item["key"])
                    result["actions"] += 1
                    log.step = result["actions"]
                    log.write("action", url=page.url, **item)
                    before = await page.evaluate(STATE)
                    locator = page.locator(item["selector"])
                    try:
                        if item["type"] == "search":
                            await locator.fill(opts.query, timeout=1500)
                        elif item["tag"] == "select" and item["options"]:
                            await locator.select_option(
                                rng.choice(item["options"]), timeout=1500
                            )
                        else:
                            await locator.click(timeout=1500)
                        await asyncio.sleep(opts.settle_ms / 1000)
                        if before == await page.evaluate(STATE):
                            log.write(
                                "possible_dead_click",
                                selector=item["selector"],
                                url=page.url,
                            )
                    except Error as error:
                        log.write(
                            "action_error", text=str(error), selector=item["selector"]
                        )
                    after = await inspect(page, log, "after")
                    if after["login"]:
                        log.write("login_wall", url=page.url)
                        result["stop"] = "login_wall"
                        return result
                    # Divide actions among widths, while still inspecting each width with zero budget.
                    if result["actions"] >= max(
                        1, opts.steps * len(result["viewports"]) // len(opts.widths)
                    ):
                        break
    except TimeoutError:
        result["stop"] = "time_budget"
    except Error as error:
        result["stop"] = "browser_error"
        log.write("browser_error", text=str(error))
    finally:
        try:
            async with asyncio.timeout(4):
                await guard.close()
                if old_viewport:
                    await page.set_viewport_size(old_viewport)
                else:
                    await cdp.send("Emulation.clearDeviceMetricsOverride")
        except (Error, TimeoutError) as error:
            result["stop"] = "cleanup_error"
            log.write("cleanup_error", text=str(error))
        coverage = dict(
            result,
            urls=sorted(log.urls),
            action_types=dict(log.action_types),
            guard_skips=dict(log.guard_skips),
            guard_resource_types=dict(log.guard_resource_types),
            unique_controls=len(visited),
        )
        (opts.output / "coverage.json").write_text(
            json.dumps(coverage, indent=2) + "\n"
        )
        log.write("finish", **result, counts=dict(log.counts))
        (opts.output / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
        log.close()
    return result


async def main(opts):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.connect_over_cdp(opts.cdp, timeout=10000)
        page, cdp = await find_page(browser, opts.target)
        try:
            result = await run(page, cdp, opts)
            print(json.dumps(result))
            return (
                1
                if result["stop"] in {"guard_error", "browser_error", "cleanup_error"}
                else 0
            )
        finally:
            with suppress(Error):
                await cdp.detach()
        # Playwright disconnects here. Never browser.close() or context.close().


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument(
        "--cdp", required=True, help="Caller-provided Chrome CDP endpoint"
    )
    parser.add_argument(
        "--target",
        required=True,
        help="Exact existing page target ID; never creates a tab",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="New private artifact directory outside source control",
    )
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument(
        "--steps", type=int, default=30, help="Total action budget across viewports"
    )
    parser.add_argument(
        "--seconds",
        type=float,
        default=90,
        help="Total run budget; cleanup may take 5 extra seconds",
    )
    parser.add_argument("--widths", type=int, nargs="+", default=[390, 1366, 1920])
    parser.add_argument(
        "--query",
        default="test",
        help="Synthetic search text; never real personal data",
    )
    parser.add_argument("--settle-ms", type=int, default=350)
    opts = parser.parse_args()
    if (
        opts.steps < 0
        or not math.isfinite(opts.seconds)
        or opts.seconds <= 0
        or opts.settle_ms < 0
        or any(w < 240 or w > 4096 for w in opts.widths)
    ):
        parser.error(
            "Use nonnegative steps/settle, finite positive seconds and widths 240..4096"
        )
    if (
        urlsplit(opts.url).scheme not in {"http", "https"}
        or urlsplit(opts.url).username
    ):
        parser.error("URL must be HTTP(S) without embedded credentials")
    return opts


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main(parse_args())))
