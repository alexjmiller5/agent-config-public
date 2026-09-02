---
name: icons
description: the user's icon standard - which set to use for every icon job (mono UI, colorful/object, brand logos), all delivered via Iconify URLs. Use whenever picking an icon for a website/app, setting a Notion page icon, adding a brand/app logo, choosing 1Password item icons, or any task that needs an icon asset.
---

# Icon Standard

One delivery layer, one set per job - never pick outside this table without
asking.

## The table

| Job | Set (Iconify prefix) | License | Notes |
|---|---|---|---|
| Mono UI icons (websites, apps) | **Tabler** (`tabler:`) | MIT | `@tabler/icons-svelte` in Svelte. Same 24px/2px language as Lucide → shadcn-svelte's internal Lucide icons and existing Lucide imports stay, no migration |
| Colorful icons (Notion page icons: foods, places, things) | **Noto Emoji** (`noto:`) | Apache 2.0 | Emoji-as-SVG. For concepts Noto lacks, nearest-match WITHIN Noto (kimchi → pot-of-food, tofu → beans) - the user dislikes mono/tinted silhouettes on Notion pages, so game-icons is not used |
| Brand/app logos, color | **selfh.st icons** (`selfhst:`) | varies (logos are trademarks) | Biggest coverage (~7k), dark/light variants; its own CDN serves PNG for manual uploads |
| Brand logos, mono/tinted | **Simple Icons** (`simple-icons:`) | CC0 | One tintable path per brand |

## Delivery - always Iconify

```
https://api.iconify.design/{prefix}:{name}.svg?color=%23{hex}
```

- Browse/search all sets at once: **icones.js.org** (slug shown is the
  `prefix:name` to use). Programmatic search:
  `https://api.iconify.design/search?query=X&prefixes=tabler,noto,selfhst`
- In web projects, use the npm package (`@tabler/icons-svelte`), not hotlinks.
- Hotlinked icons (Notion etc.): if api.iconify.design ever flakes, mirror the
  used SVGs to an R2 bucket at stable paths - same slugs, new host.

## Notion page icons

**Every Notion page an agent creates gets an icon, always** (per the
`notion-workspace` skill's icons rule). Choose by subject via the table above;
for DB entries follow the DB's existing icon pattern (query siblings if unsure).
Assignments are recorded in the `notion-icon-manifest` repo - re-run its sync
after bulk icon changes.

**Workspace custom emoji are reserved for irreplaceable personal icons**
(karls-face, openclaw, …) - brand/app logos default to Iconify
(`selfhst:`/`simple-icons:`) like everything else. Source files + the
set-by-id API protocol live in `notion-icon-manifest`
(`assets/notion-custom-emojis/` + README).

Set via API as external URLs:

```json
{"icon": {"type": "external", "external": {"url": "https://api.iconify.design/noto:broccoli.svg"}}}
```

- Notion's own built-in icons are also URL-addressable -
  `https://www.notion.so/icons/{name}_{color}.svg` - fine for system/DB pages
  that should feel Notion-native.
- Existing emoji icons on pages are fine; don't churn them.

## Gotchas

- **No mono/tinted silhouettes as Notion page icons** (game-icons etc.) - the
  flat one-color look clashes with Noto. If a set with CC BY licensing ever IS
  used on a published site, it needs attribution.
- **Manual-only icon workflows stage in `~/Documents/icons/`**
  (`1password-icons/`, `ios-shortcut-icons/`, `macos-custom-app-icons/`).
  1Password item icons have no API/CLI - export PNGs (the selfhst CDN serves
  them directly) to `1password-icons/` for manual upload.
- **Never SF Symbols** outside Apple-platform app UI (license forbids), never
  Font Awesome / Flaticon / Icons8 / freemium tiers (Hugeicons, Streamline).
