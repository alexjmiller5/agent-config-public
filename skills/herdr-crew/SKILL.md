---
name: herdr-crew
description: Use when one agent should coordinate other coding agents in Herdr tabs - dispatching a batch of tasks to parallel agents the user can watch, monitoring them, relaying their questions and the user's answers, or picking a crew back up after a break or a context reset.
---

# Herdr crew: one coordinator, agents in tabs

You coordinate; each crew agent works in its own Herdr tab, where the user
can watch and type. `herdr --skill` is the command-syntax authority; this
skill is the workflow and the gotchas. It requires access to a running Herdr
server. Approved independent workers use an explicitly selected destination and
the IDs returned by tab creation; the coordinator's own pane identity and
inherited `HERDR_ENV` are not launch requirements. Moving, renaming or closing
the coordinator's conversation still requires its own verified identity.

## Dispatch

1. **Batch** the work into independent groups: one per repo or area, sized
   for one agent, no two agents editing the same files.
2. **Write one prompt file per batch** in your scratch directory: who
   dispatched it and why, the items (ids, links, one-line titles), the rules
   the user set for this run (for example "propose first, then wait"), how
   to report (ends every turn with status and what it needs), and batch
   notes.
3. **Select the destination, then launch each agent:** use the requested server
   session, or `default`. Run `herdr --session <server> workspace list` and select
   the intended workspace; use the sole workspace when there is only one.
   Use that explicit server for every command below and when monitoring.

```bash
T=$(herdr --session <server> tab create --workspace <workspace-id> --cwd "$HOME" --label "Short Label" --no-focus)
P=$(echo "$T" | jq -r .result.root_pane.pane_id)
herdr --session <server> agent start <name> --kind claude --pane "$P" --timeout 60000   # bare: no prompt argument
herdr --session <server> agent wait <name> --until idle --timeout 60000                 # startup can report blocked first
herdr --session <server> agent prompt <name> "$(cat "$PROMPT_FILE")" --wait --until working --timeout 30000
```

- `<name>` follows `[a-z][a-z0-9_-]{0,31}`, describes the batch, and is
  unique per machine.
- New sessions start in the destination user's home folder by default. Use
  another root only when the user requests it; never inherit the coordinator's
  cwd. Put the owning repo path in the prompt so project commands run there.
- After a partial startup or timeout, inspect the returned pane and agent
  before retrying. Reuse that destination; do not create a duplicate worker.
- Another machine: use `herdr --machine <label> --session <server>` for every command.
  Use that machine's home for `--cwd`, not the coordinator's `$HOME`.

4. **Record the crew** in your reply as a table: name, tab label and ID, pane ID,
   machine, server, cwd, items, session id (`herdr agent get <name>` →
   `.result.agent.agent_session.value`).

## Monitor

- **Board:** `herdr agent list` (status per named agent).
- **Wait without polling:** run `herdr agent wait <name> --until blocked
  --until done --until idle --timeout <ms>` per agent in the background,
  and handle each as it returns.
- **Read:**
  - A working agent: `herdr agent read <name> --source visible` (a
    multi-line read fails while it works).
  - An idle or done agent: `--source recent-unwrapped --lines 150`.
- **`blocked`** = an approval or question on its screen. Read it and
  relay it to the user verbatim with your recommendation. Never answer
  approvals yourself.
- **Relay** the user's answers with `herdr agent prompt <name> "<answer>"`.
- **Report** to the user as one short table (agent | status | needs from
  you), not per-agent essays.

## Continue later

Herdr is the ledger: no state file.

- After a break or context reset, run `herdr agent list`, then read each
  agent.
- If a tab died, resume its session in a new tab with `herdr agent start
  <name> --kind <kind> --pane <new pane> -- --resume <session id>` (Codex:
  `-- resume <id>`). The id is in your crew table or wherever the task
  recorded it.
- An agent stopped on a usage limit: switch it to another agent with a
  session-switching skill if you have one, otherwise report it.

## Finish

- Have each worker preserve its result and follow its own verified completion
  procedure before closing its own tab. A worker awaiting user input or review
  stays open. Creating its tab does not authorize closing its conversation.
- Never close another session by focus, guess, or a stale creation receipt.

## Gotchas

| Symptom | Cause / fix |
|---|---|
| `invalid_agent_argument` on start | Long or multi-line prompt as a start argument; start bare, then `agent prompt` |
| `agent_not_ready` / `blocked` right after start | Startup screen; `agent read --source visible`, wait for idle, then prompt |
| `agent_not_idle` on read | Use `--source visible` while it works |
| `agent_blocked` on prompt | It waits at a dialog; relay it, do not type over it |
| `agent_prompt_stalled` | The text sits unsent in the agent's input box (a fresh agent can drop the Enter); `agent read --source visible`, then `herdr agent send-keys <name> enter` - never resend the text |
| Prompt sent, nothing happens | `--wait --until working` confirms the turn started; on a timeout, read before resending |
| Text in an idle agent's input box | Often the harness's greyed prompt suggestion, not something the user typed; a plain-text read cannot tell them apart. Never submit it; ask the user |
| jq errors on `agent read` | `agent read` prints plain text, not JSON; every other command returns JSON |
