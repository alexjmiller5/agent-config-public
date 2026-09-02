---
name: apple-contacts
description: "Read, search, create, update, or delete Apple Contacts (Contacts.app / iCloud address book) from the shell on macOS, including bulk exports and importing contacts into the Notion People DB. Use for any task touching the user's contacts, phone numbers, the address book, or 'who is X' lookups."
---

# Apple Contacts

Zero-install: two macOS built-ins cover everything, no third-party CLI.

| Path | Use for | Speed |
|------|---------|-------|
| `sqlite3` read of the AddressBook DB | bulk reads, exports, joins, JSON output | ~10 ms for ~1000 contacts |
| `osascript` (AppleScript → Contacts.app) | targeted lookups, ALL writes, vCards | ~1 s per call; looping all contacts takes ~1 min |
| pyobjc + Contacts framework (CNContacts) | bulk WRITES, or shielding from schema churn | ~0.9 s for ~1000 contacts |

**NEVER write to the SQLite DB** - it is Contacts.app's and iCloud sync's
private store; reads are safe (`mode=ro`), writes corrupt sync. All mutations
go through AppleScript.

## Permissions (TCC)

- AppleScript needs an Automation grant (calling app → Contacts); sqlite3
  needs Full Disk Access. Both must be granted on the invoking terminal.
- Error `-1743` or "unable to open database": System Settings → Privacy &
  Security → Automation (or Full Disk Access) for the terminal app.
- TCC prompts don't fire in embedded terminals (VS Code); trigger the grant
  once from Terminal.app.

## Bulk reads (sqlite3)

The root DB `~/Library/Application Support/AddressBook/AddressBook-v22.abcddb`
is nearly empty - real data lives in per-account DBs at
`Sources/<uuid>/AddressBook-v22.abcddb`. Query every source:

```bash
for db in ~/Library/Application\ Support/AddressBook/Sources/*/AddressBook-v22.abcddb; do
sqlite3 -json "file:$db?mode=ro" "
SELECT r.ZUNIQUEID AS id, r.ZFIRSTNAME AS first, r.ZLASTNAME AS last,
       r.ZMIDDLENAME AS middle, r.ZNICKNAME AS nick,
       r.ZORGANIZATION AS org, r.ZJOBTITLE AS title,
       CASE WHEN strftime('%Y', r.ZBIRTHDAY + 978307200, 'unixepoch', 'localtime') < '1900'
            THEN strftime('%m-%d', r.ZBIRTHDAY + 978307200, 'unixepoch', 'localtime')
            ELSE date(r.ZBIRTHDAY + 978307200, 'unixepoch', 'localtime') END AS birthday,
       (SELECT group_concat(ZFULLNUMBER, '; ') FROM ZABCDPHONENUMBER WHERE ZOWNER = r.Z_PK) AS phones,
       (SELECT group_concat(ZADDRESS, '; ')    FROM ZABCDEMAILADDRESS WHERE ZOWNER = r.Z_PK) AS emails
FROM ZABCDRECORD r
WHERE r.ZFIRSTNAME IS NOT NULL OR r.ZLASTNAME IS NOT NULL OR r.ZORGANIZATION IS NOT NULL;"
done
```

`ZUNIQUEID` is the same `UUID:ABPerson` id AppleScript uses - the stable
cross-path key. Full schema, more columns (socials, URLs, notes, addresses),
and label decoding: [references/sqlite.md](references/sqlite.md).

## Targeted lookups (AppleScript)

```bash
# Count / list names
osascript -e 'tell application "Contacts" to get name of every person whose name contains "John"'

# Full details for one person (NEVER `first person whose` - buggy; filter then item 1)
osascript -e 'tell application "Contacts"
  set matches to every person whose name contains "John"
  if (count of matches) > 0 then
    set p to item 1 of matches
    return {id of p, name of p, value of phones of p, value of emails of p, organization of p}
  end if
end tell'

# By id (stable - prefer over names once known)
osascript -e 'tell application "Contacts" to get name of person id "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX:ABPerson"'

# Single-contact vCard
osascript -e 'tell application "Contacts" to get vcard of person id "...:ABPerson"'
```

