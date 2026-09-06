---
name: whatsapp
description: Use when a task touches WhatsApp in any way on the user's Mac - reading, searching, or summarizing WhatsApp chats or groups, answering "what did X say on WhatsApp", checking unread WhatsApp messages, listing group members, finding media someone sent, or sending a WhatsApp message to someone - or anything mentioning WhatsApp, "wa", ChatStorage.sqlite, wacli, or a group chat that lives on WhatsApp. Load BEFORE opening the WhatsApp database or automating WhatsApp.app; the live database is WAL-backed and reading it directly misses recent messages.
---

# WhatsApp - read and send from the shell (macOS)

Two paths, both riding the **logged-in WhatsApp desktop app** - no linked
device, no unofficial client, nothing for Meta to ban:

- **Read** = SQL over a snapshot of the app's local store
  (`~/Library/Group Containers/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite`,
  plain Core Data SQLite, full history the Mac has synced).
- **Send** = the app's own `whatsapp://send` deep link (prefills the
  composer) + an Accessibility click on its Send button, then a store check.

Both live in [scripts/](scripts/): `wa-db` and `wa-send` (with the skill
symlinked into `~/.claude/skills/`, that is `~/.claude/skills/whatsapp/scripts/`;
call them by path or put the directory on `PATH`). Only useful on a Mac where
WhatsApp.app is installed and logged in (linked to the phone).

## Setup

- Reads: nothing beyond the app being logged in. `wa-db "select 1"` failing
  with "Operation not permitted" means the shell lacks access to
  `~/Library/Group Containers` - grant Full Disk Access to the terminal/agent
  host app, then relaunch it.
- Sends: the app running the script (terminal, IDE, agent host) needs
  **Accessibility** (System Settings → Privacy & Security → Accessibility).
  Without it `wa-send` reports the composer/Send button as not found.
- `wa-send` brings WhatsApp to the front for ~2 s and restores the previous
  app. Don't run it while the user is typing.

## SEND GUARD - read before any visible action

A send is outward-facing and irreversible. Both conditions must hold:

1. **The user explicitly asked for a send this session.** A read, summarize,
   or "check my WhatsApp" task never escalates into sending - no helpful
   replies, auto-replies, or follow-ups.
2. **The exact payload is confirmed.** Before sending, echo recipient name +
   number and the verbatim text, then wait for a yes. Skip the echo only
   when the request already contained BOTH the exact recipient (number, or a
   unique unambiguous chat) AND the exact text.

Resolution rules: a casual name matching more than one chat → show the
candidates, never pick one. Composing or paraphrasing the message yourself
counts as new content - confirm the wording. Headless contexts (cron, hooks)
send only what the job's spec pins down verbatim; otherwise report instead.
Batches: confirm the full list once, before the first send; never loop
sends of improvised content.

## Reading

`wa-db "<sql>"` snapshots the store (with its WAL, so the newest messages are
included), defines three views, and prints JSON. Any sqlite3 output flag goes
before the SQL (`wa-db -table "..."`); no SQL = interactive shell.

| view | columns |
|---|---|
| `chats` | `chat_pk, jid, phone_jid, name, kind (dm/group/broadcast/status/community), unread, archived, last_ts, last_text` |
| `messages` | `msg_pk, chat_pk, chat, chat_jid, from_me, sender, sender_jid, ts, type, kind, text, media_title, media_path, starred, status` - `sender` is the literal `me` for your own messages |
| `members` | `chat_pk, chat, jid, name, admin, active` (group rosters; `active=1` = current member, `0` = left or removed) |

```bash
wa-db "select name, kind, unread, last_ts from chats where archived=0 and kind in ('dm','group') order by last_ts desc limit 20"
wa-db "select chat_pk, name, kind from chats where name like '%dinner%'"        # resolve a chat
wa-db "select sender, ts, kind, text from messages where chat_pk=42 order by ts desc limit 50"
wa-db "select chat, sender, ts, text from messages where text like '%passport%' order by ts desc limit 30"
wa-db "select name, unread from chats where unread>0 and archived=0 and kind in ('dm','group')"
wa-db "select count(*) from members where chat_pk=42 and active=1"
wa-db "select ts, media_path from messages where chat_pk=42 and kind in ('image','document') order by ts desc"
```

- **Filter `kind in ('dm','group')` for anything "recent" or "unread"** -
  `status` rows are status broadcasts (their `unread` is unseen posts, not
  messages) and `broadcast`/`community` rows are containers, not chats.
- **The "Message Yourself" chat is a `dm` named after the user.** A naive
  "most recent 1:1 chat" picks it; when the user means a conversation with
  someone else, exclude it (`chats.phone_jid` = the user's own number).
- `ts` is local time. Underlying timestamps are seconds since 2001-01-01
  (`datetime(Z... + 978307200, 'unixepoch', 'localtime')`) if you query the
  raw `ZWA*` tables.
- **Resolve people from `chats`, not from message hits** - zero search hits
  is not proof a contact doesn't exist. `sender` in groups is the member's
  saved contact name, else their WhatsApp push name.
- `kind='system'` rows are joins/leaves/subject changes; `deleted` rows have
  no text. Unknown media types show as `type-N`.
- `media_path` is relative to `~/Library/Group Containers/group.net.whatsapp.WhatsApp.shared/Message/`;
  only media the Mac has downloaded is present.
- Two JID forms exist for the same person: `<phone>@s.whatsapp.net` and
  `<id>@lid`. `chats.phone_jid` always gives the phone form - that is what
  `wa-send --to` needs (digits before the `@`).
- Voice notes are `kind='audio'` with `media_path` `.opus` files; there is
  no transcript in the store.

## Sending (guard applies)

```bash
wa-send --to +15551234567 --text "message"            # 1:1 chat, E.164 number
wa-send --to +15551234567 --text "message" --dry-run  # opens + verifies composer, sends nothing
```

Prints the stored row as JSON on success (`sent:true`); non-zero exit with a
reason otherwise. Get the number from `chats.phone_jid` for an existing chat;
a number with no existing chat still works (WhatsApp creates the chat) - but
confirm with the user first.

- **Refuses to send when the composer holds anything but the requested
  text** - a stale draft in that chat blocks it; the user clears it in the
  app.
- **Groups are not sendable by `wa-send`** (no deep link opens a group, and
  the app's Accessibility tree is not stable enough to navigate the chat
  list). Say so; if the user needs agent-sent group messages, the fallback
  is `wacli` (openclaw/wacli - pairs as a separate linked device via
  WhatsApp Web protocol; carries the unofficial-client ban risk the
  desktop-app path avoids).
- No attachments, reactions, or replies-to - text only.

## Gotchas

- Reading the live `ChatStorage.sqlite` directly silently omits everything
  still in the WAL, and opening it read-write can corrupt the app's state.
  `wa-db` exists so nobody has to remember that; don't bypass it.
- `wa-send` timing out with "composer/send button not found" while the app
  is clearly open = Accessibility not granted to the process actually
  running the script (the parent app, not the shell).
- The desktop app only holds what it has synced from the phone; very old
  chats may be partial. The phone is the source of truth.
