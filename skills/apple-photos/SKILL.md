---
name: apple-photos
description: "Query, export, and edit the user's Apple Photos library via the osxphotos CLI - find photos by person/album/keyword/date/ML-label, export with templated paths, batch-edit metadata, import, and read library stats. Use for anything touching Photos.app, the photo library, iPhoto, albums, faces/people in photos, screenshots, or exporting/backing up photos."
homepage: https://rhettbull.github.io/osxphotos/cli.html
---

# Apple Photos via osxphotos

Nothing is installed: run it as `uvx osxphotos …` (uv resolves and caches
it from PyPI; first run downloads, later runs are instant). It reads a
copy of the Photos SQLite DB directly (fast, safe) and drives Photos.app
via AppleScript for writes.

Self-documenting: `uvx osxphotos help COMMAND` or `uvx osxphotos help COMMAND TOPIC`
(e.g. `uvx osxphotos help export keyword`). Full docs: homepage URL above.
Hidden commands/options: prefix with `OSXPHOTOS_SHOW_HIDDEN=1`.

## The library

- `~/Pictures/Photos Library.photoslibrary` is the default (last-opened)
  library; `--library PATH` overrides.
- **Every invocation loads the whole DB (about a minute on a ~90k-photo
  library).** Batch
  everything you can into one invocation; for iterative exploration use
  `uvx osxphotos repl` or the Python API instead of repeated CLI calls.
- mdfind/UserQueryParser lines on stderr are normal noise.

## Query semantics (same options on `query`, `export`, `batch-edit`, …)

- Different options are **AND**; the same option repeated is **OR**.
  `--person A --person B --keyword vacation` = (A OR B) AND vacation.
- `-i` for case-insensitive matching.
- Album/folder names containing `/` are escaped with `//`.
- Recently Deleted is excluded unless `--deleted` / `--deleted-only`.

