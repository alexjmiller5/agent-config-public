---
name: verdict
description: Use when an agent needs a person to decide or give feedback on something bigger than a one-line question - several decisions at once, a design, mockup or screenshots, data to approve or categorize, options with evidence - or when the user asks for a review page or review link. Also use before pasting a long numbered list of decisions into chat, and whenever a `verdict` review is open at the end of a session.
---

# Verdict: review pages for people

Verdict turns "please decide these N things" into a link. The agent writes an
HTML page, publishes it with the `verdict` CLI, sends the link, and reads the
answers back as JSON. The reviewer opens it on any device, picks answers,
pins notes to any element, presses Done. Any agent that can run a shell
command can use it; the CLI is the whole contract.

## When

| Use Verdict | Stay in chat |
|---|---|
| 3+ decisions in one go, each with evidence | one question, yes/no |
| a design, mockup, UI change, screenshots | a short text question |
| rows or groups to approve, categorize, prune | a status update |
| "which of these…" with options and a recommendation | something that needs an immediate answer mid-task |

The reviewer's time is the scarce resource: one page per batch, never one
page per question.

## Flow

```bash
verdict publish ./review/ --title "Finance: five decisions" --task <task id>   # prints the URL
verdict wait <id>            # blocks until Done; prints the state JSON (exit 3 after 8 h)
verdict show <id>            # read the state any time, e.g. when the user says "done" in chat
verdict close <id>           # after applying the answers; purged later by gc
verdict gc                   # end of session: purge, kill orphan waits, list stale reviews
```

1. Write the page (contract below) into a directory with `index.html` and
   any screenshots next to it. Relative `src` paths resolve to the review.
2. `verdict publish` once. The URL is stdout, `id: <id>` is stderr. Put the
   link in chat on its own line, plus on the task record's links if the
   workspace has one. Say what you need decided in one sentence; the page
   carries the detail. Published twice by mistake? `verdict close` the extra
   right away.
3. Wait. `verdict wait <id>` in the foreground when the review is the next
   step; otherwise continue other work and `verdict show <id>` when the user
   says they are done. Never leave a `wait` running in the background past
   the session: if you backgrounded one, kill it before you finish.
4. Read the answers (shape below), apply them, report what you applied.
5. `verdict close <id>`. A review you consumed and did not close shows up as
   stale for everyone until it is purged.
6. `verdict gc` before the final message of any session that touched a
   review. It kills orphan `verdict wait` processes on this machine, forgets
   dead waiters and lists stale reviews. A stale review you own is yours to
   finish or close; one you do not own is reported to the user, never
   closed.

`verdict publish` also warns on stderr when stale reviews exist. Read the
warning; do not suppress it.

## Page contract

| Markup | Meaning |
|---|---|
| `data-item="id"` | something to answer or annotate; `id` becomes the key in `answers` |
| `data-choices="a\|b\|c"` | pick one; `\|` is the only separator, any other text is fine; `data-default` names the recommendation (else the first) |
| `data-input="placeholder"` | free-text answer |
| `data-section="name"` | the element gets an "accept this section's recommendations" button acting on every `data-item` inside it |

Everything else is still annotatable: the reviewer can tap any element in
comment mode and type a note. Done fills unanswered choices with their
defaults, so always put the recommendation in `data-default`.

```html
<section class="card" data-section="prices">
  <h2>3. Investment price history</h2>
  <p>Alpha Vantage free returns only 100 daily closes per symbol. Tiingo gives full history on a free key.</p>
  <div data-item="prices"
       data-choices="free provider with full history, Alpha Vantage as fallback|Alpha Vantage paid ($49.99/mo)"
       data-default="free provider with full history, Alpha Vantage as fallback">Price source</div>
  <div data-item="prices-note" data-input="anything else?">Notes</div>
</section>
```

Keep the page plain: a short lead saying what the batch is, one numbered
section per decision with the evidence (numbers, a table, a screenshot), the
choices last. Mobile first (it will be read on a phone): no fixed widths, no
tiny text. Use the reviewer's words for the choices, not internal ids.
Images: `<img src="shot.png">` with the file in the same directory.

## Answers

```json
{"status": "done",
 "answers": {"prices": {"choice": "…", "defaulted": false}, "prices-note": {"text": "…"}},
 "comments": [{"item": "prices", "selector": "…", "snippet": "…", "text": "…", "at": "…"}],
 "general": "…"}
```

- `defaulted: true` = the reviewer accepted the recommendation without
  touching it. Still a decision; apply it.
- A comment's `item` is the enclosing `data-item` or null; `snippet` is the
  text of the element they tapped. Treat comments as instructions about that
  part of the page and acknowledge each one in your report.
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
| exit 5 `cannot reach the server` | `VERDICT_URL` unset or the server is down | ask the user in chat instead; report the outage |
| exit 3 from `wait` | 8 h without Done | `verdict show`; ask the user; leave the review open |
| exit 4 | the review was purged or the id is wrong | `verdict list --all` |
| stale warning on publish | old reviews nobody finished | finish or close yours; report the others |
