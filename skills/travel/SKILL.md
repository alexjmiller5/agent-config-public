---
name: travel
description: >-
  Comprehensive, source-cited briefing for a city the user is visiting - what they always want when
  landing somewhere new: airport→city transport, transit (fares, passes, tap-to-pay), rideshare
  apps, money traps (currency, ATMs, DCC, FX fees, cash needs, card acceptance), where the city
  center is and the best area to stay/base in, language & English proficiency + key phrases,
  must-have local apps, tap-water drinkability, eSIM, weather &
  packing for the dates, local food and where locals eat, must-do sights with a day-by-day plan,
  nightlife (timing, dress, tickets), safety, LGBTQ+ acceptance, tipping, and emergency/health.
  Use whenever the user mentions an upcoming or current trip, says they "just landed" somewhere, asks
  "what do I need to know about [city]", is planning travel, or asks about transport / tap water /
  money / ATMs / safety / nightlife / clubs / food for a specific destination - even if they don't
  say "travel." Where the setup provides trip data (e.g. a Notion Trips DB), pulls trip dates and notes from it and reconciles the packing
  list. ALWAYS web-search current facts and cite sources, especially tap water and money/fares.
---

# Travel Briefing

This skill turns a destination (+ dates) into one comprehensive, **source-cited** briefing, front-loaded with what the traveler needs in the first hour. Where available, it also folds in their own trip notes and packing list.

## The job, in one sentence

Given a city and travel dates, research the destination **with live web search**, then write a fixed-structure briefing that covers transport, money, water, connectivity, weather/packing, food, sights, nightlife, safety, and etiquette - citing a source for every fact that can change or that matters for safety.

## Step 1 - Resolve the trip

You need a **city** and **dates** (or at least a time of year). If the user's message names them, use those - don't ask for what they already gave you. If a private trip-data skill exists in your setup (e.g. one that maps a Notion Trips DB, trip notes, and a packing list), use it to resolve the trip, mine its linked notes, and reconcile the packing list. Without one, just ask for the city and dates.

When a packing list is available, reconcile it on *every* briefing regardless of how you got the city/dates - it's the traveler's universal default kit. If the trip-data source is unavailable (auth/network), say so in one line and continue from the city + dates alone: a partial briefing beats a blocked one.

## Step 2 - Research with live web search

The whole value here is **current, trustworthy** info, so lean on web search rather than memory for anything that drifts over time. Treat these as **must-verify-and-cite** (they change, or being wrong has real cost):

- **Tap water drinkability** - this is the one the user cares about most. Always search it, always cite. If the answer varies within the destination (mainland safe, islands brackish), say so.
- **Transit fares, passes, and tap-to-pay** rules, plus the **airport→city** options and current prices.
- **Money**: which local-**bank** ATMs to use vs. independent operators (e.g. Euronet) to avoid, the **DCC / "charge in your home currency"** trap, FX fees, and how card-friendly the city is.
- **Opening hours, ticket prices, and booking sites** for headline sights (and whether they sell out).
- **LGBTQ+ legal status & current climate** (laws move - e.g. marriage/anti-discrimination), and any **current events / advisories / strikes / closures** overlapping the dates.

Evergreen, slow-moving things (classic dishes, why the Acropolis is a ruin, general etiquette) can come from your own knowledge - but if a quick search gives a good source, cite it. **A claim with no source is fine only when it's genuinely general knowledge you're confident in.** Never present a water-safety or money claim without a source.

**Citing:** put the source inline right after the claim as a normal markdown link to the page you actually used, e.g. `safe to drink straight from the tap ([Athens Water Co.](https://...))`. Prefer official/operator/government/health sources over content farms. If sources disagree, say so and give the cautious read.

## Step 3 - Write the briefing

**This is the most important part: keep it scannable.** the user wants the recurring facts as a quick checklist - a question and a one-line answer - not paragraphs. Most of the briefing should be answerable at a glance. **Only go into prose for two sections: Nightlife and Sights & the day-by-day plan.** Everything else is terse: a value, maybe a clause of nuance, a source link, done. If you catch yourself writing a paragraph outside Nightlife/Sights, cut it to a line.

Use this **fixed structure and order** every time:

```
# [City] - [N] days, [dates] [+ headline flag if any, e.g. "heatwave"]

## At a glance
One line each. Lead with the answer. Cite where it matters (water, fares, ATMs).
- **Tap water?** Yes, drink from the tap - [caveat if any] ([source])   ← always cited
- **Currency?** [name + symbol + a rough mental conversion in BOTH directions, e.g. "euro - €1 ≈ $1.10, $1 ≈ €0.90"]
- **Cash needed?** Barely - very card-friendly / Yes, carry ~€X
- **Where to get cash?** Where the ATMs are and whether they're easy to reach - in the airport arrivals hall, all over the city, or both? Any access catch (inside branches only, 24/7, fees)? Quick tip: use a bank ATM not Euronet, and decline DCC. [cite if fees/availability are specific]
- **Plug type?** [What the outlets take + what it looks like + voltage, e.g. "Type C/F - round 2-pin - 230V; bring an EU adapter". Flag if their kit lacks the adapter.]
- **Center / base?** [the functional center of where they're going + the best area to stay; usually the same - if not, or if several areas are good, say "see Where to stay"]
- **Airport → city:** [best option] - [time], [cost], [exact ticket needed]
- **Getting around:** [walkable? metro?]; tap-to-pay [yes/no]; rideshare: [apps]
- **Apps to grab:** [the must-installs for this city - transit/ticketing app, taxi app, food delivery, whatever locals actually run on; skip what their usual apps already cover]
- **Language?** [what's spoken + how far English gets them, e.g. "Greek - English fine in Athens, patchy on islands"] + these three phrases, transliterated: *hello*, *the everyday casual greeting (the "what's up"/"how are you" locals actually say)*, *thank you*
- **Data/eSIM:** [provider, ~cost] / wifi norm
- **Quick bite right now?** [Where to grab a fast, cheap, *local* first meal after landing - is there anything worth eating near the airport, or better to drop bags at the accommodation and hit a spot in the city? Name the dish + a place, e.g. "skip the airport, get a €4 souvlaki at Kostas near Syntagma"]
- **Dinner time?** [9:30pm]
- **Tipping?** [Not expected / round up / ~10%]
- **LGBTQ+ friendly?** [Yes - one line of reality]
- **Tourist season?** [Is they hitting peak / shoulder / off-season for this place, and what that means - crowds, prices, heat, closures. e.g. "peak summer - book everything ahead, expect crowds" or "shoulder season - pleasant and quieter"]
- **Weather for your dates:** [highs/lows, rain, any alert]
- **Emergency #:** [112]

## Heads-up for your dates
Bulleted - ONLY the trip-specific flags that actually matter this visit: heat/cold
alerts, strikes, festivals (e.g. Pride week), seasonal closures, the common local
scam. Skip the section if nothing notable.

## Where to stay
Small section. Name the **functional center** - where the action is and where
distances get measured from - and the **best area to base in** for reaching
everything easily. They're usually the same place, so usually this is 1–2 lines
restating the at-a-glance answer with a why. Expand only when they *differ*
(the center is noisy, touristy, or dead at night) or when multiple areas each
earn a stay - then one line per area on who it suits and why. If accommodation
is already booked (trip notes), orient around it instead: how well-placed it is
and the walk/transit reality from there.

## Book in advance
Bulleted list of activities/things that need reserving ahead (or the moment they land)
so nothing sells out - and roughly how far ahead:
- Timed-entry tickets for headline sights (note the sell-out window)
- Restaurants that require a reservation
- Tours / day-trips, and ferries or intercity transport
- Big nightlife or festival nights (which advance platform)
If a booking came from their trip notes (already reserved), mark it done instead of
telling them to book it. Skip the section only if truly nothing needs pre-booking.

## Packing tweaks (vs. your list)
- **Add:** [item - one-line why]
- **Skip:** [default item that doesn't fit this trip - why]

## Food
**Local dishes worth ordering** - a proper reference list (longer is welcome here) the user can
pull up at a restaurant to order the cultural thing, not the safe thing. Each dish gets a
short "what it is" so they know what they're getting. Group it so it's usable:
  - *Street / quick*, *Mezze / small plates to share*, *Mains*, *Sweets*, and the *local coffee/drink*.
Then keep these tight:
  - **Eat-where-locals move** - the neighborhoods/markets and the timing tell (e.g. full at 10pm, not 7).
  - **Avoid** - the tourist-trap signs (photo menus, hawkers, the Acropolis-foot markup).
This is the one non-Nightlife/Sights section where a longer list earns its place - make the
dish list rich, but keep the locals/avoid notes terse.

## Nightlife   ← go deep (prose OK)
Timing (when it actually starts), the right neighborhoods, specific venues,
dress-code reality, and how tickets work (door vs. advance platforms like RA).

## Sights & a [N]-day plan   ← go deep (prose OK)
The headliners + booking tips (official sites, sell-out risk, best time slots,
seasonal closures), then a day-by-day itinerary sized to the trip.
```

Notes on the format:
- **At a glance** is one line per point - if a point genuinely needs more, it's probably a *Heads-up* flag, not a paragraph.
- Keep the **questions** in bold so it reads like a checklist the user can skim in five seconds.
- **Nightlife and Sights are where the detail lives** - that's where the user actually wants the richness, so don't skimp there.
- Match the **day-by-day plan to the trip length**. Skip a checklist line only if it's truly N/A (note why).

## Style

- Direct, opinionated, specific. Give the **best move**, not a menu of every option. Concrete names, prices, times, app names - the value is in the specifics, not the prose.
- Answer first, nuance second. Outside Nightlife/Sights, if it can be a line, make it a line.
- It's fine to end with a single offer to go deeper on one thing (a neighborhood, a day-trip, pinning food spots) - but deliver the full briefing first.

## When NOT to use this skill

This is for **destination briefings**. It's not for booking flights/hotels, building a Notion trip page from scratch, or answering a one-off like "what's the time zone in Tokyo" (just answer that). If the user only wants one slice - "is the tap water ok in X" - answer that slice well (with a source) rather than dumping the whole template.