Key selectors: `--person` `--album` `--folder` `--keyword` `--label`
(Photos' ML labels - list them with `uvx osxphotos labels`) `--place`
`--favorite` `--screenshot` `--selfie` `--panorama` `--live` `--portrait`
`--burst` `--hdr` `--only-photos/--only-movies` `--from-date/--to-date`
(ISO 8601) `--year` `--added-in-last '1 week'` `--min-size/--max-size`
`--duplicate` `--not-in-album` `--selected` (current Photos selection)
`--regex REGEX TEMPLATE` (regex over any template value)
`--query-eval 'photo.favorite'` (arbitrary python over PhotoInfo).

## Output - never dump full `--json` (89k photos!)

- `--count` - just the number.
- `--field uuid "{uuid}" --field name "{original_name}"` - chosen columns.
- `--print "{template}" --quiet` - one rendered template line per photo.

Discovery (all take `--json`): `persons`, `albums` (`-s` by size),
`keywords`, `labels`, `places`, `list` (libraries), `info` (library stats).

## Recipes

```bash
uvx osxphotos query --person "Jane Doe" --count
uvx osxphotos query --person "Jane Doe" --print "{uuid} {original_name}" --quiet
uvx osxphotos query --favorite --year 2025 --add-to-album "Best of 2025"   # write!
uvx osxphotos export ~/exports --album "Travel" --directory "{created.year}/{created.mm}"
uvx osxphotos export /Volumes/backup/photos --update   # incremental; re-runs only export new/changed
uvx osxphotos batch-edit --dry-run --keyword "Family" --album "Reunion"  # writes; ALWAYS --dry-run first
uvx osxphotos import ~/pics --album "Imported/{today.date}" --split-folder "/"
```

`export` extras worth knowing: `--update` (incremental, tracked in an
export DB inside DEST), `--dry-run`, `--limit N` (testing),
`--export-by-date`, `--skip-original-if-edited`, `--convert-to-jpeg`,
`--sidecar xmp|json`, `--exiftool` (writes metadata into exported files;
needs `exiftool` in PATH), `--download-missing` (pull from iCloud, slow),
`--preview-if-missing`.

Also exists (see `uvx osxphotos help X`): `timewarp` (fix dates/timezones),
`sync` (metadata between libraries), `push-exif`, `add-locations`,
`compare` (two libraries), `orphans`, `show`/`uuid`/`inspect`, `run`
(run a python script with osxphotos env).

## Templating (used by --directory, --filename, --print, --field, batch-edit)

Single-value: `{original_name}` `{name}` `{title}` `{descr}` `{uuid}`
`{created}` `{created.year}` `{created.mm}` `{created.strftime,%Y-%m}`
`{place.name}` `{place.name.city}` `{exif.camera_make}` `{media_type}`.
Multi-value (can fan out to multiple export dirs): `{album}`
`{folder_album}` `{keyword}` `{person}` `{label}`.
Conditionals: `{favorite?fav,notfav}`, `{edited?edited,original}`.
Anything else: `{photo.PROPERTY}` reaches the full PhotoInfo object.
Test templates live with `uvx osxphotos inspect -T "{template}"` (select a
photo in Photos first) or `osxphotos query --limit`-style small queries.

- **A multi-value field in `--print` fans out to one line per VALUE** (a
  20-label photo prints 20 lines). Join instead with `{DELIM+FIELD}`, e.g.
  `{,+label}` → one line per photo, labels comma-joined. `{photo.labels}`
  (list attribute) fans out the same way - always use the join form.

## Tip: one-line-per-photo digest of a date range

`--print "{uuid}|{created.strftime,%a %m-%d %H:%M}|{place.name}|{,+label}"`
over a `--from-date`/`--to-date` window gives a compact digest of a whole
period in one invocation: GPS place names, timestamps, and ML labels for
indoor scenes (English Breakfast, Nightclub, Stadium…), with exported
previews of key photos (see below) for reading signage/menus/tickets
visually. Caveats when interpreting:

- **Not every library photo was taken by the user.** Photos saved from
  shares/AirDrop carry the SENDER's GPS and time - a fix that's physically
  impossible given adjacent photos means someone else took it.
- **Duplicate timestamps ± whole hours** are shared/saved copies rendered
  in the original device's timezone; trust the copies consistent with the
  GPS-tagged sequence. Screenshots have no GPS but device-local time.

## Exporting when originals are in iCloud (optimized storage)

On an optimize-storage Mac most originals aren't local: `export` reports
them `missing` and exports 0 files. `--download-missing` is slow;
`--preview-if-missing` exports Photos' local preview instead - instant and
plenty for visual identification (reading signs, menus, tickets). It asks
an interactive y/N - pipe `echo y |`. Files land as `*_preview.jpeg` (or
`.heic` without `--convert-to-jpeg`). Export selected photos by repeating
`--uuid`, with `--filename "{uuid}"` for predictable names.

## Writes: what to know

- Write paths (`batch-edit`, `--add-to-album`, `import`, `timewarp`) go
  through Photos.app/AppleScript: Photos must be launchable, it only works
  on the **default (last-opened) library**, and the invoking context needs
  a TCC Automation grant for Photos on the invoking terminal.
- **Big imports wedge Photos - import per-file, never one giant batch.**
  A single AppleScript `import` of ~25GB/33 videos hung Photos' UI thread
  outright. photoscript surfaces the hang as
  `AppleScriptError: ... User canceled. (-128)`, which looks like a TCC
  denial but usually is NOT one - diagnose before blaming permissions.
- **On -128 / -1712: diagnose the hang, then force-quit Photos.**
  Hang tells: process alive (`pgrep -x Photos`) but ~0% CPU, menus won't
  open, clicking the dock icon does nothing, every AppleEvent times out
  (-1712). That state never self-recovers - `killall Photos`, relaunch
  (`open -a Photos`), and only then re-check permissions if writes still
  fail. Force-quit is safe: a wedged bulk import stages file copies but
  registers nothing, so no partial media items land (the orphaned staging
  is cleaned up by Photos itself). After relaunch, VERIFY what actually
  imported (query the album/`--added-in-last`) rather than assuming, then
  resume with one `import {file}` AppleScript call per file (own timeout
  each) - 33 files imported flawlessly that way after the batch hang.
- `batch-edit` operates on the current Photos selection unless you pass
  query options. `--undo` reverts the last batch-edit (not album adds).
- Always `--dry-run` first on any write against many photos.
- Reads need Full Disk Access on the invoking terminal.

## Python API (for anything beyond one-liners)

PEP 723 script with `dependencies = ["osxphotos"]`, run via `uv run`:
`osxphotos.PhotosDB()` → `.photos(persons=[...], albums=[...], ...)` →
`PhotoInfo` (`.uuid .original_filename .persons .face_info .keywords
.albums .path .score.overall` …). `ExportOptions`/`PhotoExporter` for
programmatic export. API docs: https://rhettbull.github.io/osxphotos/
