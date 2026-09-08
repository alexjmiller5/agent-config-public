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
`home/spotify-player.nix`, same family as the gh/gog/wacli wrappers): its
two auth files - `credentials.json` (librespot session) and
`user_client_token.json` (Web API token + refresh token) - live in the
"AI Agent Spotify Player Credentials" 1Password item and are handed to the
binary through a per-call mktemp cache folder (`-C`) that is deleted on
exit. Any change (a token refresh, a fresh login) is written back to the
item, so every machine is authed as soon as the item is. Nothing to run on
a new machine. Caller-set `-C` bypasses the round-trip. Spotify Premium
required.

- **Re-login (item reset, refresh token expired after 6 months idle, or the
  wrapper prints its write-back WARNING):** launch the TUI once through the
  wrapper (`spotify_player`, no args) - it runs both OAuth consents in the
  browser (two "Agree" pages, click or drive them with chrome-control) and
  the wrapper stores the result on quit. `spotify_player authenticate` is
  NOT enough: it mints only the Web API token, never `credentials.json`
  (that file is written by a session connect, i.e. the TUI), and CLI
  subcommands need both. The TUI needs a pty; headless, run it under
  `script -q /dev/null spotify_player` and kill the binary once
  `credentials.json` exists.
- **Never set `client_id`** - the built-in default is ncspot's
  extended-quota app; a personal one runs in restricted mode (429/403s).
- **429 Too Many Requests on every command** = Spotify's short-window
  quota, usually after several TUI launches in a row (each startup fires a
  burst of requests). Wait it out; it is not an auth problem.

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
