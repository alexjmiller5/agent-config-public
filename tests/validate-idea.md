# validate-idea evaluations

Run each scenario in a fresh context with the skill; compare with the previous
version in a separate fresh context. Controlled runs below prohibit network
access, so they test analysis behavior, honesty and output structure, not current
factual research. A live research pass separately verifies sources and prices.
Never contact people or publish during these evaluations.

## Scenarios

### commercial

Prompt: Criticize my AI proposal checker for small architecture firms. I cannot answer customer questions yet; research for me. Who pays and how do I sell it?

Checks:

- Proceeds with labeled hypotheses instead of stalling on researchable questions;
  in a live run, actually researches those questions
- Sales/distribution appears before technical scope
- Separates user and economic buyer
- Concrete initial niche, first ten buyers channel, offer and sales step
- Labels price/acquisition/support figures as assumptions with ranges
- Uncertainty does not become negative evidence; no invented revenue
- Cheapest behavioral test with denominator and decision threshold

### portfolio

Prompt: Review three ideas: a personal offline photo sorter, paid cafe shift-swap app, and AI meeting notes. Rank where I should spend a weekend, be blunt.

Checks:

- Separates own-use and hobby value from commercial value
- Checks built-ins, direct competitors and current workaround
- Portfolio table covers each idea with bottleneck and next test
- Orders by likely goal and validates uncertainty rather than arbitrary scores
- No automatic rejection merely because alternatives exist
- No invented private revenue from popularity or absent data

Shared checks: current competitor facts remain unverified without network;
unknown commercial viability receives Investigate, not Build as hobby unless
actual personal learning/enjoyment is established. No arbitrary numeric ratings.
Sales appears before feasibility. Proposed economics explicitly label their
assumptions; contribution includes support. No experiment is executed.

## Trigger checks

Give a fresh classifier only the name/description and each query. Ask whether
the skill should be read. Compare actual decisions against these labels.
These are semantic checks, not a claim about automatic harness invocation.

| Expected | Query |
| --- | --- |
| Read | Is this worth building: a tool that checks supplier invoices before payment? |
| Read | Criticize my idea for a neighborhood tool-lending marketplace. |
| Read | Go through this Ideas database and tell me which deserve a weekend. |
| Read | Does an offline photo sorter already exist and would mine be worthwhile? |
| Read | Would small studios pay for automated project handover checklists? |
| Read | Validate my AI proposal checker, especially selling it. |
| Read | Research competitors and monetization for my queue-management app idea. |
| Read | I cannot answer the customer questions yet. Figure out whether my app concept makes sense. |
| Read | How would I get the first ten customers for this unvalidated cafe scheduling idea? |
| Read | Is my side project worth doing just for fun even if there is no market? |
| Skip | Compare SQLite and Postgres for the app we have already decided to build. |
| Skip | Fix the failing invoice parser test in this existing app. |
| Skip | Rewrite this launch email for our already profitable scheduling product. |
| Skip | List the current features and prices of three vector database APIs. |
| Skip | Implement the checkout page from this approved design. |
| Skip | Summarize customer interviews without making a product recommendation. |
| Skip | Find a discount code for the photo software I am buying. |
| Skip | Check the compliance claims on our current legal page. |
| Skip | Debug why our meeting recorder cannot access the microphone. |
| Skip | Calculate last month’s customer acquisition cost from this CSV. |

## Channel selection and expansion

Use the same no-network conditions as above. These prompts are fictional. Read
the main skill and any reference it requests. Score actual answers, not a promise
to follow the checklist.

### consumer-channels

Prompt: Criticize this idea and choose how to sell it before I build: a subscription puzzle app for Spanish-speaking adults. I have $300 and six hours a week, no audience, and want $1,000 monthly profit eventually. I could cram App Store keywords, use popular movie clips and AI UGC, give free access for ten friends signing up, copy a successful creator, or pay a niche creator a revenue share. Maybe long-tail SEO or subreddit ads? Compare applicability, cheapest tests and core metrics, then pick one primary channel. I need speed, not a guaranteed viral plan.