Phone search (`whose value of phones contains "..."`) is exact-match on the
stored format (`+1XXXXXXXXXX` ≠ `XXXXXXXXXX`) - for phone/email lookups use
the sqlite path with `LIKE` instead. Name `contains` is case-insensitive
partial; `is` is exact. No match returns empty output, not an error.

## Writes (AppleScript)

Every mutation needs an explicit `save` inside the `tell` block or it
silently doesn't persist. All verified working:

```bash
# Create
osascript -e 'tell application "Contacts"
  set p to make new person with properties {first name:"Jane", last name:"Doe", organization:"Acme"}
  make new phone at end of phones of p with properties {label:"mobile", value:"+15551234567"}
  make new email at end of emails of p with properties {label:"work", value:"jane@example.com"}
  save
  return id of p
end tell'

# Edit a property (birthday: build the date from components - literals are locale-fragile)
osascript -e 'tell application "Contacts"
  set d to current date
  set {year of d, month of d, day of d} to {1997, 4, 20}
  set birth date of person id "...:ABPerson" to d
  save
end tell'

# Delete
osascript -e 'tell application "Contacts"
  delete person id "...:ABPerson"
  save
end tell'
```

Labels: `mobile`, `home`, `work`, `main`, `other` (or custom strings).
Confirm with the user before deleting or bulk-editing real contacts.

## Gotchas

- Bulk `get vcard of every person` fails (error `-1741`, reply too large);
  per-person looping works but is slow. Bulk = sqlite.
- Long AppleScript ops need `with timeout of N seconds ... end timeout` (the
  default Apple-event timeout is 2 min, and osascript otherwise hangs).
- Birthday with no year is stored as year **1604** (Apple's no-year
  sentinel) - test `year < 1900` and emit MM-DD. (`ZBIRTHDAYYEARLESS` is not
  a flag: it's the MM-DD as a timestamp in year 2001, set for every birthday.)
- Raw labels in sqlite/vCards look like `_$!<Mobile>!$_` - strip to the inner
  token (AppleScript's `label` property returns them clean).
- `note` is documented as entitlement-locked (`CNContactNoteKey` needs
  `com.apple.developer.contacts.notes`), but an unsandboxed pyobjc fetch of it
  returns no error here. Unproven either way.
  sqlite (`ZABCDNOTE.ZTEXT`) reads them regardless.
- Contact ids are `UUID:ABPerson`; accept and prefer ids everywhere.

## Third path: CNContacts via pyobjc

Apple's official API, reachable with NO signed binary - a `uv run` script is
the TCC subject and inherits the terminal's existing Contacts grant
(`authorizationStatusForEntityType_` returns 3 here). PEP 723 header:
`dependencies = ["pyobjc-framework-Contacts"]`.

Worth it only for **bulk writes** (one `CNSaveRequest` batches many changes vs
AppleScript's ~1 s per event) or if a macOS upgrade ever breaks the private
sqlite schema. It is ~100x SLOWER than sqlite for bulk reads (0.9 s vs 9 ms),
so it does not replace the two paths above.

Two footguns it removes: yearless birthdays come back as
`NSDateComponentUndefined` instead of the 1604 sentinel, and
`CNLabeledValue.localizedStringForLabel_()` turns `_$!<Mobile>!$_` into
`mobile` (custom labels pass through unchanged).

## Importing into the Notion People DB

The People DB holds the user's standardized person format - get its
data_source_id and schema from the workspace-map skill in your setup
(e.g. `notion-workspace`) and read that before writing to it. Ad-hoc import flow:

1. Bulk-export via the sqlite query above (add socials/URLs from
   [references/sqlite.md](references/sqlite.md) as needed).
2. **Dedup first**: query People by name (`title contains` first+last, also
   check Nickname) before creating - never blind-create.
3. Map fields:

| Apple Contacts | People DB property |
|---|---|
| first + last name | Name (title, "First Last") + First Name + Last Name |
| middle name / nickname | Middle Name / Nickname |
| organization | Company |
| job title | Position Title |
| birthday (with year) | Birthday (date) |
| birthday (year 1604 = yearless) | Slightly Known Birthday (rich_text, "MM-DD") |
| social profiles / URLs (Instagram, LinkedIn, Facebook) | Instagram / LinkedIn URL / Facebook |
| groups | Tags (multi_select) |

Phones, emails, and postal addresses have no People DB property - they stay
in Apple Contacts by design; don't invent properties for them.
