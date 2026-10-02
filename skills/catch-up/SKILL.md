---
name: catch-up
description: Use when the user asks to be caught up on the current session - "/catch-up", "catch me up", "where are we", "where did we leave off", "what's the status", "recap", "what do you need from me" - typically after stepping away, switching between agent tabs, a context compaction, or returning to a long-running session.
---

# Catch-up

One read that lets the user resume this session without scrolling back. It
reports the session's state; it never continues the work.

## Output

Exactly these five headed sections, in this order, each a bulleted list. A
section with nothing in it reads `- none`.

1. **Done** - outcomes finished this session, one bullet per outcome (not per
   step), each with the evidence the user would click: commit hash, PR or page
   URL, file path, passing check.
2. **In progress** - work started and not finished, how far it got, and
   anything still running: background shells, monitors and watchers, subagents,
   remote jobs, CI runs.
3. **Needs you** - every open decision, approval, question or manual step only
   the user can do, including ones asked long ago and never answered. Number
   them, give the options with your recommendation first, so the user can reply
   "1a, 2b".
4. **Remaining** - agreed work not started yet, in the order you would do it.
5. **Loose ends** - whatever else the user would want surfaced: uncommitted or
   unpushed changes, files, tabs or processes you created, trackers or tickets
   not yet updated, checks that failed or were skipped, assumptions you made,
   problems you noticed outside the scope.

End the turn after the five sections.

## Gathering

1. Read the session from your own context. After a compaction the summary
   drops detail; the transcript is the record (Claude Code:
   `~/.claude/projects/<cwd-slug>/<session-id>.jsonl`) - search it for
   questions you asked and the replies.
2. Verify perishable facts instead of recalling them, read-only only: `git
   status -sb` in every repo the session touched, your background task list
   and the processes you started, the current state of any ticket you were
   updating.
3. Report what is true now. Something said or planned but not done goes under
   Remaining or Loose ends, never Done.

## Common mistakes

| Mistake | Instead |
|---|---|
| Restating only the pending questions | All five sections; the questions are section 3 |
| Narrating steps ("then I ran...") | One bullet per outcome, with its evidence |
| "Done" for written-but-unverified or unpushed work | In progress or Loose ends, saying what is missing |
| Forgetting a background command or watcher still running | Check the task list; list it under In progress |
| Answering a question or resuming work after the recap | Stop; the user's reply decides what happens next |
