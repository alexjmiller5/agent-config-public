---
name: quota
description: Use when checking how much of an AI coding subscription is left - Claude Code, Codex, Cursor, Copilot, Grok, Kimi, Z.AI or Antigravity plan quota, rate-limit windows, reset times or burn pace - when the user asks "how much do I have left", or before deciding whether it is safe to keep spending a provider's quota.
---

# quota (quota-axi)

Binary: `quota-axi` ([kunchenguid/quota-axi](https://github.com/kunchenguid/quota-axi)),
installed via the machine's package manager (nix here). Data only: it reads local
provider credentials and first-party usage endpoints; it never routes, ranks, or
mints tokens. `quota-axi --help` is the syntax authority over this file.

## Commands

| Need | Run |
|---|---|
| Everything, compact TOON (default for agents) | `quota-axi` |
| One or a few providers | `quota-axi --provider claude,codex` |
| Normalized model for jq | `quota-axi --provider claude --json` |
| Per-window pace / reserve / account evidence | `quota-axi --full` |
| Which credential sources exist (no secret values) | `quota-axi auth` |
| Human live dashboard (needs a real tty - not from an agent shell) | `quota-axi --tui` |

## Reading the default report

- `quota[]` - one row per measurable scope: `effectivePercentRemaining`, `resetsAt`
  (ISO, UTC), `runway` / `limitedBy` (which window binds first), `spendPriority`.
- `exhaustion[]` - only scopes projected to run out before reset, with the ETA.
- `attention[]` - anything non-nominal: `auth_required`, `error`, `unresolved_windows`,
  plus a `remedy` column. **Read this block before reporting numbers** - an empty
  `quota[]` with an `attention` row means "not measured", not "0% left".
- Exit 0 even when some providers failed; 1 = every provider failed; 2 = usage error.

## Gotchas

- **macOS Claude quota needs a one-time Keychain grant.** Until then Claude shows
  `auth_required · keychain_access_required`. The USER runs
  `quota-axi --allow-keychain-prompt` once and clicks **Always Allow** - never click
  that dialog for them. The ACL attaches to `/usr/bin/security`, and the grant marker
  is per Claude account, so it survives package rebuilds.
- A provider whose CLI is installed but not logged in reports `error` / `missing`
  credential sources (e.g. Codex without `~/.codex/auth.json`) - the fix is the
  vendor's own login, not quota-axi.
- A plain read may delegate an expired token's refresh to the vendor CLI; pass
  `--no-credential-refresh` when the read must stay strictly read-only.
- Never run `quota-axi update` on a package-manager install (read-only store) - bump
  the package version instead.
- Percentages are per provider; never present one provider's % as comparable to another's.
