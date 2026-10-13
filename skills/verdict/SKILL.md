---
name: verdict
description: Use whenever an agent has something for a person to decide or read - any decision, or a report, findings, summary or final report longer than a few lines - and before pasting a long list, table or numbered decisions into chat. Also for designs, mockups, screenshots, data to approve or categorize, when the user asks for a review page or review link, and whenever a `verdict` review is open at the end of a session.
---

# Verdict: decisions and reports on a page

Verdict is the default channel from agent to person. The agent writes a page
(Markdown or HTML), publishes it with the `verdict` CLI, sends the link, and
reads the answers back as JSON. The reviewer opens it on any device, picks
answers, pins notes to any element, and presses Done (Got it on a page with
nothing to answer). Any agent that can run a shell command can use it; the
CLI is the whole contract.

## What goes on a page

| On a page | In chat |
|---|---|
| every decision you need from the person, with its evidence and your recommendation | the link, plus one sentence on what you need |
| any report longer than a few lines: findings, a summary, what you applied, the final report of a task | a one-line answer to a direct question |
| designs, mockups, screenshots, rows to approve or categorize | a short status line while you work |
| | one quick blocking question mid-task, through the harness's own question prompt when it has one |

The reviewer's time is the scarce resource: one page per batch, never one
page per question. Everything that follows on the same batch (a second round
of questions, a correction, what you applied, the final report) goes on the
same link with `verdict update`.

## Flow

```bash
verdict publish report.md --task <task id>   # prints the URL; also a directory, or - for stdin
verdict update <id> report.md                # same link, new page; answers and notes stay
verdict wait <id>            # blocks until Done; prints the state JSON (exit 3 after 8 h)
verdict show <id>            # read the state any time, e.g. when the user says "done" in chat
verdict close <id>           # after acting on it; purged later by gc
verdict gc                   # end of session: purge, kill orphan waits, list stale reviews
```

1. Write the page (contract below): a `.md` file, or a directory holding
   `index.md` (or `index.html`) with any screenshots next to it.
2. `verdict publish` once. The URL is stdout, `id: <id>` is stderr. Put the
   link in chat on its own line THE MOMENT publish returns, plus on the task
   record's links if the workspace has one. Say what you need in one
   sentence; the page carries the detail. Several pages in flight? Send each
   link as it publishes. Published twice by mistake? `verdict close` the
   extra right away.
3. Arm a wake-up right after publishing. A configured publish hook
   (`VERDICT_PUBLISH_HOOK`) may already have done it: publish then prints
   its output (e.g. `armed <id>: wakes pane ...`) on stderr, and you arm
   nothing more. Otherwise, where the environment has a waker that messages
   your session when a command returns (such as `agent-wake verdict <id>`),
   arm it and keep working: Done reaches you without polling, and the page
   tells the reviewer an agent is listening. Without one, `verdict wait <id>`
   in the foreground when the review is the next step; otherwise continue
   other work and `verdict show <id>` when the user says they are done.
   Never leave a `wait` running in the background past the session.
4. Read the answers (shape below) and act on them. Then put what you applied
   on the same page with `verdict update` (an "Applied" section at the top)
   and say it in one line in chat. `update` reopens a finished review and
   reruns the publish hook, so the wake-up is armed again; on a review that
   was still open the earlier wake-up is still waiting.
5. The final report of a task is a page too, usually the batch page updated
   one last time with what you applied. Its Done or Got it is a fresh one:
   the Done that answered the decisions does not cover a report the
   reviewer has not seen yet. Keep the session open until they press it;
   their notes are your next instructions. Act on them, update the page,
   and only then `verdict close` and end the session.
6. `verdict close <id>` once you have acted on everything on it. A review
   you consumed and did not close shows up as stale for everyone until it is
   purged.
7. `verdict gc` before the final message of any session that touched a
   review. It kills orphan `verdict wait` processes on this machine, forgets
   dead waiters and lists stale reviews. A stale review you own is yours to
   finish or close; one you do not own is reported to the user, never
   closed.

`verdict publish` also warns on stderr when stale reviews exist. Read the
warning; do not suppress it.

