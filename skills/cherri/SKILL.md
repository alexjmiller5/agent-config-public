---
name: cherri
description: The Cherri programming language - write, compile, and debug iOS Shortcuts as code (.cherri files). Use for ANY task touching a .cherri file, the ios-shortcuts repo, writing or modifying an iOS/macOS Shortcut programmatically, or questions about Cherri syntax, actions, includes, glyphs, or compile errors. Bundles the complete cherrilang.org/language docs as local references - consult them instead of guessing syntax or searching the web.
---

# Cherri

> **Last updated: 2026-08-11** (docs synced from cherrilang.org source repo). If today is more than 3 months past this date, offer to run [Self-Update](#self-update).

[Cherri](https://cherrilang.org) is a language that compiles to `.shortcut` files for the Apple Shortcuts app. If the shortcuts live in a dedicated repo, see that repo's AGENTS.md for repo-specific mechanics (secrets/constants pipeline, folder layout).

## Toolchain

With the `cherri` binary installed, it is self-documenting - use these before reaching for the references:

```bash
cherri file.cherri --skip-sign     # compile (unsigned; signing needs contact with Apple servers)
cherri --action=showNotification   # full docs for one action (any action, incl. required include)
cherri --glyph=music               # validate/suggest icon glyph names
cherri --docs=<query>              # search the documentation
cherri file.cherri -d              # also emit the .plist - grep it to verify compiled actions
```

In the ios-shortcuts repo, compile via `just compile <file>` (runs `scripts/compile-shortcut.sh`: substitutes `<<constant:NAME>>` from constants.txt, `<<secret:NAME>>` via `op inject` from the Personal vault). **Claude's shell cannot read the Personal vault** - to compile-validate, sed the placeholders to dummies in a scratch copy:

```bash
sed -E -e 's|<<(secret|constant):([A-Za-z_0-9]+)>>|DUMMY_\2|g' file.cherri > /tmp/check.cherri && cherri /tmp/check.cherri --skip-sign
```

## Syntax cheat sheet

```cherri
#define name My Shortcut          // metadata directives first
#define color blue
#define glyph shazam              // must be a valid glyph - verify with cherri --glyph=
#define from sharesheet           // accepts share-sheet input (read via ShortcutInput global)
#include 'actions/web'            // most actions need an include; the compile error names it

@mutable = "value"                // variables; interpolate with "{mutable}"
const Fixed = getName(@x)         // immutable; fewer compiled actions
@declared: text                   // type-only declaration (assign later, e.g. in if branches)

if @textVar == "yes" && @other contains "x" { ... } else { ... }
repeat i for 20 { ... }           // count can be a variable
for item in @list { ... }
```

## Gotchas (hard-won - read before writing code)

1. **HTTP responses are not dictionaries.** `jsonRequest`/`formRequest`/`downloadURL` return "Contents of URL". `@resp['key']` compiles to an inline aggrandizement that silently reads NOTHING at runtime. Always coerce: `@d = getDictionary(@resp)` then `getValue(@d, "key")`. Walk nested keys one level at a time (no dotted paths), and coerce list items too: `getDictionary(getFirstItem(...))`. Verify with `-d`: the .plist should show `detect.dictionary` + `getvalueforkey`; `WFPropertyVariableAggrandizement` on a response means it's broken.
2. **Conditions require `@` on variables** (`if @var == "x"`), despite doc examples showing bare names. The compiler errors otherwise.
3. **`containsText()` hardcodes a `^` anchor** onto its pattern - prepend `.*` for a real contains match. The `contains` *conditional operator* has no such quirk.
4. **Missing include?** The compile error names the exact `#include` to add. Core actions (`showNotification`, `alert`, `prompt`, …) need none.
5. **`show()` blocks the flow with a modal; `showNotification(body, ?title)` is async** - prefer notifications for fire-and-forget status.
6. **JSON `null` reads back as empty text** - `"{value}"` of a null is `""`, testable with `if !@var`.
7. `nothing()` after unused action outputs frees runtime memory; statement blocks add it automatically at their end.
8. **File-typed form values are inexpressible in cherri v2.3** - dictionary items only support text/number/bool/array/dict, so a multipart file upload (`formRequest` with a file field) compiles to an empty form value that silently uploads nothing. The working structure is `WFItemType: 5` + `WFTokenAttachmentParameterState`; the ios-shortcuts repo post-patches it via `scripts/patch-shortcut-plist.py` in its compile pipeline.
9. **`embedFile()` resolves paths relative to cherri's CWD, not the source file** - run the compiler from the `.cherri` file's directory (the ios-shortcuts compile script does this) or asset references like `assets/foo.mp3` fail when compiling from the repo root. (`base64File` from the docs doesn't exist in cherri v2.3; the action is `embedFile`.)

## References (complete cherrilang.org/language docs, local)

Read the file matching the problem, per the table below.

| Topic | File |
|---|---|
| Variables, constants, globals (`ShortcutInput`, …) | `references/variables-constants-globals.md` |
| If/else, repeat, for, menus | `references/control-flow.md`, `references/menus.md` |
| Types, enums, operators, functions | `references/types.md`, `references/enums.md`, `references/operators.md`, `references/functions.md` |
| Metadata `#define`s (name, color, glyph, from…) | `references/definitions.md` |
| Includes & the package manager | `references/includes.md`, `references/package-manager.md` |
| Custom action definitions | `references/action-definitions.md` |
| Raw actions (use any Shortcuts action Cherri lacks) | `references/raw-actions.md` |
| Copy-paste blocks, import questions/actions, vcards | `references/copy-paste.md`, `references/import-questions.md`, `references/import-actions.md`, `references/vcards.md` |
| Best practices (performance, memory) | `references/best-practices.md` |
| Standard actions by category (web, media, text, device, scripting-ish basics, macOS-only, …) | `references/standard/*.md` - e.g. `web.md`, `media.md`, `text.md`, `basic.md`, `builtin.md`, `stdlib.md` |

## Self-Update

1. Re-download the docs: list `language/` and `language/standard/` in `electrikmilk/cherrilang.org` (`gh api repos/electrikmilk/cherrilang.org/contents/language`), fetch each `.md` from `https://raw.githubusercontent.com/electrikmilk/cherrilang.org/main/language/...`, strip the Jekyll frontmatter/TOC, and write them into `references/` (same filenames, `standard/` subdir preserved).
2. Skim the [changelog/releases](https://github.com/electrikmilk/cherri/releases) since the Last-updated date; fold breaking syntax changes into the cheat sheet and gotchas.
3. Bump the Last-updated date.
