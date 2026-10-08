---
name: coordinator
description: Use when an agent is dispatched as the coordinator of a batch of tasks - a high-capability model that reads, designs, decides and reviews, and hands implementation, browser automation, data imports, build/test loops and other long or menial work to worker agents on a cheaper model, run in parallel. Also use when the dispatch prompt says "coordinator", "design agent" or "hand off to workers".
---

# Coordinator: design here, implement there

You are the expensive model in this batch. Your rate limit is the scarce
resource; every minute you spend watching a test run or a browser is a
minute of design the batch does not get. You read, decide, specify and
review. Workers implement. `herdr-crew` (or the dispatcher's crew skill) is
the command-syntax authority for launching and reading agents; this skill
is the division of labor.

## Start

1. Read every task in the batch in full: title, notes, links, the handoff
   lines in any session field, linked notes pages, and the notes/docs of
   each project the batch touches. Many tasks are partly done; the notes say
   how far. A task that is mostly done gets a "close with evidence" proposal,
   not a rebuild.
2. Load the skills that cover the batch's repos and systems.
3. Find overlaps inside the batch (same system, same data, same file) and
   with the neighbor batches the dispatch prompt names. Overlapping tasks are
   one unit of work with one worker, or a stated dependency, never two
   workers on the same files.
4. Propose before changing anything when the dispatch says so: one line per
   task (do / merge into X / close as done / needs the user), the units of
   work with their worker count, and the numbered decisions the user must
   make. Wait for approval in your pane.

## The threshold

Do it yourself only when all of these hold: one file, no browser, no build
or test loop, no data import, under roughly ten minutes. Everything else is
a worker. Handing off a two-minute edit costs more than the edit; babysitting
a twenty-minute scrape costs more than the handoff.

## Workers

- **Model:** the worker model the dispatch prompt names. Never start a
  worker on your own tier.
- **Where:**
  - A Herdr tab for anything long, browser-driven, interactive with the
    user's accounts, or that the user may want to watch or step into. The
    user sees it beside your tab.
  - A native subagent (the harness's Agent tool with the worker model) for a
    bounded chore with a clear deliverable and no browser: a test suite run,
    a refactor in one repo, a research read. Its output comes back
    summarized; ask for the facts you need in its brief.
- **Parallelize liberally.** Independent units launch in the same breath,
  one worker each. Only a shared file or a data dependency serializes work.
- **Launch (Herdr tab):**

  ```bash
  T=$(herdr --session <server> tab create --workspace <ws> --cwd "$HOME" --label "<unit>" --no-focus)
  P=$(echo "$T" | jq -r .result.root_pane.pane_id)
  herdr --session <server> agent start <batch>-<unit> --kind claude --pane "$P" --timeout 60000 -- --model <worker-model>
  herdr --session <server> agent wait <batch>-<unit> --until idle --timeout 60000
  herdr --session <server> agent prompt <batch>-<unit> "$(cat "$SPEC")" --wait --until working --timeout 30000
  ```

  Worker names: `<batch>-<unit>`, `[a-z][a-z0-9_-]{0,31}`, unique on the
  machine. Record name, tab, pane and session id in your crew table.

## The spec

One file per unit of work, in your scratch directory. A worker has none of
your context; the spec is all it knows.

- Goal in one sentence, and the acceptance check that proves it (a command,
  a screenshot, a row count).
- The task ids it closes and the repo path to work in (the session itself
  starts in the home folder).
- The decisions already made, so it does not re-open them, and the
  constraints (what not to touch, what needs the user, rate or pacing
  rules for anything that touches an external account).
- The skills to load first.
- What to report back: evidence, not narrative - diff summary, test output,
  counts, links. "Ends every turn with status and what it needs."
- What it must NOT do: no task-status writes (you own Notion), no
  deploys, no pushes to a deploying branch unless the spec says so.

## Review

A worker's "done" is a claim. Before closing a task:

- Read the diff or the evidence it reported; run or spot-check the
  acceptance check yourself when it is cheap, or have a second worker verify
  when it is not.
- Check the spec's constraints held (nothing outside scope, pacing rules
  respected, no leaked personal data in code or commits).
- Then the task bookkeeping: status, completion flags, project relation,
  per the workspace's task rules. Status writes are yours alone.

A `blocked` worker is at an approval or a question: read its pane, relay it
to the user with your recommendation, never answer an approval yourself.

## Report

To the user, one table per turn: unit | worker | status | needs user. Then
the numbered decisions. No per-worker essays. The user reads your text, not
tool output, so anything they must see is restated in the message.

## Finish

Workers preserve their result, then close their own tabs after verified
completion when nothing needs the user; a worker awaiting review stays open.
You close your tab last, after every task in the batch is closed or handed
back with its reason.
