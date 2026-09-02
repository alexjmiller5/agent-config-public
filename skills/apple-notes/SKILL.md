---
name: apple-notes
description: "Create, view, edit, delete, search, move, or export Apple Notes via the memo CLI and AppleScript on macOS. Use for any task reading or writing the user's Apple Notes."
---

# Apple Notes CLI

Use `memo notes` to manage Apple Notes directly from the terminal. Create, view, edit, delete, search, move notes between folders, and export to HTML/Markdown.

Setup

* Preferred install: a shell wrapper around `uvx --from git+https://github.com/antoniorodr/memo memo`
  (the brew formula's python can be broken). Update: `uvx --refresh --from git+https://github.com/antoniorodr/memo memo --version`.
* Alternative: `brew tap antoniorodr/memo && brew install antoniorodr/memo/memo` (on declaratively managed machines, declare it in your config - never ad-hoc).
* macOS-only; requires an Automation TCC grant (calling app → Notes). If AppleScript errors with -1743, enable it in System Settings → Privacy & Security → Automation, or run one memo/osascript command from the target app to trigger the prompt.

View Notes

* List all notes: `memo notes`
* Filter by folder: `memo notes -f "Folder Name"`
* Search notes (fuzzy): `memo notes -s "query"`

Create Notes

* Add a new note: `memo notes -a [-f "Folder Name"]`
  * `-a` takes NO title argument (`memo notes -a "Title"` errors). It opens
    `$EDITOR` on a temp file; first line becomes the title. For
    non-interactive/agent use, point `EDITOR` at a script that writes the
    content into `"$1"`.

Edit / Delete / Move / Export

* `memo notes -e` / `-d` / `-m` / `-ex` open an interactive selector on a TTY
  and cannot be driven by an agent. Use the osascript primitives below
  instead.

## osascript primitives (canonical mechanics)

Bulk-read every note body in a folder (memo's list truncates titles):

```bash
osascript -e 'tell application "Notes"
  set out to ""
  repeat with n in notes of folder "Notes" of account "iCloud"
    set out to out & "=====NOTE=====" & linefeed & (name of n) & linefeed & (plaintext of n) & linefeed
  end repeat
  return out
end tell'
```

Creation date of a note (for backdating retroactive entries):

```bash
osascript -e 'tell application "Notes" to get creation date of first note of folder "Notes" of account "iCloud" whose name is "TITLE"'
```

Delete by title (Recently Deleted keeps 30 days as the safety net):

```bash
osascript -e 'tell application "Notes" to delete (first note of folder "Notes" of account "iCloud" whose name is "TITLE")'
```

Folder names: `osascript -e 'tell application "Notes" to return name of folders of account "iCloud"'`.

Limitations

* Cannot edit notes containing images or attachments.
* Interactive prompts may require terminal access.
* memo caches note lists; a fetch made while TCC was denied caches an empty
  list that persists after access is granted - pass `-nc` to bypass/refresh.

