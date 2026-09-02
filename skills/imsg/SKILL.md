---
name: imsg
description: Use when a task touches iMessages or SMS on the user's Macs - reading or searching message history, listing chats, checking unread messages, watching for incoming messages, sending a text or attachment to someone, or anything mentioning imsg, Messages.app, chat.db, or "text <person>". Load BEFORE running any imsg command or reading the Messages database.
---

# imsg - iMessage/SMS from the shell

`imsg` reads `~/Library/Messages/chat.db` directly (reads are local and safe)
and sends through Messages.app automation. Every read command takes `--json`
and emits **NDJSON** (one object per line) - pipe to `jq -s` for an array;
stdout is JSON-only, progress/warnings go to stderr.

Full flag reference: `imsg completions llm`. The official docs (imsg.sh) are
mirrored in [references/](references/) - consult them before guessing flags.

## Setup

- Install: `brew install steipete/tap/imsg` (on declaratively managed
  machines, declare it in your config instead of installing ad-hoc).
  Only useful on a Mac signed into Messages.app.
- Reads need Full Disk Access on the invoking context (the terminal app).
  Verify: `sqlite3 ~/Library/Messages/chat.db 'pragma quick_check;'` - failure
  means no FDA, see [references/permissions.md](references/permissions.md).
- First `imsg send` triggers an Automation → Messages TCC prompt that THE USER
  must click. If a send
  hangs or errors on permissions, stop and tell them.
- **Bridge tier is reachable but off by default.** It requires SIP in a
  custom configuration (Filesystem Protections and Debugging Restrictions
  disabled), which `imsg status` reports as `"sip":"disabled"`, plus the
  helper dylib installed. Bridge/private-API commands
  (`send-rich`, `tapback`, `edit`, `unsend`, `poll`, `chat-*`,
  `send-attachment`, ...) still need Messages.app injected: `imsg launch`
  does that, and until it runs `advanced_features` is `false` and those
  commands fail. macOS 26/Tahoe can additionally block injection via library
  validation, so treat bridge tier as best-effort - check
  `imsg status --json` rather than assuming. Never silently downgrade a
  bridge-only request (threaded reply, effect, tapback by GUID, group
  management) to a plain send; if injection is unavailable, say so.
- `imsg status --json` reports feature availability when unsure.

## SEND GUARD - read before any visible action

A send is outward-facing and irreversible. "Visible actions" = `send`,
`react`, `name-photo share`, and anything else another person can see.

Both conditions must hold before a visible action:

1. **the user explicitly asked for it this session.** A read/summarize/watch task
   never escalates into sending. No "helpful" replies, auto-replies, or
   follow-ups.
2. **The exact payload is confirmed.** Before sending, echo to the user:
   recipient display name + handle (participants list for a group), service
   (iMessage/SMS), and the verbatim text / attachment path - then wait for a
   yes. Skip the echo only when their request already contained BOTH the exact
   recipient (handle, or unique unambiguous contact) AND the exact text.

Resolution rules:

- Casual name with more than one plausible chat/handle match → show the
  candidates, never pick one. A `contains` match on "Mom" is not an identity.
- Composing or paraphrasing the message yourself counts as new content -
  confirm the wording even when the recipient is unambiguous.
- No existing chat with the handle → always confirm before creating one.
- Headless contexts (cron, launchd, hooks - nobody to ask): send only what
  the job's own spec pins down verbatim, recipient and text. Otherwise
  queue/report instead of sending.
- Batches: confirm the full recipient+message list once, before the first
  send. Never loop sends of improvised content.

Red flags - STOP, confirm first: "they probably mean this chat",
"close enough to what they said", "it's just a quick reply", "I'll send now
and tell them after", "the previous send was approved so this one is too".

## Reading (no guard)

```bash
imsg chats --limit 200 --json | jq -s          # list conversations
imsg chats --unread-only --json | jq -s
imsg group --chat-id 42 --json                  # identity + participants
imsg history --chat-id 42 --limit 50 --json | jq -s
imsg history --chat-id 42 --start 2026-08-01T00:00:00Z --end 2026-09-01T00:00:00Z --json
imsg search --query "dinner" --match contains --json | jq -s
imsg stats --chat-id 42 --media --json
imsg watch --chat-id 42 --since-rowid N --json  # stream; message id = cursor
```

- Resolve a person from `chats` (its `contact_name` uses Contacts), NOT from
  `search` - search hits message bodies only, and raw handles carry no names.
  **Zero search hits is not proof a contact doesn't exist.**
- `id` (chat.db rowid) is the stable per-machine handle - prefer `--chat-id`
  everywhere; `guid`/`identifier` are the portable forms.
- `--start` inclusive, `--end` exclusive, ISO8601.
- `--attachments` adds metadata; `--convert-attachments` converts CAF→M4A /
  GIF→PNG for model consumption.
- `watch --since-rowid` is exclusive; without it, watch starts at newest.

## Sending (guard applies)

```bash
imsg send --chat-id 42 --text "message"             # prefer: no address ambiguity
imsg send --to "+15551234567" --text "message" --service auto
imsg send --to "+15551234567" --file /absolute/path.jpg
```

- `--service auto` (default) prefers iMessage, falls back to SMS for phone
  numbers; `--no-sms-fallback` disables. SMS relay requires Text Message
  Forwarding enabled on the user's iPhone.
- E.164 phone numbers (`+1...`).
- Verify an attachment path exists before sending it.
- `react` targets only the most recent incoming message in a chat AND needs
  an Accessibility grant nobody has given - treat reactions as unavailable.

## Gotchas

- No output from a read? You're probably missing `jq -s` around NDJSON, or
  the shell lacks FDA (run the quick_check above).
- Raw `sqlite3` against chat.db is a last resort (imsg already decodes the
  `attributedBody` blobs that hide ~93% of modern message text). If forced:
  timestamps are ns since 2001-01-01 -
  `datetime(date/1000000000 + 978307200, 'unixepoch', 'localtime')` - filter
  tapback rows with `associated_message_type = 0`, and quote `!=` for zsh.
- `imsg rpc` (JSON-RPC over stdio) is for long-running daemons, not one-shot
  tasks.

## References

Mirrored from the imsg docs (imsg.sh):
[permissions](references/permissions.md), [chats](references/chats.md),
[history](references/history.md), [watch](references/watch.md),
[send](references/send.md), [groups](references/groups.md),
[attachments](references/attachments.md), [json](references/json.md),
[stats](references/stats.md), [troubleshooting](references/troubleshooting.md),
[bridge](references/bridge.md), [advanced-imcore](references/advanced-imcore.md).
