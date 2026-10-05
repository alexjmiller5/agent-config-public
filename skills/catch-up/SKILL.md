---
name: catch-up
description: Use when the user asks to be caught up on the current session - "/catch-up", "catch me up", "where are we", "where did we leave off", "what's the status", "recap", "what do you need from me" - typically after stepping away, switching between agent tabs, a context compaction, or returning to a long-running session.
---

# Catch-up

One read that lets the user resume this session without scrolling back. It
reports the session's state; it never continues the work.

## Output

Exactly two headed sections, in this order. Put most of the detail in
**Needs you**, so the user can answer accurately without scrolling back.

### Summary

One short paragraph, usually 2-4 sentences, combining completed outcomes,
work in progress, remaining work and loose ends. Include the most useful
result or evidence link, anything still running, and material blockers or
unverified work. Distinguish finished work from plans. Compress routine checks
and cleanup details; do not recreate the old sections as labeled bullets.

### Needs you

A numbered list of every unresolved decision, approval, question or manual
step only the user can handle, including earlier requests still unanswered.
Order blockers first. Give each item enough context to stand alone:

- State the specific question or action, what it concerns, and why their
  input is needed. Explain what their answer will enable or change.
- For choices, use lettered options with the recommendation first, its reason,
  and the meaningful tradeoffs. Make replies like "1a, 2b" possible. Do not
  invent choices when a direct answer is needed.
- For missing information, specify the exact details needed and a useful
  example or answer format when it would remove ambiguity.
- For manual steps, give the relevant link or location, concise instructions,
  and what result the user should report back.
- Carry forward prior answers and approvals; ask only for what is still
  missing. Never turn work the agent can do into a request for the user.

Use a few sentences per item when needed to make the decision clear; omit
implementation details that do not affect the answer. If nothing needs the
user, write "Nothing needed from you."

End the turn after these two sections. Do not continue the underlying work.

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
   the Summary as pending or unverified, never as completed.

## Common mistakes

| Mistake | Instead |
|---|---|
| A long status report followed by terse questions | Brief Summary, self-contained Needs you items |
| A choice without context or consequences | Explain what changes, recommend an option and why |
| Calling written-but-unverified or unpushed work done | Say what verification or delivery remains |
| Hiding a needed approval in the Summary | Put the actionable request in Needs you |
| Forgetting a running command or watcher | Check current processes and mention them in the Summary |
| Asking again for an answered question | Preserve the answer and request only missing input |
| Answering questions or resuming work after the recap | Stop; the user's reply decides what happens next |
