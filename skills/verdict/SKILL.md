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

The reviewer's time is the scarce resource: one page per decision batch or
round, never one page per question. A new round gets a new page: follow-up
questions, new evidence, what you applied and a substantive final report go
through `verdict publish` with only the new material. Keep a short link back
when context matters. Do not make the person scroll past an earlier round or
replace content they have already seen.

Use `verdict update` only when the user explicitly asks to edit that existing
page. Preserve its answers and notes; an explicit edit is not permission to
append later rounds to it.

## Flow

```bash
verdict publish report.md --task <task id>   # prints the URL; also a directory, or - for stdin
verdict publish follow-up.md --task <task id> # a fresh page for the next round
verdict wait <id>            # blocks until Done; prints the state JSON (exit 3 after 8 h)
verdict show <id>            # read the state any time, e.g. when the user says "done" in chat
verdict close <id>           # after acting on it; purged later by gc
verdict gc                   # end of session: purge, kill orphan waits, list stale reviews
```

1. Write the page (contract below): a `.md` file, or a directory holding
   `index.md` (or `index.html`) with any screenshots next to it.
2. `verdict publish` once for this round. The URL is stdout, `id: <id>` is stderr. Put the
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
4. Read the answers (shape below) and act on them. Close the consumed review
   after everything on it is resolved. If there is substantive new material
   to show, publish a fresh, focused page for that next round, with the task
   link appended to its existing links. Leave the earlier page intact.
5. A substantive final report is a fresh page too: show what changed and its
   verification without copying the old questions. Its Done or Got it covers
   only that new report. Keep the session open while a requested decision or
   review remains. Do not create another page merely to acknowledge an
   unchanged report, and do not send repeated unchanged completion reports.
6. `verdict gc` before the final message of any session that touched a
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

<div data-item="prices-note" data-input="anything else?" data-optional>Optional notes</div>
```

- The text before the first `##` is the lead; each `##` heading opens a card.
  A decision is one HTML line, with a blank line before and after it.
- Screenshots: `![what it shows](shot.png)` with the file next to `index.md`.
- Inside HTML blocks such as `<details>`, use HTML for the contents too:
  `<details><summary>Earlier version</summary><img src="earlier.png" alt="Earlier version"></details>`.
  Markdown image syntax inside these blocks renders as literal text. After
  publishing, expand every image dropdown in the browser and verify its images
  load (`img.complete && img.naturalWidth > 0`).
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
| `data-optional` | an optional answer; saved normally but excluded from required progress and unanswered warnings |
| `data-section="name"` | gets an "accept this section's recommendations" button for the choices inside it (every Markdown card is a section) |

A page with no choices or inputs is a report: the reviewer gets a Got it
button. A page with optional inputs still has Done, without requiring those
inputs to be filled. Mark supplemental notes, corrections and additional
instructions with `data-optional`; do not turn them into required questions.
Every element stays annotatable: in comment mode (Ctrl+Option+C) the
reviewer taps anything and types a note.

Let the client supply review controls and its responsive pane; do not build a
second Done interface.

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
- Done sends only what the reviewer touched. A nonblank item-linked comment
  can answer a question without an entry in `answers`; read those comments
  before declaring it unanswered. Blank optional fields need no follow-up.
  If a required item is still unanswered, ask on a fresh follow-up page, or
  record its details for later when the task can finish without it. Never
  apply an untouched recommendation on your own.
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
