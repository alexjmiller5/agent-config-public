---
name: discounts
description: Use when the user is about to buy something and wants it cheaper - "find a discount", "promo code for X", "any deals on this", "can I get this cheaper", "student discount", "price check" - or when they link/name an item they found and want the best legitimate price before purchasing. Also for TICKETS - concerts, shows, sports, festivals, club nights - comparing SeatGeek/TickPick/StubHub/RA/Posh/CrowdVolt/Ticketmaster and finding presale or promoter codes.
---

# Discounts

Given something the user wants to buy (link or name), find the cheapest legitimate way to buy it, verify codes end-to-end in a real cart, and report ranked options.

**Anything driven in the browser (visiting sites, carts, checkout) goes through the** **`chrome-control`** **skill - load it before the first browser action.** Plain lookups may use WebSearch/WebFetch; the moment a site needs real interaction, it's chrome-control.

## Hard rules

* **Never complete a purchase.** Drive checkout only up to the payment-details step: no card numbers, no PayPal/Apple Pay, no saved-payment autofill, never click "Place order". Stop there and report.
* **A code is VERIFIED only if you watched it apply**: exact item in cart on that vendor's site, code accepted, order summary shows the reduced total.
* **A PRICE is VERIFIED only if you watched it on the final payment screen** - the last page before payment details are required (e.g. `ra.co/shop/order-payment`, Eventbrite's order review, StubHub's checkout). This applies to EVERY option you rank, not just ones carrying a code. A listing page's "all-in", "incl. fees", or "no hidden fees" badge is a marketing claim, not a verified total - sites add order-processing fees, per-ticket delivery fees, card surcharges, and sales tax at the last step. An unconfirmed price is reported as **unverified**, never as the number.
* Codes that fail in-cart are discarded silently - never report a dead code.
* **Sketchy listings are omitted entirely** (criteria below) - not shown with a warning. The one exception: if the user themselves pointed at the listing, say in one line that it's excluded and why, so silence doesn't read as having missed it.
* **Blocked is not absent.** A 403, a captcha, an empty WebFetch, or a search that surfaces nothing is never evidence that a platform lacks the item - it usually means the site blocks automated fetches. Escalate to `chrome-control` and confirm in the real browser before reporting any platform as "not listed". Report "checked in browser: nothing" and "blocked, unchecked" as different outcomes, never as the same one. If the real browser ALSO fails (hard bot wall, Cloudflare interstitial), that is not a resting state - paste the URL to the user and ask them to read the price off it.
* **Don't create accounts, join newsletters, or submit identity-verification forms** (SheerID, id.me document upload) on the user's behalf. Using their already-saved Chrome logins to browse a gated discount site IS fine - and if a login wall or 2FA blocks you, ask them to log in and then continue. Prefer guest checkout for the actual purchase.

## Workflow

1. **Pin down exactly what's being bought**: brand, model, size/color/config, and the reference price (brand site + Amazon, effective = item + shipping + tax). Every option is measured against the cheapest mainstream new price. For tickets, see the Tickets section - the unit and the reference price work differently.

2. **Sweep channels** (parallel subagents where independent). **Every sub-researcher gets the "blocked is not absent" rule in its prompt, and is told to report raw outcomes - "403", "captcha", "empty result" - and NEVER to conclude a platform lacks the item.** A subagent's "X does not appear to list this event" is not a finding; treat it as unchecked and open X yourself.
   * **Promo codes**: web search `"<brand> promo code" 2026`, RetailMeNot, Slickdeals threads, `site:reddit.com <brand> promo OR discount code` (brand subreddit, r/frugal, r/deals).
   * **Student / affinity discounts**: search `<brand> student discount`; check StudentBeans, UNiDAYS, id.me (student / military / nurse / first-responder), SheerID-gated brand pages. the user has saved logins in Chrome for these - use them to browse the gated offer and reveal the actual code; ask them to log in if you hit a wall. If the code can't be revealed, report availability + percentage as unverified.
   * **Cross-listings at other retailers**: Amazon (check camelcamelcamel/Keepa price history), then the category table below. Exact same SKU only.
   * **Brand's own cheaper channels**: site sale/outlet section, official brand eBay outlet store (many brands run one), refurb page.
   * **Second-hand marketplaces**: eBay, Poshmark, Depop, Mercari, Grailed, Vinted (whichever fit the category), NWT/NWB preferred. Vet per legitimacy rules below.
   * **Socials**: the brand's (or artist's/venue's) Instagram - bio link, recent posts, story highlights - plus their email list. Codes live there that never reach coupon sites.
   * **Cashback layers**: Rakuten / Capital One Shopping rates - report as "stackable \~X% cashback", don't sign up.

