---
name: scout
description: Use when the user wants to deeply understand a technology space, industry, tool category, or API type - "scout X", "what's the best X for...", "how does the X industry/space work", "compare the options for X", "help me pick a Y", or a task about researching/looking into a technology. Also use before committing to a tool, library, or service in an unfamiliar landscape.
---

# Scout

Produce a decision-grade landscape briefing on an industry / technology / tool category / API type: how the space works, how it got here, who the contenders are, and what the user specifically should use. Saved to Notion so the research is reusable.

## Process

1. **Scope** - only if the ask is vague, ask up to 3 questions: what decision is at stake, hard constraints, what it must integrate with. If the topic is already specific, skip.
2. **User context** - pull stack preferences from the global AGENTS.md and any stack/infra/project skills your setup provides. The "for the user" sections are filtered through these.
3. **Research** - run the research engine (section below). On Claude Code that's one call: `Workflow({ name: "deep-research", args: "<refined question + lenses>" })` - its built-in workflow implements exactly the engine's phases. Never invoke it as a *skill* (`Skill(deep-research)` is user-invocation-only and errors for the model). On any other agent, or if the named workflow doesn't resolve, execute the engine's phases directly. Structure the question as distinct **opinionated lenses**, each carrying the user's use case and the instruction *"be opinionated rather than encyclopedic"*. Default lenses (adapt to topic):
   - Established/mainstream solutions and their honest tradeoffs
   - Emerging/upstart solutions - what's genuinely new vs. hype
   - Adjacent-or-avoid - existing projects to steal from, and alternatives that eliminate the need entirely (the Teller.io-instead-of-scraping class of find)

   **Quick mode** (`/scout quick <topic>`): skip the deep-research workflow. Research the same lenses yourself with inline WebSearch/WebFetch (a few searches per lens; verify maintenance dates on anything you'd recommend). No adversarial verification - claims are single-sourced.
4. **Deliver** - write the briefing (structure below) to a **Notion notes page** if your setup has one (see the `notion-workspace` skill where available; otherwise a local markdown file), titled `Scout: <topic>`, dated in the body (landscapes rot - a reader must see how stale it is). Quick-mode briefings add to that dated header line: *"Quick run - single-sourced, no verification pass; re-scout in full before committing."* Link it to the originating task/project relation when there is one. End with the Notion link + TL;DR in chat.

## Research engine

The phases the deep-research workflow already implements, for agents that have
to run them by hand (parallelize with whatever the harness offers; sequential
is fine, just slower): **scope** (~5 complementary search angles from the
lenses, including a practitioner/DIY one) → **search** (one pass per angle) →
**fetch** (~15 deduped sources, extracting falsifiable claims with a verbatim
quote, source quality, and date; primary sources for any maintenance/pricing
claim) → **verify** (3 independent adversarial refute-attempts per top claim;
≥2/3 refutes kills it) → **synthesize** (findings ranked by confidence with
sources and votes, caveats, open questions - claims that died in verification
get said out loud, not silently dropped).

## Briefing structure

Every briefing has exactly these sections:

- **TL;DR verdict** - the answer in ≤3 sentences.
- **How this space works** - the problem it solves and the mechanics under the hood.
- **History & eras** - old solutions, what replaced what and why; the forces that made the landscape what it is (standards, incumbents, business models, platform shifts).
- **Contenders** - comparison table (approach, maturity, license/pricing, ecosystem, when to pick it) + a short **"my read"** verdict. If a call is genuinely close, say so in one line and resolve it with the user's context - no dedicated pro/con ritual.
- **Ecosystem gems** - existing projects worth stealing architecture from, adjacent tools, "you might not need this at all" alternatives.
- **Recommended stack for the user** - concrete setup (a config block, not just a winner's name) filtered through their stack + infra paradigm, with fallbacks and when they'd win instead.
- **Hard skips** - tools that are dead, deprecated, or wrong for the user, each with the reason (abandonment date, deprecated-by-author, threat-model mismatch...).
- **Watchlist** - what could change the answer, and roughly when to re-scout.
- **Sources** - cited, from the engine's verification pass (quick mode: the URLs actually read).

## Common mistakes

- Encyclopedic neutrality - every section should push toward the decision, not survey for survey's sake.
- Skipping history - "why is it like this" is half the value; the modern table alone is a listicle.
- Research-process residue in the output - agent/lens mechanics never appear in the briefing.
- Recommending against the user's stack without flagging the conflict explicitly.
