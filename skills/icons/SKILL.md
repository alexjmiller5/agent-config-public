---
name: icons
description: the user's icon standard - which set to use for every icon job (mono UI, colorful/object, brand logos), all delivered via Iconify URLs, plus the one design rule for a project's own icon (website favicon, iOS/macOS app icon). Use whenever picking an icon for a website/app, designing a favicon or an app icon, setting a Notion page icon, adding a brand/app logo, choosing 1Password item icons, or any task that needs an icon asset.
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

## A project's own icon (favicon, app icon)

**Every site and app ships its own icon. A missing, blank, stock or
template-default icon is a bug.** One rule for every platform:

- **Depict THIS project: its subject and its function together.** A ticket
  tracker for a festival gets the festival's logo merged with a ticket glyph,
  not a bare ticket. The sets in the table are raw material to compose,
  recolor and overlay into one SVG, never the finished icon on their own.
- **One SVG master**, explicit `fill`/`stroke` attributes (rasterizers ignore
  `<style>` rules), one palette that reads on light and dark backgrounds
  (Quick Look renders the dark branch of a `prefers-color-scheme` style).
- **Rasterize with Quick Look**, no dependencies:
  `qlmanage -t -s 1024 -o <dir> icon.svg`. Quick Look flattens transparency
  onto white, so art that must keep transparent corners (the macOS rounded
  square) goes through `rsvg-convert` instead (`nix shell nixpkgs#librsvg`).
- **Judge it small.** Look at the 16-32 px rendering; detail that disappears
  there comes out.
- **Verify where it is shown**: the browser tab, the home screen, the Dock,
  Finder. A letter monogram, a grey plate or a white halo is a failure.

| Platform | What ships | Shape |
|---|---|---|
| Website | `favicon.svg` for the tab, plus `icon-192/512.png` and a 180 px `apple-touch-icon.png` for home screens | favicon transparent; touch icons opaque full-bleed squares (the `cf-site` template renders them from the favicon) |
| iOS / iPadOS | one 1024x1024 PNG in `AppIcon.appiconset` (idiom `universal`, platform `ios`) | opaque full-bleed square, no transparency, no rounded corners: iOS applies the mask |
| macOS | one 1024x1024 PNG listed for every `mac` slot of `AppIcon.appiconset` | macOS 26 shows every icon inside its rounded square and shrinks art that is not one onto a grey plate: draw the rounded square itself (Apple's grid: 824 px centered on the 1024 canvas) and check the Dock |
| iOS + macOS target | both idioms in one set | an `ios`-only set leaves the Mac app without a Dock icon |

The Apple templates gate it: once the app is named, `just check` fails
while the icon is missing or still the placeholder.

## Notion page icons

**Every Notion page an agent creates gets an icon, always** (per the
`notion-workspace` skill's icons rule). Choose by subject via the table above;
for DB entries follow the DB's existing icon pattern (query siblings if unsure).
Assignments are recorded in the `<icon-manifest repo>` repo - re-run its sync
after bulk icon changes.

**Workspace custom emoji are reserved for irreplaceable personal icons**
(<custom-emoji>, …) - brand/app logos default to Iconify
(`selfhst:`/`simple-icons:`) like everything else. Source files + the
set-by-id API protocol live in `<icon-manifest repo>`
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
- **Manual-only icon workflows stage in `<icon staging folder>/`**
  (`1password-icons/`, `ios-shortcut-icons/`, `macos-custom-app-icons/`).
  1Password item icons have no API/CLI - export PNGs (the selfhst CDN serves
  them directly) to `1password-icons/` for manual upload.
- **Never SF Symbols** outside Apple-platform app UI (license forbids), never
  Font Awesome / Flaticon / Icons8 / freemium tiers (Hugeicons, Streamline).