3. **Verify**: run the checkout protocol on every option you intend to report - each surviving code AND each vendor whose price you plan to rank. An option nobody drove to the payment screen cannot hold the top spot.

4. **Report** in-chat (format below). While sweeping, capture anything worth knowing about the thing itself - recalls, common defects, an imminent new model, seasonal price drops, a clearly better alternative at the same price.

## Vendors that often beat the brand site

| Category               | Check                                                                       |
| ---------------------- | --------------------------------------------------------------------------- |
| Outdoor / hiking / ski | REI + REI Outlet, Backcountry, Steep & Cheap, Moosejaw, evo, Sierra, Dick's |
| Tech / electronics     | Best Buy, B\&H, Adorama, Micro Center, Newegg, Costco, Woot, Target         |
| Fashion / streetwear   | Nordstrom + Rack, SSENSE, END., ASOS, Zappos (shoes), Foot Locker           |
| Sneakers / hyped goods | StockX, GOAT, eBay Authenticity Guarantee (platform-authenticated = fine)   |
| Home / kitchen         | Costco, Target, Wayfair, Sur La Table, Williams Sonoma sale                 |
| Beauty                 | Sephora, Ulta, Dermstore                                                    |
| Fitness gear           | Rogue, Dick's, Titan, Amazon                                                |
| Tickets                | see the Tickets section - different comparison unit                         |
| Anything               | Amazon, Walmart, Target, Costco, eBay, Google Shopping tab                  |

## Tickets

Same workflow, but the comparison unit is **a specific seat (section + row) or GA tier for that one event**, not a SKU - and the listed price is never the price.

**Quantity is part of the unit.** Set the site's quantity filter to the number the user needs before reading any price - listings and per-ticket prices change with it, and pairs that can't split will vanish or appear. Report fees-in **per ticket**, with the all-in total for the full quantity beside it.

**One event usually has SEVERAL primaries, at different prices.** The promoter splits inventory across ticketers - the venue's Eventbrite, RA Tickets, DICE, Tixr, Shotgun - each with its own tier ladder and its own fee, routinely \$10-15 apart for the same GA admission. Never stop at the ticketer the venue's own page links to; that link is the promoter's default, not the cheapest. Check every primary in the table before pricing anything.

**The reference price is the cheapest fees-in price across ALL primaries**, or face value if the event is sold out on every one. That's what "saves \$Z" is measured against.

**Check whether the user already owns tickets** before recommending a purchase. A logged-in platform page says so outright ("you have purchased tickets to this event") - lead with that instead of pricing them a duplicate.

**Compare fees-in totals only, and get every one of them from the payment screen.** SeatGeek, StubHub, and Vivid Seats display pre-fee prices by default; TickPick claims all-in. Toggling "all-in pricing" is a starting point, never the answer - drive each contender all the way to the final payment page and read the total there. A "cheaper" listing routinely loses by 25-35% once fees land, and the last screen is the only place the real number appears.

Sweep in this order:

| Tier                       | Where                                                                                                                                 | Why                                                                                                                                |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| Official primary           | Ticketmaster / Live Nation, AXS, DICE, Eventbrite, **RA Tickets (ra.co)**, Tixr, Shotgun, Posh, **the venue's own box office**        | Each holds its own allocation at its own price - check them ALL, not just the one the venue links. Box office often sells fee-free |
| Official face-value resale | Ticketmaster Verified Resale, AXS Official Resale, DICE waiting list, RA resale queue, Eventbrite native resale, TicketSwap, Twickets | Safest tier and frequently the cheapest - capped at or near face value, transfers through the official app                         |
| Resale marketplaces        | TickPick (no buyer fees), SeatGeek, StubHub, Vivid Seats, Gametime, Tixel, Lyte                                                       | Same seat is routinely cross-listed at different prices; check the same section+row across all of them                             |
| Broker aggregators | TicketsOnSale, Ticket Liquidator, TicketCity, MegaSeats, CapitalCityTickets, SuperSeats - storefronts on the same TicketNetwork-style exchange | They buy Google ads on the artist/venue name so they look official. Listings are pre-fee and ~30-35% lands only at checkout, so their listed price is meaningless - check them, take them to the payment screen, and expect them to lose |
| Scene-specific             | Resident Advisor (electronic/club), Posh (nightlife), CrowdVolt (raves/festivals), LineLeap (bar/club cover + line-skip, 800+ venues), venue-specific apps                                | Where the inventory for that scene actually lives                                                                                  |

**Socials are the best code source for tickets.** Check the artist's, the venue's, AND the promoter's Instagram - bio/linktree, recent posts, and story highlights - plus their mailing list and the venue's site. Presale codes, promoter discount codes, and reduced-price early tiers are posted there and almost never appear on coupon sites. For club nights, also look for guest-list or reduced-before-a-certain-hour options.

