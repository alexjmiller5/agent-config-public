---
name: spotify
description: Use when controlling Spotify from the terminal or scripts on the user's Macs - play/pause/skip, search-and-play, playlists, liking tracks, current-track info, transferring playback between devices, or anything involving the spotify_player CLI/TUI.
---

# Spotify (spotify_player)

Binary: `spotify_player` - TUI with no args, CLI subcommands for scripting.
For full syntax trust `spotify_player -h` / `spotify_player <cmd> -h` over memory.
Spotify Premium required.

## Auth

`spotify_player` keeps its auth files in its cache folder (`-C`, default
`~/.cache/spotify-player`): `credentials.json` (the librespot session) and one
`<client_id>_token.json` per Web API client (token + refresh token). A
machine can wrap the binary to hand these files in through a temporary `-C`
folder; when a private auth companion skill (`spotify-auth`) is installed,
load it for where this machine keeps them and how a re-login is saved.

- **Web API client = your own Spotify developer app**, passed as
  `-o client_id=<id>`. Upstream master's custom-client mode falls back to the
  built-in ncspot client on 4xx and routes `search`, `me/playlists`,
  `playlists/` to ncspot always (`ncspot_only_get_endpoints`). Reason: ncspot
  alone gets throttled for hours (429 on every call); a post-2024 dev app
  alone breaks on stripped fields (`missing field followers/popularity`).
- **Re-login (auth files reset, or the refresh token expired - 180 days in
  development mode):** `spotify_player authenticate` re-mints the Web API
  tokens (two browser consents: your dev app and "Spotify for Desktop";
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
persistently means a launchd agent declared in your machine configuration,
never raw `launchctl`.
