# AddressBook SQLite reference

All queries read-only (`file:$db?mode=ro`). Verified on macOS 26 (Darwin 25),
schema `AddressBook-v22`. Timestamps are Core Data epoch: add `978307200`
for `unixepoch`, and use the `'localtime'` modifier for dates to avoid
day-boundary drift.

## Layout

```
~/Library/Application Support/AddressBook/
  AddressBook-v22.abcddb          # root - nearly empty, ignore
  Sources/<uuid>/AddressBook-v22.abcddb   # one per account (iCloud, On My Mac, ...)
```

Account names aren't stored in the source dirs - just query all of them and
union. WAL files sit alongside; `mode=ro` handles them. If a lock error ever
appears, copy the `.abcddb` + `-wal` + `-shm` trio to scratch and query the copy.

## Key tables

| Table | Contents | Join |
|---|---|---|
| `ZABCDRECORD` | people (and group records) - names, org, birthday | `Z_PK` is the FK target |
| `ZABCDPHONENUMBER` | `ZFULLNUMBER`, `ZLABEL` | `ZOWNER = record.Z_PK` |
| `ZABCDEMAILADDRESS` | `ZADDRESS`, `ZLABEL` | `ZOWNER` |
| `ZABCDPOSTALADDRESS` | `ZSTREET, ZCITY, ZSTATE, ZZIPCODE, ZCOUNTRYNAME, ZLABEL` | `ZOWNER` |
| `ZABCDSOCIALPROFILE` | `ZSERVICENAME` (e.g. WHATSAPP), `ZUSERNAME`, `ZURLSTRING` | `ZOWNER` |
| `ZABCDURLADDRESS` | `ZLABEL` (e.g. Telegram, `_$!<HomePage>!$_`), `ZURL` | `ZOWNER` |
| `ZABCDNOTE` | `ZTEXT` | `ZCONTACT = record.Z_PK` |
| `ZABCDRELATEDNAME` | related people: `ZLABEL` (mother, spouse...), `ZNAME` | `ZOWNER` |

`ZABCDRECORD` name columns: `ZFIRSTNAME, ZLASTNAME, ZMIDDLENAME, ZNICKNAME,
ZMAIDENNAME, ZTITLE, ZSUFFIX, ZORGANIZATION, ZDEPARTMENT, ZJOBTITLE`, plus
`ZPHONETICFIRSTNAME`-style variants. `ZUNIQUEID` is the `UUID:ABPerson` id
shared with AppleScript. `ZCREATIONDATE` / `ZMODIFICATIONDATE` are Core Data
timestamps. Filter people rows with
`WHERE ZFIRSTNAME IS NOT NULL OR ZLASTNAME IS NOT NULL OR ZORGANIZATION IS NOT NULL`
(group/metadata rows share the table).

## Labels

Multi-value labels come back as tokens: `_$!<Mobile>!$_`, `_$!<Home>!$_`,
`_$!<Work>!$_`, `_$!<Main>!$_`, `_$!<Other>!$_`, `_$!<HomePage>!$_`,
`_$!<iPhone>!$_`. Strip with:

```sql
CASE WHEN ZLABEL LIKE '_$!<%' THEN lower(substr(ZLABEL, 5, length(ZLABEL) - 8)) ELSE ZLABEL END
```

Custom labels (e.g. `Telegram`) are stored as plain strings.

## Birthdays

`ZBIRTHDAY` is the full date; **year 1604 = "no year set"**. Extract:

```sql
CASE WHEN strftime('%Y', ZBIRTHDAY + 978307200, 'unixepoch', 'localtime') < '1900'
     THEN strftime('%m-%d', ZBIRTHDAY + 978307200, 'unixepoch', 'localtime')
     ELSE date(ZBIRTHDAY + 978307200, 'unixepoch', 'localtime') END
```

(`ZBIRTHDAYYEARLESS` is NOT a boolean - it's the same MM-DD as a timestamp
normalized to year 2001, populated for every birthday.)

## Recipes

Search by phone (format-insensitive - digits only; this is what AppleScript
can't do):

```sql
SELECT r.ZFIRSTNAME, r.ZLASTNAME, p.ZFULLNUMBER
FROM ZABCDPHONENUMBER p JOIN ZABCDRECORD r ON p.ZOWNER = r.Z_PK
WHERE replace(replace(replace(replace(p.ZFULLNUMBER,'(',''),')',''),'-',''),' ','') LIKE '%2035551234%';
```

Social profiles / URLs per person:

```sql
SELECT r.ZUNIQUEID, s.ZSERVICENAME, s.ZUSERNAME, s.ZURLSTRING
FROM ZABCDSOCIALPROFILE s JOIN ZABCDRECORD r ON s.ZOWNER = r.Z_PK;

SELECT r.ZUNIQUEID, u.ZLABEL, u.ZURL
FROM ZABCDURLADDRESS u JOIN ZABCDRECORD r ON u.ZOWNER = r.Z_PK;
```

Notes:

```sql
SELECT r.ZUNIQUEID, n.ZTEXT
FROM ZABCDNOTE n JOIN ZABCDRECORD r ON n.ZCONTACT = r.Z_PK WHERE n.ZTEXT IS NOT NULL;
```

`sqlite3 -json` for JSON output; `group_concat(x, '; ')` correlated
subqueries flatten multi-values into one row per person (see the bulk query
in SKILL.md).
