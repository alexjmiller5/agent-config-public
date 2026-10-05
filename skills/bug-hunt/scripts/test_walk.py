# /// script
# requires-python = ">=3.11"
# dependencies = ["playwright>=1.48,<2"]
# ///
"""Local-fixture integration tests; caller supplies a disposable, grouped CDP tab."""

import argparse
import asyncio
import importlib.util
import io
import json
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stderr
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from playwright.async_api import Error, async_playwright

sys.dont_write_bytecode = True

SPEC = importlib.util.spec_from_file_location(
    "walk", Path(__file__).with_name("walk.py")
)
walk = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(walk)

ARGS = None


class PolicyTests(unittest.TestCase):
    def test_request_policy(self):
        base = "http://localhost:8000"
        for method, url in [
            ("POST", base + "/save"),
            ("PUT", base + "/save"),
            ("GET", "http://localhost:8001/out"),
            ("GET", base + "/api/auth/google"),
            ("GET", base + "/logout"),
            ("GET", base + "/%6cogin"),
            ("GET", base + "/analytics/collect"),
            ("GET", base + "/?action=delete"),
        ]:
            with self.subTest(method=method, url=url):
                self.assertIsNotNone(walk.block_reason(method, url, base))
        self.assertIsNone(walk.block_reason("GET", base + "/products?q=book", base))

    def test_nonfinite_time_budget_is_rejected(self):
        for value in ["inf", "-inf", "nan"]:
            args = [
                "walk.py",
                "https://example.com",
                "--cdp",
                "http://localhost:9222",
                "--target",
                "fixture",
                "--output",
                "unused",
                "--seconds=" + value,
            ]
            with (
                self.subTest(value=value),
                patch.object(sys, "argv", args),
                redirect_stderr(io.StringIO()),
            ):
                with self.assertRaises(SystemExit) as raised:
                    walk.parse_args()
                self.assertEqual(raised.exception.code, 2)

    def test_guard_exceptions_are_skips_but_other_errors_stay_candidates(self):
        with tempfile.TemporaryDirectory() as temp:
            log = walk.Log(Path(temp) / "events")
            log.write("page_error", text="bug-hunt blocked channel")
            log.write("console_error", text="Error: bug-hunt blocked worker")
            log.write("page_error", text="TypeError: application failed")
            log.close()
            events = [
                json.loads(line)
                for line in (log.directory / "events.ndjson").read_text().splitlines()
            ]
            self.assertEqual(
                [e["classification"] for e in events],
                ["guard_skip", "guard_skip", "candidate"],
            )

    def test_seeded_unvisited_first(self):
        import random

        choices = [{"key": "a"}, {"key": "b"}, {"key": "c"}]
        self.assertEqual(walk.choose(choices, {"a", "b"}, random.Random(7))["key"], "c")
        self.assertEqual(
            walk.choose(choices, set(), random.Random(7)),
            walk.choose(choices, set(), random.Random(7)),
        )


class BrowserTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.hits = []
        hits = self.hits

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_POST(self):
                hits.append(("POST", self.path))
                self.send_response(204)
                self.end_headers()

            def do_GET(self):
                hits.append(("GET", self.path))
                if self.path == "/redirect":
                    self.send_response(302)
                    self.send_header("Location", "/auth/callback")
                    self.end_headers()
                    return
                self.send_response(500 if self.path == "/broken" else 200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                if self.path == "/wall":
                    html = '<h1>Sign in</h1><input type="password"><button>Continue</button>'
                elif self.path == "/late-wall":
                    html = """<button type="button" onclick="document.body.innerHTML='<h1>Sign in</h1><input type=password>'">Show panel</button>"""
                elif self.path == "/pulse-page":
                    html = "<script>setInterval(()=>fetch('/pulse-write',{method:'POST'}).catch(()=>{}),20)</script>"
                elif self.path == "/clean":
                    html = '<h1>Clean</h1><button type="button">No effect</button>'
                else:
                    html = """<h1>Fixture</h1><img src="http://localhost:EXTERNAL/logo.svg">
<div style="width:2400px">Overflow</div>
<div style="width:30px;height:10px;overflow:hidden">A long clipped label</div>
<button style="position:fixed;top:200px;left:20px">Covered</button>
<div style="position:fixed;top:190px;left:10px;width:200px;height:80px;background:white;z-index:999"></div>
<button type="button">No effect</button>
<button type="button" onclick="document.querySelector('h1').textContent='Changed'">Show detail</button>
<script>
console.error('fixture console error');
setTimeout(() => {throw new Error('fixture page error')}, 20);
fetch('/save', {method:'POST'}).catch(()=>{});
navigator.sendBeacon('/beacon', 'payload');
fetch('/analytics/collect').catch(()=>{});
fetch('/auth/callback').catch(()=>{});
fetch('/redirect').catch(()=>{});
fetch('/broken');
fetch('http://localhost:EXTERNAL/out').catch(()=>{});
</script>""".replace("EXTERNAL", str(self.server.server_port))
                self.wfile.write(html.encode())

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.temp = tempfile.TemporaryDirectory()
        self.pw = await async_playwright().start()
        self.browser = await self.pw.chromium.connect_over_cdp(ARGS.cdp)
        self.page, self.cdp = await walk.find_page(self.browser, ARGS.target)
        await self.cdp.send("Emulation.setScriptExecutionDisabled", {"value": False})
        await self.cdp.send("Page.setWebLifecycleState", {"state": "active"})
        await self.page.goto("about:blank")

    async def asyncTearDown(self):
        await self.cdp.send("Emulation.setScriptExecutionDisabled", {"value": False})
        await self.cdp.send("Page.setWebLifecycleState", {"state": "active"})
        await self.page.goto("about:blank")
        await self.cdp.detach()
        await self.pw.stop()
        await asyncio.to_thread(self.server.shutdown)
        self.server.server_close()
        self.temp.cleanup()

    async def test_guard_and_ui_findings(self):
        before = [p for c in self.browser.contexts for p in c.pages]
        log = walk.Log(Path(self.temp.name) / "guard")
        guard = walk.Guard(self.page, self.cdp, self.base, log)
        await guard.install()
        try:
            await self.page.goto(self.base + "/")
            await asyncio.sleep(0.4)
            await walk.inspect(self.page, log, "fixture")
            for destination in [
                self.base + "/auth/direct",
                self.base.replace("127.0.0.1", "localhost") + "/out",
            ]:
                with self.assertRaises(Error):
                    await self.page.goto(destination, timeout=3000)
                await asyncio.sleep(0.1)
                await self.page.goto("about:blank")
            await self.page.goto(self.base + "/")
            await self.page.evaluate("window.open('/clean', '_blank')")
            await asyncio.sleep(0.1)
            self.assertEqual(
                before, [p for c in self.browser.contexts for p in c.pages]
            )
        finally:
            await guard.close()
            log.close()
        self.assertIn(("GET", "/broken"), self.hits)
        self.assertNotIn(("POST", "/save"), self.hits)
        for forbidden in [
            "/logo.svg",
            "/beacon",
            "/analytics/collect",
            "/auth/callback",
            "/auth/direct",
            "/out",
        ]:
            self.assertFalse(any(path == forbidden for _, path in self.hits), self.hits)
        events = [
            json.loads(line)
            for line in (Path(self.temp.name) / "guard" / "events.ndjson")
            .read_text()
            .splitlines()
        ]
        kinds = {event["kind"] for event in events}
        self.assertTrue(
            {
                "blocked_request",
                "console_error",
                "page_error",
                "http_error",
                "overflow",
                "possible_clipping",
                "possible_overlap",
            }
            <= kinds,
            kinds,
        )
        self.assertTrue(list((Path(self.temp.name) / "guard").glob("*.png")))
        self.assertTrue(
            any(
                e.get("resource_type") == "Image"
                and e["classification"] == "guard_skip"
                for e in events
            )
        )
        self.assertTrue(
            all(
                e["classification"] == "guard_skip"
                for e in events
                if e["kind"] == "blocked_request"
            )
        )
        self.assertTrue(await self.page.evaluate("!window.__bugHuntRestore"))

    async def test_walk_budget_dead_click_and_login(self):
        opts = argparse.Namespace(
            url=self.base + "/clean",
            output=Path(self.temp.name) / "walk",
            seed=17,
            steps=2,
            seconds=12,
            widths=[390, 1366, 1920],
            query="sample",
            settle_ms=80,
        )
        result = await walk.run(self.page, self.cdp, opts)
        self.assertLessEqual(result["actions"], 2)
        self.assertEqual(result["viewports"], [390, 1366, 1920])
        events = (opts.output / "events.ndjson").read_text()
        self.assertIn('"kind": "possible_dead_click"', events)
        coverage = json.loads((opts.output / "coverage.json").read_text())
        self.assertEqual(coverage["actions"], 2)
        self.assertIn(self.base + "/clean", coverage["urls"])
        self.assertEqual(coverage["viewports"], [390, 1366, 1920])
        opts.url = self.base + "/wall"
        opts.output = Path(self.temp.name) / "login"
        result = await walk.run(self.page, self.cdp, opts)
        self.assertEqual(result["stop"], "login_wall")
        self.assertEqual(result["actions"], 0)
        self.assertFalse(self.page.is_closed())

    async def test_login_after_last_action_and_time_budget(self):
        opts = argparse.Namespace(
            url=self.base + "/late-wall",
            output=Path(self.temp.name) / "late",
            seed=17,
            steps=1,
            seconds=10,
            widths=[390],
            query="sample",
            settle_ms=50,
        )
        result = await walk.run(self.page, self.cdp, opts)
        self.assertEqual(result["stop"], "login_wall")
        opts.output = Path(self.temp.name) / "timed"
        opts.url = self.base + "/clean"
        opts.seconds = 0.05
        import time

        started = time.monotonic()
        result = await walk.run(self.page, self.cdp, opts)
        self.assertEqual(result["stop"], "time_budget")
        self.assertLess(time.monotonic() - started, 6)
        self.assertEqual(self.page.url, "about:blank")
        self.assertTrue((opts.output / "summary.json").exists())

    async def test_cleanup_does_not_remove_guard_when_blank_navigation_fails(self):
        log = walk.Log(Path(self.temp.name) / "cleanup")
        guard = walk.Guard(self.page, self.cdp, self.base, log)
        await guard.install()
        await self.page.goto(self.base + "/clean")
        try:
            with (
                patch.object(
                    self.page,
                    "goto",
                    AsyncMock(side_effect=Error("simulated navigation failure")),
                ),
                patch.object(self.cdp, "send", wraps=self.cdp.send) as send,
            ):
                with self.assertRaises(Error):
                    await guard.close()
                methods = [call.args[0] for call in send.call_args_list]
                self.assertIn("Page.setWebLifecycleState", methods)
                self.assertNotIn("Fetch.disable", methods)
                self.assertNotIn("Page.removeScriptToEvaluateOnNewDocument", methods)
        finally:
            await self.cdp.send(
                "Emulation.setScriptExecutionDisabled", {"value": False}
            )
            await self.cdp.send("Page.setWebLifecycleState", {"state": "active"})
            await self.page.goto("about:blank")
            await guard.close()
            log.close()

    async def test_double_failure_closes_only_supplied_target_and_reports_failures(
        self,
    ):
        for close_success in (True, False):
            with self.subTest(close_success=close_success):
                log = walk.Log(Path(self.temp.name) / f"double-failure-{close_success}")
                guard = walk.Guard(self.page, self.cdp, self.base, log)
                await guard.install()
                await self.page.goto(self.base + "/clean")
                send = self.cdp.send
                targets = []

                async def fail_freeze(
                    method,
                    params=None,
                    targets=targets,
                    close_success=close_success,
                    send=send,
                ):
                    if method == "Page.setWebLifecycleState":
                        raise Error("simulated freeze failure")
                    if method == "Target.closeTarget":
                        targets.append(params["targetId"])
                        return {"success": close_success}
                    if method == "Target.getTargets":
                        return {"targetInfos": []}
                    return await send(method, params)

                try:
                    with (
                        patch.object(
                            self.page,
                            "goto",
                            AsyncMock(
                                side_effect=Error("simulated navigation failure")
                            ),
                        ),
                        patch.object(self.cdp, "send", side_effect=fail_freeze),
                        patch.object(
                            self.browser,
                            "new_browser_cdp_session",
                            AsyncMock(
                                return_value=SimpleNamespace(
                                    send=AsyncMock(side_effect=fail_freeze),
                                    detach=AsyncMock(),
                                )
                            ),
                        ),
                        self.assertRaises(Error),
                    ):
                        await guard.close()
                    events = [
                        json.loads(line)
                        for line in (log.directory / "events.ndjson")
                        .read_text()
                        .splitlines()
                    ]
                    event = next(e for e in events if e["kind"] == "cleanup_freeze")
                    self.assertFalse(event["frozen"])
                    self.assertIn("simulated freeze failure", event["text"])
                    self.assertEqual(targets, [ARGS.target])
                    closed = next(
                        e for e in events if e["kind"] == "cleanup_emergency_close"
                    )
                    self.assertEqual(closed["closed"], close_success)
                    if not close_success:
                        self.assertIn("may still execute", closed["text"])
                finally:
                    await guard.close()
                    log.close()

    async def test_frozen_periodic_writer_stays_stopped_after_disconnect(self):
        log = walk.Log(Path(self.temp.name) / "periodic")
        guard = walk.Guard(self.page, self.cdp, self.base, log)
        await guard.install()
        await self.page.goto(self.base + "/pulse-page")
        await asyncio.sleep(0.15)
        self.assertGreater(log.guard_skips["write_method"], 0)
        with (
            patch.object(
                self.page,
                "goto",
                AsyncMock(side_effect=Error("simulated navigation failure")),
            ),
            self.assertRaises(Error),
        ):
            await guard.close()
        await self.cdp.detach()
        await self.pw.stop()
        await asyncio.sleep(0.3)
        after_disconnect = list(self.hits)
        self.pw = await async_playwright().start()
        self.browser = await self.pw.chromium.connect_over_cdp(ARGS.cdp)
        self.page, self.cdp = await walk.find_page(self.browser, ARGS.target)
        # Commit a safe document while frozen, then reactivate only that document.
        await self.page.goto("about:blank", wait_until="commit", timeout=2000)
        await self.cdp.send("Emulation.setScriptExecutionDisabled", {"value": False})
        await self.cdp.send("Page.setWebLifecycleState", {"state": "active"})
        self.assertEqual(await self.page.evaluate("location.href"), "about:blank")
        log.close()
        self.assertFalse(
            any(method == "POST" for method, _ in after_disconnect), after_disconnect
        )

    async def test_cleanup_waits_for_commit_not_load(self):
        log = walk.Log(Path(self.temp.name) / "commit")
        guard = walk.Guard(self.page, self.cdp, self.base, log)
        await guard.install()
        await self.page.goto(self.base + "/clean")
        goto = self.page.goto

        async def slow_load(url, **kwargs):
            if kwargs.get("wait_until") != "commit":
                raise Error("simulated blank load never settles")
            return await goto(url, **kwargs)

        try:
            with (
                patch.object(self.page, "goto", side_effect=slow_load),
                patch.object(
                    self.page,
                    "evaluate",
                    side_effect=RuntimeError("Blank execution context unavailable"),
                ),
            ):
                await guard.close()
            self.assertEqual(self.page.url, "about:blank")
            self.assertFalse(self.page.is_closed())
        finally:
            log.close()

    async def test_deadline_during_recovery_finishes_emergency_close(self):
        log = walk.Log(Path(self.temp.name) / "deadline")
        guard = walk.Guard(self.page, self.cdp, self.base, log)
        await guard.install()
        await self.page.goto(self.base + "/clean")
        send = self.cdp.send
        targets = []

        async def slow_freeze(method, params=None):
            if method == "Page.setWebLifecycleState":
                await asyncio.sleep(10)
            if method == "Target.closeTarget":
                await asyncio.sleep(0.02)
                targets.append(params["targetId"])
                return {"success": True}
            if method == "Target.getTargets":
                return {"targetInfos": []}
            return await send(method, params)

        try:
            with (
                patch.object(
                    self.page, "goto", AsyncMock(side_effect=Error("navigation failed"))
                ),
                patch.object(self.cdp, "send", side_effect=slow_freeze),
                patch.object(
                    self.browser,
                    "new_browser_cdp_session",
                    AsyncMock(
                        return_value=SimpleNamespace(
                            send=AsyncMock(side_effect=slow_freeze), detach=AsyncMock()
                        )
                    ),
                ),
                self.assertRaises(TimeoutError),
            ):
                async with asyncio.timeout(0.05):
                    await guard.close()
            self.assertEqual(targets, [ARGS.target])
            events = [
                json.loads(line)
                for line in (log.directory / "events.ndjson").read_text().splitlines()
            ]
            self.assertTrue(
                next(e for e in events if e["kind"] == "cleanup_emergency_close")[
                    "closed"
                ]
            )
        finally:
            await guard.close()
            log.close()

    async def test_deadline_while_emergency_close_pending_waits_before_disconnect(self):
        log = walk.Log(Path(self.temp.name) / "pending-close")
        guard = walk.Guard(self.page, self.cdp, self.base, log)
        await guard.install()
        await self.page.goto(self.base + "/clean")
        send = self.cdp.send
        order = []

        async def fail_recovery(method, params=None):
            if method == "Page.setWebLifecycleState":
                raise Error("recovery failed before deadline")
            return await send(method, params)

        async def slow_browser_close(method, params=None):
            if method == "Target.closeTarget":
                self.assertEqual(params["targetId"], ARGS.target)
                order.append("close_started")
                await asyncio.sleep(0.12)
                order.append("closed")
                return {"success": True}
            self.assertEqual(method, "Target.getTargets")
            order.append("verified")
            return {"targetInfos": []}

        async def detach():
            order.append("browser_session_detached")

        try:
            with (
                patch.object(
                    self.page, "goto", AsyncMock(side_effect=Error("navigation failed"))
                ),
                patch.object(self.cdp, "send", side_effect=fail_recovery),
                patch.object(
                    self.browser,
                    "new_browser_cdp_session",
                    AsyncMock(
                        return_value=SimpleNamespace(
                            send=slow_browser_close, detach=detach
                        )
                    ),
                ),
            ):
                with self.assertRaises(TimeoutError):
                    try:
                        async with asyncio.timeout(0.05):
                            await guard.close()
                    finally:
                        order.append("caller_disconnect")
                self.assertEqual(
                    order,
                    [
                        "close_started",
                        "closed",
                        "verified",
                        "browser_session_detached",
                        "caller_disconnect",
                    ],
                )
        finally:
            # Let the delayed fixture task settle even if an assertion fails.
            await asyncio.sleep(0.15)
            await guard.close()
            log.close()

    async def test_screenshot_timeout_is_candidate_and_walk_continues(self):
        opts = argparse.Namespace(
            url=self.base + "/clean",
            output=Path(self.temp.name) / "slow-shot",
            seed=17,
            steps=1,
            seconds=5,
            widths=[390],
            query="sample",
            settle_ms=20,
        )
        with patch.object(
            self.page,
            "screenshot",
            AsyncMock(side_effect=walk.PlaywrightTimeoutError("slow animation")),
        ):
            result = await walk.run(self.page, self.cdp, opts)
        self.assertEqual(result["actions"], 1)
        self.assertEqual(result["stop"], "step_budget")
        events = [
            json.loads(line)
            for line in (opts.output / "events.ndjson").read_text().splitlines()
        ]
        shots = [e for e in events if e["kind"] == "screenshot_timeout"]
        self.assertTrue(shots)
        self.assertTrue(all(e["classification"] == "candidate" for e in shots))

    async def test_missing_target_does_not_fall_back(self):
        with self.assertRaisesRegex(ValueError, "target"):
            await walk.find_page(self.browser, "missing-target")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cdp", required=True)
    parser.add_argument("--target", required=True)
    ARGS, rest = parser.parse_known_args()
    unittest.main(argv=[__file__, *rest])
