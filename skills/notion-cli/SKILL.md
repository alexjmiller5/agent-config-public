---
name: notion-cli
description: Notion operations via the official `ntn` CLI - query data sources, create/update pages, read/write page content as Markdown, search, and filter. Use when any agent needs to interact with Notion programmatically. Covers authentication, CLI commands, property formats, filter syntax, pagination, and rate limits. For the user's specific workspace structure (DB IDs, relations, schemas), use the notion-workspace skill alongside this one.
---

# Notion CLI / API Skill

> **Last updated: 2026-08-15.** If today is more than 1 month past this date, this skill may be stale. Before proceeding, tell the user and offer to run the [Self-Update](#self-update) steps. If they decline, continue normally and don't ask again this session.

## Authentication

Auth is a Notion internal-integration secret, stored wherever your setup keeps secrets (e.g. a 1Password item). The `ntn` CLI takes it via `NOTION_API_TOKEN` (overrides any keychain login):

```bash
export NOTION_API_TOKEN=$(op read "op://<vault-id>/<item-id>/credential")
```

Export once per shell, not per command (secret-manager rate limits). If a workspace-map skill exists in your setup (e.g. `notion-workspace`), the concrete reference lives there.

- The integration only sees pages **connected** to it in Notion. A `403`/object-not-found on a page the user clearly has means the connection is missing - the user adds it via the page's ••• menu → Connections.
- Alternative: a personal access token from https://www.notion.so/developers/tokens also works in `NOTION_API_TOKEN` (acts as the user's own user, no connections needed, max 1yr expiry) - not currently used.

## The CLI: `ntn`

Official Notion CLI, installed via Homebrew on the user's Macs (`brew install --cask notion-cli`; upgrade: `brew upgrade --cask notion-cli`; elsewhere: `curl -fsSL https://ntn.dev | bash`). **It is self-documenting - consult it before guessing syntax:**

```bash
ntn <command> --help      # help for any command
ntn api ls                # enumerate all public API endpoints
ntn api <path> --docs     # full official docs for an endpoint
ntn api <path> --spec     # reduced OpenAPI fragment
```

Beyond the commands used below, the CLI also has `whoami` / `auth` (inspect credentials), `files` (file uploads, beta), `doctor`, and `update`.

**There is deliberately NO local api-docs mirror.** When this skill's
references don't cover an endpoint or parameter, `ntn api <path> --docs` IS
the documentation - live, current, and complete (e.g.
`ntn api v1/data_sources/{data_source_id}/query --docs`). Find the path with
`ntn api ls`, then pull its docs; never go hunting for cached copies.

## Core Operations

### 1. Query a Data Source (Most Common)

```bash
ntn datasources query $DATA_SOURCE_ID \
  --filter '{"property":"Status","status":{"equals":"Done"}}' \
  -s "Created time desc" \
  --limit 100 --json
```

- `--filter` takes raw Notion filter JSON verbatim (`--filter-file -` for stdin)
- `-s "<property> [asc|desc]"`, repeatable, order matters - takes **exact property names only** (case-sensitive). Timestamp sorts/filters (`created_time` / `last_edited_time`) aren't properties: use `ntn api v1/data_sources/$ID/query` with `{"sorts": [{"timestamp": "last_edited_time", "direction": "descending"}]}` / `{"filter": {"timestamp": "created_time", ...}}`
- **Requires a data source ID, not a database ID.** `ntn datasources resolve <database-id>` lists a database's data sources.
- **Pagination**: default `--limit 25` (max 100); when output reports more results, re-run with `--start-cursor <cursor>` until exhausted:

```bash
CURSOR=""
while :; do
  RESPONSE=$(ntn datasources query $DATA_SOURCE_ID --limit 100 --json \
    ${CURSOR:+--start-cursor "$CURSOR"})
  echo "$RESPONSE" | jq '.results[]'
  [ "$(echo "$RESPONSE" | jq -r '.has_more')" = "true" ] || break
  CURSOR=$(echo "$RESPONSE" | jq -r '.next_cursor')
done
```

### 2. Read Page Content - as Markdown

```bash
ntn pages get $PAGE_ID          # Markdown, properties as frontmatter
ntn pages get $PAGE_ID --json   # raw; `markdown` is a TOP-LEVEL field
```

Properties only, without the body: `ntn api v1/pages/$PAGE_ID`.

One call returns the whole page - no block pagination, no recursive children. If the response has `"truncated": true`, pass each id in `unknown_block_ids` back to the same endpoint to fetch the remaining subtrees; a `404` on one means it's permission-restricted, not truncated - skip it.

### 3. Create a Page

```bash
ntn pages create --parent data-source:$DATA_SOURCE_ID --content '# Title

Body markdown here.'
```

`--parent` accepts `page:<id>`, `database:<id>`, or `data-source:<id>`; content via `--content`, stdin, or `$EDITOR`. To set properties beyond the title, use the API passthrough:

```bash
ntn api v1/pages -d '{
  "parent": {"type": "data_source_id", "data_source_id": "'$DATA_SOURCE_ID'"},
  "properties": {
    "Title": {"title": [{"text": {"content": "New Task"}}]},
    "Status": {"status": {"name": "In Progress"}},
    "Due Date": {"date": {"start": "2026-07-12"}}
  },
  "markdown": "# Heading\n\nBody content."
}'
```

(`markdown` is mutually exclusive with `children`.)

### 4. Edit Page Content

```bash
ntn pages edit $PAGE_ID --content '# Updated body'   # full rewrite (also: stdin)
```

Targeted search-and-replace via the markdown endpoint (array key is `content_updates`, NOT `operations`):

```bash
ntn api v1/pages/$PAGE_ID/markdown -X PATCH -d '{
  "type": "update_content",
  "update_content": {"content_updates": [{"old_str": "find this", "new_str": "replace with this"}]}
}'
```

Full rewrite via raw HTTP (the reliable path for anything over a couple of KB - see gotcha 8). Note the payload key is `new_str`, NOT `markdown`:

```bash
curl -s -X PATCH "https://api.notion.com/v1/pages/$PAGE_ID/markdown" \
  -H "Authorization: Bearer $NOTION_API_TOKEN" -H "Notion-Version: 2026-03-11" \
  -H "Content-Type: application/json" \
  -d '{"type": "replace_content", "replace_content": {"new_str": "# New body\n\n..."}}'
```

To *append*, set `old_str` to a unique existing anchor (e.g. a heading) and include that anchor in `new_str`. Markdown tables render as native Notion tables. Avoid the block API (`/v1/blocks/{id}/children`) except for block types markdown can't express.

### 5. Update Page Properties

```bash
ntn api v1/pages/$PAGE_ID -X PATCH -d '{
  "properties": {"Status": {"status": {"name": "Complete"}}}
}'
```

### 6. Retrieve Data Source Schema

```bash
ntn api v1/data_sources/$DATA_SOURCE_ID
```

**Performance tip**: `filter_properties[]` returns only the properties you need - `POST /v1/data_sources/{id}/query?filter_properties[]=title&filter_properties[]=status`. Also works on the page create/update endpoints (trims the response, not the write).

### 7. Search

```bash
ntn api v1/search -d '{"query": "meeting notes", "filter": {"property": "object", "value": "page"}, "page_size": 20}'
```

### `ntn api` syntax notes

Method is inferred (GET default; POST when a body is present; `-X` wins). Besides `-d '<json>'` / `-d @file.json`, it supports httpie-style inline inputs: `page_size==100` (query param), `properties[foo]=bar` (body string), `archived:=true` (typed JSON).

## API Version Notes (2026-03-11)

`ntn` sends a current `Notion-Version` automatically (`--notion-version` to override). Still relevant when composing `ntn api` calls:

- Database query/schema endpoints live at `/v1/data_sources/` - the old `/v1/databases/*/query` endpoint is **DEAD** (returns 400). Use `data_source_id` everywhere.
- `archived` was replaced by `in_trash` in all requests/responses.
- Block append `after` param was replaced by a `position` object (`after_block`, `start`, `end`).
- The `transcription` block type was renamed to `meeting_notes`.
- Page content should be read/written via the **markdown endpoints** (`ntn pages get/edit`), not the block API.

## Property Types Quick Reference

```json
{
  "Title": {"title": [{"text": {"content": "Page title"}}]},
  "Text": {"rich_text": [{"text": {"content": "Rich text content"}}]},
  "Status": {"status": {"name": "In Progress"}},
  "Select": {"select": {"name": "Option A"}},
  "Multi-select": {"multi_select": [{"name": "Tag1"}, {"name": "Tag2"}]},
  "Date": {"date": {"start": "2026-03-25", "end": "2026-03-26"}},
  "URL": {"url": "https://example.com"},
  "Number": {"number": 42},
  "Checkbox": {"checkbox": true},
  "Relation": {"relation": [{"id": "related-page-id"}]}
}
```

## Filter Syntax

Filters passed to `--filter` / `ntn api` bodies are standard Notion filter JSON:

```json
{"property": "Status", "status": {"equals": "Done"}}
```

Compound:

```json
{
  "and": [
    {"property": "Status", "status": {"equals": "Done"}},
    {"property": "Priority", "select": {"equals": "High"}}
  ]
}
```

For anything long or nested, pipe it in with `--filter-file -` instead of fighting shell quoting:

```bash
ntn datasources query $DATA_SOURCE_ID --filter-file - <<'EOF'
{
  "and": [
    {"or": [
      {"property": "Title", "title": {"contains": "API"}},
      {"property": "Description", "rich_text": {"contains": "API"}}
    ]},
    {"property": "Status", "status": {"does_not_equal": "Archived"}},
    {"timestamp": "created_time", "created_time": {"on_or_after": "2025-01-01"}}
  ]
}
EOF
```

Full operator list: `ntn api v1/data_sources/{data_source_id}/query --docs`.

## Important Gotchas

1. **Data source ID ≠ database ID** - `ntn datasources resolve <database-id>` when unsure
2. **Pagination**: exhaust all pages via `--start-cursor` / `start_cursor`
3. **Rate limits**: 3 requests/second average (burst higher)
4. **Rich text**: limited to 2000 characters per rich_text array
5. **Trash**: use `in_trash`, not `archived`
6. **Empty strings**: use `null` instead of `""` to unset values
7. **The integration only sees connected pages** - missing pages usually mean a missing connection, not a bad query
8. **The CLI hangs on markdown bodies - creates AND edits.** `ntn api v1/pages` hangs on creates with a `markdown` body (observed 2026-08-11: >90s twice on ~3.5KB), and `ntn pages edit --content` hangs on full rewrites (observed 2026-09-01: >10min on ~15KB, never returned). The same payloads over raw HTTP finish in seconds. Send any markdown write beyond a couple of KB straight to the No-CLI curl form - and re-read the page before retrying, since a hung call may still have applied and a create would otherwise duplicate.
9. **⚠️ DATA-LOSS: schema PATCHes on select/multi_select** - updating a data-source property (even just its `description`) requires including the type key, and sending it EMPTY (`"multi_select": {}` / `"select": {}`) REPLACES the option list with nothing, wiping every option and stripping that property's values from ALL pages in the database (happened 2026-07-19; recovery required rewriting 133 pages, original option colors unrecoverable). Before any data-source PATCH touching a select/multi_select property, GET the current schema and resend the existing `options` array verbatim inside the type key. `status` properties are protected (empty `"status": {}` leaves options intact), and empty type keys are harmless for scalar types (`rich_text`, `url`, `number`, `date`).

## Error Handling

- `400`: bad request (check JSON - or a dead pre-2026 endpoint)
- `401`: unauthorized (bad/revoked token - see Authentication)
- `403`: forbidden (page not connected to the integration)
- `404`: not found
- `429`: rate limited (slow down)
- `500`: server error (retry with exponential backoff)

Add `-v` to any `ntn` command for full error chains; `ntn doctor` checks the setup.

## No-CLI Fallback (deployed environments)

Where `ntn` isn't installable (Modal, CI, Workers), hit the API directly - same bodies as above:

```bash
curl -s -X POST "https://api.notion.com/v1/data_sources/$DATA_SOURCE_ID/query" \
  -H "Authorization: Bearer $NOTION_API_TOKEN" \
  -H "Notion-Version: 2026-03-11" \
  -H "Content-Type: application/json" \
  -d '{"page_size": 100}'
```

## Self-Update

Run these steps with the user when the **Last updated** date at the top is more than 1 month old (or on request):

1. **Update the CLI**: `ntn update`, then skim `ntn --help` for new/changed commands and reconcile this file.
2. **Read the changelog** at https://developers.notion.com/page/changelog for changes since the Last updated date. Apply any endpoint/param/behavior changes to this SKILL.md.
3. **Verify auth still works**: `ntn api v1/users/me` with `NOTION_API_TOKEN` exported - if it fails, fix the 1Password reference in the Authentication section.
4. **Bump the Last updated date** at the top of this file to today.
6. Suggest also self-updating the `notion-workspace` skill if it's stale.
