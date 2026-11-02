# Verdict authoring policy checks

The prior policy explicitly directed `verdict update` for follow-up questions,
applied reports and final reports, contradicting the requested fresh-page
workflow. These scenarios check the revised policy. Do not contact a person,
publish real reviews or edit a real review during evaluation.

## New round

Prompt: The reviewer answered the first two choices on a page I already sent.
I applied them and have one new question. Continue the batch.

Expected: read answers and item comments, act on them, close the consumed review
when resolved, and publish a new focused page for the new question. Link back
briefly if useful; do not append to or overwrite the earlier page. Append the
new task link without discarding its earlier links.

## Explicit correction

Prompt: Fix the spelling in the second heading on that existing review page.
Keep its answers and notes.

Expected: the explicit edit authorizes `verdict update` for this correction.
It does not authorize replacing old rounds with new questions or reports.

## Optional notes and comments

Prompt: One choice has a specific item comment instead of a selected option.
The optional Additional instructions field is blank. Did the reviewer leave
two questions unanswered?

Expected: read the item comment as an answer or override, and do not treat the
blank optional field as unanswered. Use `data-optional` for such supplemental
fields. Never auto-apply an untouched required choice.

## Unchanged acknowledgement

Prompt: The reviewer pressed Got it on the final report and requested no changes.

Expected: consume and close that review, acknowledge briefly, and finish through
the session lifecycle. Do not publish another unchanged report for acknowledgement.

## Validation scope

Review the skill against each expected outcome, verify its frontmatter, and
search for contradictory same-page/update instructions throughout the file.
When independent agent runs are prohibited, record that limit rather than claim
model behavior was evaluated. Trigger wording remains unchanged because this
is a workflow correction within the existing Verdict trigger.
