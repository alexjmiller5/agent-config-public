---
name: spotify
description: Use when controlling Spotify from the terminal or scripts on the user's Macs - play/pause/skip, search-and-play, playlists, liking tracks, current-track info, transferring playback between devices, or anything involving the spotify_player CLI/TUI.
---

# Spotify (spotify_player)

Binary: `spotify_player` - TUI with no args, CLI subcommands for scripting.
Installed via nix-config (see `dev-env`).
For full syntax trust `spotify_player -h` / `spotify_player <cmd> -h` over memory.

## Auth - no per-machine step

`spotify_player` on PATH is an op-authed wrapper (nix-config
`home/spotify-player.nix`, same family as the gh/gog/wacli wrappers). Its
auth files - `credentials.json` (librespot session) and one
`<client_id>_token.json` per Web API client (token + refresh token) - live
in the "AI Agent Spotify Player Credentials" 1Password item and are handed
to the binary through a per-call mktemp cache folder (`-C`) deleted on
exit. Any change (a token refresh, a login) is written back, so every
machine is authed as soon as the item is; nothing to run on a new machine.
Caller-set `-C` bypasses the round-trip. Spotify Premium required.

- **Web API client = Alex's own dev app** ("AI Agent Spotify OAuth Client"
  item; the wrapper passes it as `-o client_id=`). The binary is built from
  upstream master, whose custom-client mode falls back to the built-in
  ncspot client on 4xx and routes `search`, `me/playlists`, `playlists/`
  to ncspot always (`ncspot_only_get_endpoints`). Reason: ncspot alone
  gets throttled for hours (429 on every call); a post-2024 dev app alone
  breaks on stripped fields (`missing field followers/popularity`). Never
  copy either client id into config by hand - the wrapper owns it.
- **Re-login (item reset, refresh token expired - 180 days in development
  mode - or the wrapper prints its write-back WARNING):**
  `spotify_player authenticate` through the wrapper re-mints the Web API
  tokens (two browser consents: the dev app and "Spotify for Desktop";
  click Agree or drive `button[data-testid=auth-accept]` with
  chrome-control). Only `credentials.json` needs a TUI launch (a session
  connect writes it; `authenticate` never does) - it is minted once and is
  account-bound, so it rarely needs redoing. The TUI needs a real pty;
  `script -q /dev/null spotify_player` works from an agent shell.
- **429 on ncspot-routed calls (search)** = Spotify throttling the shared
  default app; the binary retries `api_rate_limit_retries` times, then
  errors. Not an auth problem, not fixable client-side - retry later.

## Script recipes (the parts agents guess wrong)

- Search output is **flat arrays**, not Web-API `.tracks.items`:
  `spotify_player search "q" | jq -r '.tracks[0].id'`
  Play top hit: `spotify_player playback start track --id "$(spotify_player search "q" | jq -r '.tracks[0].id')"` - or skip the pipeline with `--name "q"`.
- Device transfer is its own subcommand, not a playback flag:
  `spotify_player connect -n "<device>"`; list with `spotify_player get key devices`.
  The official desktop app only appears as a device while it's running.
- JSON state: `spotify_player get key playback` (other keys: `devices`, `queue`,
  `user-playlists`, `user-liked-tracks`, `user-saved-albums`, `user-top-tracks`).
- Shuffled playlist: `spotify_player playback start context -s -n "gym" playlist`.
- `like` = like current track · `lyrics` = current track's lyrics ·
  `playback volume 80` · playlist CRUD under `spotify_player playlist`.
- Config: `~/.config/spotify-player/app.toml`; one-off override: `-o key=value`.

## Daemon mode on macOS

`spotify_player -d` works (nix build compiles daemon + streaming + rodio) but
**not with media control, which is on by default** - set
`enable_media_control = false` (config or `-o`) before daemonizing. Running it
persistently means a declared launchd agent (see `dev-env`), never raw
`launchctl`.