### b2b-channels

Prompt: Validate a small subscription tool that turns approved inspection records into client handover packs for independent contractors. I have one friendly buyer, can spend five hours a week and $200, and want a self-funded business. Compare founder outreach, partners/affiliates, paid search, build-in-public, a free mini-tool for SEO, Product Hunt/Hacker News, and a lifetime-deal marketplace. Pick a realistic first ten customers path and pricing test. Could I land one team then expand? How do I judge recurring revenue versus actual retained profit before making another app?

Checks:

- Uses the distribution reference and selects one primary channel fitted to
  buyer access, weekly capacity, cash and time to revenue.
- For credible alternatives states applicability, a bounded cheap test, core
  conversion/retention metric and principal pitfall; explicitly defers poor fits.
- Treats views, keywords, trends, language niches and signups as hypotheses,
  not guaranteed demand; uses original/licensed media and truthful endorsements.
- Creator proposal accounts for audience fit, attribution, revenue share,
  refund basis, rights and disclosure; no outreach is executed.
- Referral proposal measures incremental activated/retained users, not email
  verification alone; caps rewards, fraud and resulting contribution risk.
- Backsolves a stated profit goal using contribution, relevant commissions and
  founder workload; does not confuse MRR, cash and retained profit.
- Matches subscription versus outcome/usage pricing to demonstrated frequency.
- For expansion, tests paid adjacency/champion/budget and states NRR's existing
  cohort basis, exclusion of new customers and distinction from customer retention
  and profit. Does not compute NRR when starting recurring revenue is zero.
- Proposes reversible capped experiments while preserving security/privacy;
  proves one acquisition-to-retained-value loop before multiplying products.
- Separates recruitment/setup from the full repeat-use or billing observation
  window; does not promise renewal evidence before it can exist.
- Keeps unavailable current platform rules, prices and competitor facts unknown.

Live-run extension: for a new idea with no channel suggestions in the prompt,
scan the reference before choosing channels. Verify any relied-on platform rules,
fees, audience and search claims against current primary sources. Do not copy
personal source notes into the public evaluation corpus.

## Feature parity and existing paid demand

These fictional supplied facts are verified inputs within the test; do not browse
or invent competitor results. Run old and revised skill in separate fresh contexts.

### parity-paid

Prompt: Evaluate a feature-parity subscription receipt organizer for freelancers. Treat these fictional facts as verified test inputs: two rivals have independently verified recurring paying customers; our eight-week manual pilot has 25 unrelated paying customers, 22 renewals, $12 monthly contribution per active customer after all support and fees, and $18 acquisition cost including founder labor through a small creator partnership. The automation is straightforward and we have appropriate data rights. Customers like the ordinary product and clear demos; there is no novel feature, technical moat or underserved niche. Should we automate the proven workflow, or must we find unique differentiation first? Keep under 300 words.

### parity-interest

Prompt: I want to launch an ordinary paid study-timer app with roughly the same features as existing apps. Rivals exist and publish prices, but their revenue is not disclosed. I have original short-video hooks that earned 40,000 views and 80 waitlist signups, access to a relevant creator, but no payment test yet. I want a small self-funded business, not a category winner. Assess whether competition helps validate it, whether good marketing could make it viable at feature parity, and the next test. Do not invent rival revenue or insist on a unique technical feature. Keep under 300 words.

Checks:

- Paid case permits Build/automation without demanding a unique technical
  feature, unserved niche or moat; marketing/reach and paid unit economics suffice.
- Treats verified rival paying customers as positive demand evidence, separate
  from the entrant's own conversion and retention evidence.
- Preserves distinction between verified revenue/payments and mere competitor
  existence, listed prices or unsupported revenue estimates.
- Interest-only case accepts feature parity as a viable hypothesis but tests
  payment; views and signups are not presented as purchases or retention.
- Uses supplied economics accurately: $18 acquisition / $12 monthly contribution
  is 1.5 active customer-months; no fabricated TAM or lifetime value.
- Offers a concrete acquisition/payment or renewal test rather than requiring
  technical invention or a fundamentally different product.
