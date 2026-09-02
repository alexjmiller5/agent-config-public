---
name: spotify
description: Use when controlling Spotify from the terminal or scripts on the user's Macs - play/pause/skip, search-and-play, playlists, liking tracks, current-track info, transferring playback between devices, or anything involving the spotify_player CLI/TUI.
---

# Spotify (spotify_player)

Binary: `spotify_player` - TUI with no args, CLI subcommands for scripting.
Installed via nix-config (see `dev-env`).
For full syntax trust `spotify_player -h` / `spotify_player <cmd> -h` over memory.

## Auth (first run)

- `spotify_player authenticate` is interactive browser OAuth - an agent cannot
  complete it; ask the user to run it once. Tokens then refresh silently from
  `~/.cache/spotify-player/` (`user_client_token.json` = Web API,
  `credentials.json` = librespot). Spotify Premium required.
- **Never create or configure a developer-app `client_id`** - the bundled
  default has extended quota; a personal one runs in restricted mode and gets
  429/403s.

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
