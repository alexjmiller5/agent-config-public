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
