"""Offline tests for the groupme script: python3 -m unittest test_groupme (from this directory)."""

import importlib.machinery
import importlib.util
import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

LOADER = importlib.machinery.SourceFileLoader("groupme", str(Path(__file__).with_name("groupme")))
SPEC = importlib.util.spec_from_loader("groupme", LOADER)
gm = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(gm)


def msg(i, text, name="Sam", ts=None):
    return {
        "id": str(i),
        "created_at": ts if ts is not None else 1_700_000_000 + i,
        "name": name,
        "text": text,
        "attachments": [],
        "favorited_by": [],
    }


class FakeAPI:
    """Serves newest-first pages like GroupMe; None (HTTP 304) once history is exhausted."""

    def __init__(self, messages, key="messages", page=2):
        self.messages = sorted(messages, key=lambda m: int(m["id"]), reverse=True)
        self.key, self.page, self.calls = key, page, []

    def __call__(self, path, params):
        self.calls.append((path, dict(params)))
        rows = self.messages
        if params.get("before_id"):
            rows = [m for m in rows if int(m["id"]) < int(params["before_id"])]
        if params.get("after_id"):
            rows = sorted((m for m in rows if int(m["id"]) > int(params["after_id"])), key=lambda m: int(m["id"]))
        rows = rows[: min(self.page, int(params.get("limit", 20)))]
        return {"count": len(self.messages), self.key: rows} if rows else None


def run(argv, api):
    out = io.StringIO()
    with patch.object(gm, "get", api), redirect_stdout(out):
        gm.main(argv)
    return [json.loads(line) for line in out.getvalue().splitlines()]


class SearchTests(unittest.TestCase):
    def test_pages_back_through_all_history_case_insensitive(self):
        api = FakeAPI([msg(1, "Refund for dues"), msg(2, "hi"), msg(3, "no REFUND yet"), msg(4, "ok"), msg(5, "x")])
        hits = run(["search", "123", "refund"], api)
        self.assertEqual([h["id"] for h in hits], ["3", "1"])
        self.assertEqual(api.calls[0][0], "/groups/123/messages")
        self.assertEqual([c[1].get("before_id") for c in api.calls], [None, "4", "2", "1"])

    def test_since_stops_paging(self):
        api = FakeAPI([msg(i, "refund") for i in range(1, 9)])
        since = gm.iso(1_700_000_000 + 6)[:19]
        hits = run(["search", "123", "refund", "--since", since], api)
        self.assertEqual([h["id"] for h in hits], ["8", "7", "6"])
        self.assertLessEqual(len(api.calls), 2)

    def test_dm_uses_direct_messages(self):
        api = FakeAPI([msg(1, "refund?"), msg(2, "nope")], key="direct_messages")
        hits = run(["search", "dm:42", "refund"], api)
        self.assertEqual([h["id"] for h in hits], ["1"])
        self.assertEqual(api.calls[0], ("/direct_messages", {"other_user_id": "42"}))

    def test_message_shape(self):
        m = msg(7, "see pic", name="Alex", ts=0)
        m["attachments"] = [{"type": "image", "url": "https://i.groupme.com/x"}]
        m["favorited_by"] = ["1", "2"]
        (hit,) = run(["search", "1", "pic"], FakeAPI([m]))
        self.assertEqual(
            hit,
            {
                "id": "7",
                "at": "1970-01-01T00:00:00Z",
                "name": "Alex",
                "text": "see pic",
                "likes": 2,
                "attachments": ["image https://i.groupme.com/x"],
            },
        )


class HistoryTests(unittest.TestCase):
    def test_before_and_after_windows(self):
        api = FakeAPI([msg(i, f"m{i}") for i in range(1, 11)], page=2)
        self.assertEqual(
            [h["id"] for h in run(["history", "9", "--before-id", "6", "--limit", "3"], api)], ["5", "4", "3"]
        )
        self.assertEqual(
            [h["id"] for h in run(["history", "9", "--after-id", "6", "--limit", "3"], api)], ["7", "8", "9"]
        )

    def test_latest_by_default(self):
        api = FakeAPI([msg(i, f"m{i}") for i in range(1, 6)], page=100)
        self.assertEqual([h["id"] for h in run(["history", "9", "--limit", "2"], api)], ["5", "4"])


class ListTests(unittest.TestCase):
    def test_groups_include_former(self):
        pages = {
            "/groups": [[{"id": "1", "name": "EC", "messages": {"count": 9, "last_message_created_at": 0}}], []],
            "/groups/former": [[{"id": "2", "name": "Old", "messages": {"count": 3, "last_message_created_at": 0}}]],
        }

        def api(path, params):
            rows = pages[path]
            p = int(params.get("page", 1)) - 1
            return rows[p] if p < len(rows) else []

        rows = run(["groups"], api)
        self.assertEqual(
            [(r["id"], r["name"], r["former"], r["messages"]) for r in rows],
            [("1", "EC", False, 9), ("2", "Old", True, 3)],
        )


class Router:
    """Routes /groups listings and per-group message paths to fakes; a group id mapped to an int raises that HTTP code."""

    def __init__(self, groups, messages):
        self.groups, self.messages, self.calls = groups, messages, []

    def __call__(self, path, params):
        self.calls.append(path)
        if path == "/groups":
            return self.groups if int(params.get("page", 1)) == 1 else []
        if path == "/groups/former":
            return []
        gid = path.split("/")[2]
        api = self.messages[gid]
        if isinstance(api, int):
            raise gm.ApiError(api, path, "")
        return api(path, params)


def group(i, name):
    return {"id": i, "name": name, "messages": {"count": 1, "last_message_created_at": 0}}


class FilterAndScopeTests(unittest.TestCase):
    def test_sender_filter_with_empty_pattern(self):
        api = FakeAPI([msg(1, "a", name="Pat Lee"), msg(2, "b", name="Sam"), msg(3, "c", name="pat q")])
        self.assertEqual([h["id"] for h in run(["search", "1", "", "--from", "ALEX"], api)], ["3", "1"])

    def test_group_resolved_by_name(self):
        r = Router([group("7", "Board Room 2023"), group("8", "Planning")], {"7": FakeAPI([msg(1, "refund")])})
        self.assertEqual([h["id"] for h in run(["search", "BOARD ROOM", "refund"], r)], ["1"])
        self.assertIn("/groups/7/messages", r.calls)

    def test_ambiguous_name_exits(self):
        r = Router([group("7", "EC Fall"), group("8", "EC Spring")], {})
        with self.assertRaises(SystemExit):
            run(["search", "ec", "x"], r)

    def test_search_all_tags_group_and_survives_errors(self):
        r = Router(
            [group("7", "One"), group("8", "Gone"), group("9", "Two")],
            {"7": FakeAPI([msg(1, "refund"), msg(2, "no")]), "8": 404, "9": FakeAPI([msg(5, "Refund!")])},
        )
        hits = run(["search", "all", "refund"], r)
        self.assertEqual(sorted((h["group"], h["id"]) for h in hits), [("One", "1"), ("Two", "5")])

    def test_left_group_404_explains(self):
        self.assertIn("left", str(gm.ApiError(404, "/groups/1/messages", "")))


if __name__ == "__main__":
    unittest.main()
