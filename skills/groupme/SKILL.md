---
name: groupme
description: Use when a task touches GroupMe in any way - searching or reading group chats or DMs for historical reference ("what did the group chat say about X", "find the message about the refund"), listing groups or DM threads, or anything mentioning GroupMe or api.groupme.com. Load BEFORE calling the GroupMe API.
---

# GroupMe - read and search chat history from the shell

GroupMe has a REST API (`https://api.groupme.com/v3`) but no search endpoint
and no maintained CLI. `scripts/groupme` fills the gap: stdlib Python, GET
requests only, NDJSON on stdout, scan accounting on stderr.

## Setup

- **Token:** sign in at dev.groupme.com, then click **Access Token** (top
  right). Accounts that sign in with Microsoft, Apple or Facebook must first
  set a GroupMe password ("Forgot password") before the developer site accepts
  the login. The token has full account access, including sending; the script
  only reads.
- Pass it as `GROUPME_TOKEN` for the command. A private companion skill, if
  present, says where your setup keeps it.

## Commands

```bash
G="python3 ~/.claude/skills/groupme/scripts/groupme"
$G groups                                    # {id,name,former,messages,last}: active groups, then groups you left
$G chats                                     # DM threads; id is dm:<other_user_id>
$G search <id> 'refund|reimburs' [--since 2024-01-01]   # case-insensitive regex over message text, newest first
$G history <id> --before-id <msg> --limit 20 # context older than a hit (newest first)
$G history <id> --after-id <msg> --limit 20  # context newer than a hit (oldest first, groups only)
$G history <id> --limit 50                   # latest messages
```

A message row is `{id, at (UTC), name, text, likes, attachments}`. Pipe to
`jq` for sender filters (`select(.name|test("Sam"))`).

## Working method

1. Resolve the conversation by name from `groups` / `chats`. Never guess an id.
2. `search` with a broad regex (stems and synonyms: `refund|reimburs|venmo`).
   The stderr line says how far back it scanned; zero hits over the full
   history is a real negative, zero hits under `--since` is not.
3. Read around each hit with `history --before-id` / `--after-id` before
   answering. A single message rarely carries the whole story.

## Gotchas

- Search pages the entire conversation: 100 messages per request in groups,
  20 in DMs. A 20,000-message group takes about 200 requests. Bound it with
  `--since` when the era is known.
- Only message text is searched. Photo-only messages have empty text, and
  poll and event bodies are not covered.
- HTTP 429 backs off and retries three times, then exits.
- Nothing here posts. Sending to a group is outward-facing and not part of
  this skill.
- For bulk analysis of every chat at once, GroupMe's own data export
  (Settings > Export Data) emails a zip of all conversations as JSON.
