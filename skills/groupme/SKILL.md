---
name: groupme
description: Use when a task touches GroupMe in any way - searching or reading group chats or DMs for historical reference ("what did the group chat say about X", "find the message about the refund", "which chat was that in"), listing groups or DM threads, or anything mentioning GroupMe or api.groupme.com. Load BEFORE calling the GroupMe API.
---

# GroupMe - read and search chat history from the shell

GroupMe's official REST API (`https://api.groupme.com/v3`, the same one its
web app uses) serves full history for every group you are still in and every
DM thread, but it has no search endpoint, and neither does the web app.
`scripts/groupme` fills the gap: stdlib Python, GET requests only, NDJSON on
stdout, scan accounting on stderr.

## Setup

- **Token:** sign in at dev.groupme.com (email or phone plus password, then
  a one-time PIN by SMS), open the account menu > **Access token**, then
  **Show**. Accounts that sign in with Microsoft, Apple or Google need a
  GroupMe password first ("Forgot password"). The token has full account
  access, including sending; the script only reads.
- Pass it as `GROUPME_TOKEN` for the command. A private companion skill, if
  present, says where your setup keeps it.

## Commands

```bash
G="python3 ~/.claude/skills/groupme/scripts/groupme"
$G groups                                     # {id,name,former,messages,last}: groups you are in, then groups you left
$G chats                                      # DM threads; id is dm:<other_user_id>
$G search <conv> 'refund|reimburs'            # case-insensitive regex over message text, newest first
$G search <conv> '' --from 'sam'              # everything one sender wrote ('' matches all)
$G search all 'refund' --since 2024-01-01     # every group you are in; hits carry "group"
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

## Where it works and where it doesn't

| Need | Status |
|---|---|
| Groups you are in, full history | Works, back to the group's first message |
| DM threads | Works (20 per page, so long threads are slower) |
| Groups you left | `groups` lists them, but their messages answer HTTP 404. Rejoin in the app, or use GroupMe's data export |
| Big groups | Paging only: 1,000 requests per 100,000 messages, about 15 minutes. Bound it with `--since` |
| Search speed across everything | `search all` scans 6 groups at a time, but the biggest group sets the pace: 15 minutes for one 100,000-message group |
| Images, polls, events | Only image and file URLs and reply ids show in `attachments`; poll and event bodies are not searched |
| Topics (subgroups) | Not searched (`/groups/<id>/subgroups` lists them) |
| Sending, liking, reactions | Deliberately absent: posting is outward-facing |

GroupMe's own data export (Settings > Export Data) emails a zip of every
conversation as JSON. Use it for bulk analysis or for groups you left.

## Gotchas

- HTTP 429 backs off and retries three times, then exits.
- Group names change and repeat, so resolve them each time.
- Message ids are not strictly ordered by time; trust `at`, not id order.
