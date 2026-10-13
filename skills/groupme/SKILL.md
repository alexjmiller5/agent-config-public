---
name: groupme
description: Use when a task touches GroupMe in any way - searching or reading group chats or DMs for historical reference ("what did the group chat say about X", "find the message about the refund", "which chat was that in"), listing groups or DM threads, or anything mentioning GroupMe or api.groupme.com. Load BEFORE calling the GroupMe API.
---

# GroupMe - read and search chat history from the shell

GroupMe's official REST API (`https://api.groupme.com/v3`, the same one its
web app uses) serves full history for every group you are still in and every
DM thread, but it has no search endpoint, and neither does the web app.
`scripts/groupme` fills the gap: stdlib Python, GET requests only, NDJSON on
stdout, scan accounting on stderr. Searches run against a local archive
(below), so only the first search of a conversation is slow.

## Setup

- **Token:** sign in at dev.groupme.com (email or phone plus password, then
  a one-time PIN by SMS), open the account menu > **Access token**, then
  **Show**. Accounts that sign in with Microsoft, Apple or Google need a
  GroupMe password first ("Forgot password"). The token has full account
  access, including sending; the script only reads.
- Pass it as `GROUPME_TOKEN` for the command. A private companion skill, if
  present, says where your setup keeps it.
- **First run on a machine: build the archive.** `$G sync all` pages every
  group you are in into the archive. A 300,000-message account across 40
  groups took about 30 minutes and 225 MB. Run it in the background (or as a launchd one-shot
  where shells die after a few hours), and check whether it is finished
  before you promise fast searches. It resumes where it stopped, so rerun it
  after an interruption. After that, each search fetches only the newest
  pages (well under a second) before querying locally.

## Commands

```bash
G="python3 ~/.claude/skills/groupme/scripts/groupme"
$G groups                                     # {id,name,former,messages,last}: groups you are in, then groups you left
$G chats                                      # DM threads; id is dm:<other_user_id>
$G search <conv> 'refund|reimburs'            # case-insensitive regex over message text, newest first
$G search <conv> '' --from 'sam'              # everything one sender wrote ('' matches all)
$G search all 'refund' --since 2024-01-01     # every group you are in; hits carry "group"
$G sync all                                   # build or top up the archive for every group (sync <conv> for one)
$G history <conv> --before-id <msg> --limit 20   # context older than a hit (newest first)
$G history <conv> --after-id <msg> --limit 20    # context newer than a hit (oldest first, groups only)
```

`<conv>` is a group id, `dm:<user id>`, or a piece of a group's name that
matches exactly one group you are in (`'book club'`); an ambiguous
name exits listing the candidates. A message row is
`{id, at (UTC), name, text, likes, attachments}`.

## Working method

1. Name the conversation, or run `search all` when you don't know which
   chat it was in.
2. Search with a broad regex (stems and synonyms: `refund|reimburs|venmo`).
   People rarely use the word you expect, so pair a topic with a person
   (`--from`) or a money word. The stderr line says how far back each scan
   went; zero hits over the full history is a real negative, zero hits under
   `--since` is not.
3. Read around each hit with `history --before-id` / `--after-id` before
   answering. A single message rarely carries the whole story.

## The archive

`search` and `sync` keep a SQLite cache at `GROUPME_ARCHIVE` (default
`${XDG_CACHE_HOME:-~/.cache}/groupme/archive.sqlite`, owner-only): the raw
message JSON per conversation plus a backfill cursor. It is a cache, not a
record: delete it and the next search rebuilds it. Every search re-reads the
newest pages until one is fully archived, so new messages and changed likes
show up, but an edit deep in history only appears after a rebuild.
`history` always reads live.

## Where it works and where it doesn't

| Need | Status |
|---|---|
| Groups you are in, full history | Works, back to the group's first message |
| DM threads | Works (20 per page, so long threads are slower) |
| Groups you left | `groups` lists them, but their messages answer HTTP 404. Rejoin in the app, or use GroupMe's data export |
| Big groups | The first search or sync pages the whole history: 1,000 requests and about 15 minutes per 100,000 messages. After that, searches take under a second |
| Search across everything | `search all` over 300,000 archived messages takes about 8 seconds, mostly the per-group refresh |
| Images, polls, events | Only image and file URLs and reply ids show in `attachments`; poll and event bodies are not searched |
| Topics (subgroups) | Not searched (`/groups/<id>/subgroups` lists them) |
| Sending, liking, reactions | Deliberately absent: posting is outward-facing |

GroupMe's own data export (Settings > Export Data) emails a zip of every
conversation as JSON. Use it for bulk analysis or for groups you left.

## Gotchas

- HTTP 429 backs off and retries three times, then exits.
- Group names change and repeat, so resolve them each time.
- Message ids are not strictly ordered by time; trust `at`, not id order.
