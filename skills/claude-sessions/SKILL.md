---
name: claude-sessions
description: Finds and recovers content from Claude Code session history files. This skill should be used when searching for deleted files, tracking changes across sessions, analyzing conversation history, or recovering code from previous Claude interactions. Triggers include mentions of "session history", "recover deleted", "find in history", "previous conversation", or ".claude/projects".
---

# Claude Sessions

Claude Code writes every session as JSONL at
`~/.claude/projects/<encoded-project-path>/<session-id>.jsonl`. Everything
below is `jq`/`rg` over those files - no tooling to install.

## Finding the project directory

**The directory name is the project's ABSOLUTE working-directory path with
every `/` AND `.` replaced by `-`** - never the basename. So
`/Users/<name>/.config/agent-config` becomes
`-Users-<name>--config-agent-config`, and a bare `agent-config` matches
nothing.

```bash
D=~/.claude/projects/$(echo /abs/path/to/project | tr '/.' '-')
```

**A failed `ls` is not proof there is no history** - reverse-look-up instead:

```bash
ls ~/.claude/projects/ | grep -i <project-name>
```

Sessions run from **Claude Desktop's cowork / built-in Claude Code mode**
also land here (Desktop runs a bundled CLI); only Desktop's *native* chat
lives elsewhere (a LevelDB store, not JSONL). "It ran inside Desktop" does
not mean it is missing.

## Operations

List sessions, newest first:

```bash
ls -lt "$D"/*.jsonl | head
```

Search across every session of a project (add `-i`, drop `-c` for hits):

```bash
rg -c 'search term' "$D"/*.jsonl | sort -t: -k2 -rn | head
```

Tool-usage breakdown for one session:

```bash
jq -r '.message.content[]?|select(.type=="tool_use")|.name' "$D"/<session>.jsonl \
  | sort | uniq -c | sort -rn
```

Every file a project's sessions ever wrote:

```bash
jq -r 'select(.message.content|type=="array")|.message.content[]
       |select(.type=="tool_use" and .name=="Write")|.input.file_path' \
  "$D"/*.jsonl | sort -u
```

Recover one of them (last write wins, so `tail`/redirect the final copy):

```bash
jq -r --arg f /abs/path/to/lost.py 'select(.message.content|type=="array")
       |.message.content[]|select(.type=="tool_use" and .name=="Write"
       and .input.file_path==$f)|.input.content' "$D"/*.jsonl
```

Only `Write` calls carry full content. `Edit` calls carry
`old_string`/`new_string` deltas (same filter, `name=="Edit"`); a file only
ever edited cannot be reconstructed whole.

Schema details and older-session field locations: `references/session_file_format.md`.
