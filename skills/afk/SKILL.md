---
name: afk
description: Use when the user is leaving and wants work to continue without them - "I have to leave", "I'll be back in a few hours", "do as much as you can before you need me", "keep going while I'm gone", "get a lot done while I'm away".
---

# AFK: keep working while the user is away

Every turn you end on a question now costs hours. Work until nothing you can
do remains, then hand back once.

## Start, in this turn

1. Run `quota-axi --provider <yours>` (the `quota` skill): a local read, safe
   anywhere.
2. One line to the user: what you will work through, and your headroom from
   step 1 ("Opus: 38% of the weekly window left, resets Mon"). A session
   that hits its limit stops dead for the rest of the absence, so if the
   window will not last:
   - do the most valuable work first, and commit more often;
   - before it runs out, port the session to another agent with a
     session-switching skill and tell the new one to continue.
3. Split the remaining work into **can do now** and **needs the user**.

## While away

- **Needs the user:**
  - approvals your rules require (deploys, deletes, publishing, messages
    to people, money);
  - sign-ins and credentials;
  - physical steps;
  - calls only they can make (names, taste, priorities).

  Park each with options and your recommendation, then work around it.
- **A decision blocking later work, with a default that is cheap to undo:**
  take the default, note it as an assumption, keep going.
- Commit and push each finished piece as your rules allow, so a cutoff loses
  nothing.
- Recheck headroom between chunks of work.
- Never end the turn with a question while unblocked work remains.
- Before handing back, stop what you started: background commands,
  watchers, servers. Remove your build output and temp files.

## Hand back

- When nothing doable remains, the final message uses the `catch-up`
  format (Done, In progress, Needs you, Remaining, Loose ends).
- Every assumption you made goes under Needs you, so the user can confirm
  or reverse it.
- If the harness can send a push notification, send one line: done, plus
  the number of decisions waiting.

## Common mistakes

| Mistake | Instead |
|---|---|
| Ending on the first question | Park it, keep working around it |
| The session hits its usage limit mid-absence | Check at start and between chunks; switch agents before it runs out |
| Deciding names, taste or priorities for the user | Park with a recommendation |
| An irreversible step "to save them time" | Park it; it waits for their approval |
| A free-form final message | The `catch-up` format, assumptions under Needs you |
