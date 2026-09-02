# agent-config-public

The shareable half of my agent configuration: agent-agnostic skills with
nothing personal in them. The private half (personal skills, memory, global
AGENTS.md, harness settings) lives in a separate private repo that symlinks
these skills in alongside its own.

## Layout

- `skills/` - one directory per skill, each with a `SKILL.md` (frontmatter
  `name` + `description`, then the instructions) and optional `references/`.

## Using these skills

Clone the repo and symlink the skills you want into your agent's skills
directory (e.g. `~/.claude/skills/` for Claude Code):

```bash
git clone https://github.com/alexjmiller5/agent-config-public ~/.config/agent-config-public
ln -s ~/.config/agent-config-public/skills/* ~/.claude/skills/
```

Some skills reference private companion skills by name (workspace maps,
machine specifics) - they degrade gracefully when those don't exist.

## Contributing personal-info-free

Nothing personal ever goes in this repo: no names, emails, phone numbers,
vault/database IDs, machine hostnames, or personal file paths. Personal
halves of a skill belong in a private companion skill.