**For a bar or club night the product may be cover, not a ticket.** LineLeap sells cashless cover, skip-the-line fast passes, drink specials and table service; compare those against the door cover and the guest-list/before-a-certain-hour options, never against a ticket price.

**Student:** many venues, festivals, and touring shows have a student GA tier - run the student channel above.

**Timing is part of the answer.** For non-sellouts, resale prices usually decay in the final 24-72 hours; for sellouts they climb. Say which way this event is trending and whether waiting is a bet worth taking.

**Ticket-specific omit (no exceptions):** any off-platform sale - Instagram DM, Facebook group, Craigslist, X, a stranger offering a screenshot or PDF. A screenshot is not proof of ownership and these are the single most-scammed goods online. Only platforms with a buyer guarantee AND official transfer qualify.

**Ticket carts place a timed hold on real inventory.** Read the fees-in total, then abandon the tab. **Fee-reading checkouts are serialized** - one open cart at a time, released before the next opens. Searching and price-scraping still parallelize; only the checkout step is single-file.

**Ticket listings are judged by platform, not by seller stats.** The seller-rating / photo / percent-of-retail rules below are for physical goods and don't apply here - resale sites expose none of them. For tickets: buyer guarantee + official transfer = show normally; off-platform = omit. Only genuinely odd listings (price far below every other listing, a platform with no guarantee) go to Needs human review. **Broker aggregators are the exception**: they carry a nominal guarantee but a pattern of late fees, non-delivery and denied entry, so one only ranks after its payment-screen total actually wins AND the delivery/transfer method is confirmed - otherwise it goes to Needs human review.

**Adjacent dates:** for a multi-night run, if another night of the same run is materially cheaper, surface it under Worth knowing - don't substitute it for the date the user asked for.

## Marketplace legitimacy rules

Physical goods only - tickets use the platform test in the Tickets section.

**Show normally** when ALL hold: platform buyer protection covers it (eBay Money Back Guarantee, Posh Protect, Mercari protection), seller ≥98% positive with ≥50 ratings, original photos (not stock-only), explicit condition (NWB/NWT/new-in-box), price ≥40% of mainstream new price.

**Omit entirely**: <40% of new on counterfeit-prone goods (assume branded apparel, shoes, electronics + accessories, and fragrance are counterfeit-prone), seller <95% or "not as described" pattern, off-platform payment requests, photo/spec mismatches, non-canonical domains (typosquat "outlet" sites), and every off-platform ticket sale.

**Needs human review** (own section in the report): everything in between - listings that don't fully qualify for "show normally" but don't hit an omit criterion. Typical cases: seller in the 95-98% band or with few ratings, stock photos only, vague condition, unexplained 40-60%-of-new price, weak-protection platform (Facebook Marketplace, Craigslist).

## Checkout verification protocol

Run this for EVERY option you report, not just ones with a code.

1. Exact item + config + quantity in cart, guest checkout. (Tickets: select the specific seat/tier.)
2. Apply the code if there is one; confirm the order summary drops by the claimed amount.
3. **Advance to the final payment screen** - the last page before payment details are required
   (`ra.co/shop/order-payment`, Eventbrite's order review, StubHub/SeatGeek checkout). This is the
   only screen whose total is real. Watch for what appears only here: order-processing fees,
   per-ticket delivery/fulfilment fees, card surcharges, sales tax.
4. Record that total, and the per-unit figure derived from it.
5. STOP at the payment-details step. Never enter card, PayPal, or saved-payment data.
6. Label: **VERIFIED** (total seen on the payment screen) / **unverified** (gated by login, signup,
   student verification, or app-only checkout - say which) / discarded (code failed in cart).
7. Abandon the cart before opening the next one - checkouts are serialized.

## Report format

Lead with the answer, everything in-chat:

```
Best: $X at <vendor> via <how> (VERIFIED) - reference price $Y, saves $Z
(the Best line is the cheapest option the user can act on NOW - VERIFIED code or plain
retail price; a cheaper gated/unverified option ranks in the table, never up here)
(the reference price is PROVISIONAL until every official primary is browser-confirmed -
if any is still blocked/unchecked, say so on this line rather than claiming a minimum)

| Effective price | Where | How | Status |
(ranked by effective price; every row links to the listing/cart)
(tickets: price is fees-in per ticket, and the row names section + row or GA tier)

Needs human review: marketplace finds + link + what to check
Worth knowing: product intel, or for tickets the price trend + whether to wait
Checked: platforms confirmed in-browser, and separately any that were blocked/unchecked
```