## Page contract

Write Markdown unless the layout needs HTML:

```markdown
# Finance: three decisions

Where these came from, in one sentence.

## 1. Investment price history

Alpha Vantage free returns only 100 daily closes per symbol. Tiingo gives full history on a free key.

| Provider | History | Cost |
|---|---|---|
| Tiingo | full | free |
| Alpha Vantage | 100 days | $49.99/mo for full |

<div data-item="prices" data-choices="Tiingo, Alpha Vantage as fallback|Alpha Vantage paid" data-default="Tiingo, Alpha Vantage as fallback">Price source</div>

<div data-item="prices-note" data-input="anything else?">Notes</div>
```

- The text before the first `##` is the lead; each `##` heading opens a card.
  A decision is one HTML line, with a blank line before and after it.
- Screenshots: `![what it shows](shot.png)` with the file next to `index.md`.
- HTML works too (`index.html`, or a single `.html` file). The server injects
  base styles for type, cards (`class="card"`), tables, images and both color
  schemes, so a page needs no `<style>`. If you add one, define colors as
  tokens with a dark-mode override: a light card under dark-mode text is
  unreadable on a phone at night.

| Markup | Meaning |
|---|---|
| `data-item="id"` | something to answer or annotate; `id` becomes the key in `answers` |
| `data-choices="a\|b\|c"` | pick one; `\|` is the only separator, any other text is fine; `data-default` names the recommendation (else the first) |
| `data-input="placeholder"` | free-text answer |
| `data-section="name"` | gets an "accept this section's recommendations" button for the choices inside it (every Markdown card is a section) |

A page with no choices or inputs is a report: the reviewer gets a Got it
button. Every element stays annotatable: in comment mode (Ctrl+Option+C) the
reviewer taps anything and types a note.

Keep the page plain: a lead saying what the batch is, one numbered section
per decision or topic with the evidence (numbers, a table, a screenshot), the
choices last, the recommendation in `data-default`. Mobile first: no fixed
widths, no tiny text. Use the reviewer's words for the choices, not internal
ids.

## Answers

```json
{"status": "done",
 "answers": {"prices": {"choice": "…", "defaulted": false}, "prices-note": {"text": "…"}},
 "comments": [{"item": "prices", "selector": "…", "snippet": "…", "text": "…", "at": "…"}],
 "general": "…"}
```

- Read `general` first: it can scope the rest ("only section A is done").
- An item missing from `answers` was not answered: Done sends only what the
  reviewer touched. Ask again on the same page (`verdict update`, next to
  what you applied), or file it as a follow-up with its details when the
  task can finish without it; never apply its recommendation on your own.
- `defaulted: true` = the reviewer took the recommendation with an accept
  button. That is a decision; apply it.
- A comment's `item` is the enclosing `data-item` or null; `snippet` is the
  text of the element they tapped. Treat comments as instructions about that
  part of the page; they override the choice on the same item. Acknowledge
  each one in the applied report.
- `status` `open` after `show` means not finished: do not apply partial
  answers unless the user says so.

## Cleanup rules

- Every review you publish ends in `verdict close`, in this session or a
  later one you resume. Record the review id with the task.
- `verdict wait` is foreground or killed; `gc` catches the rest, run it.
- The server stores the page and answers as files; nothing else is created.
  Do not keep copies of the answers in scratch files past the session.

## Failures

| Symptom | Meaning | Do |
|---|---|---|
| exit 5 `cannot reach the server` | `VERDICT_URL` unset or the server is down | first check whether the shell simply lacks `VERDICT_URL` (a session started before the variable was declared): read the server's public URL from the machine configuration and pass it explicitly (`VERDICT_URL=<url> verdict ...`); only when the server itself is unreachable tell the user in chat and report the outage |
| exit 1 `the server refused it` | bad input, e.g. a file name with a space | fix what the message names and publish again |
| exit 3 from `wait` | 8 h without Done | `verdict show`; ask the user; leave the review open |
| exit 4 | the review was purged or the id is wrong | `verdict list --all` |
| stale warning on publish | old reviews nobody finished | finish or close yours; report the others |
