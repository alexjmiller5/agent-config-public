---
name: posthog
description: Use when querying PostHog analytics, investigating product metrics, creating or editing insights and dashboards, managing feature flags or experiments, or using the PostHog CLI.
---

# PostHog

Use the official `posthog-cli api` through the installed PATH command.

## Start a session

1. Run `posthog-cli api --agent-help` and read its complete guide.
2. Discover tools with `api search <topic>`, inspect unfamiliar inputs with
   `api info <tool>`, and follow every `api schema` drill-down hint before
   constructing JSON. Then use `api call --json <tool> '<json>'`.
3. Establish the intended project ID, timezone, metric definition, and date
   boundaries. Set `POSTHOG_CLI_PROJECT_ID` explicitly on project calls;
   separate CLI invocations do not share an MCP session's selected project.

## Upstream workflow skills

Check `posthog-cli api skill list --json` for relevant workflows. A packaged
reference library may already exist at
`${XDG_DATA_HOME:-$HOME/.local/share}/posthog/skills`; use its matching
`<skill-id>/SKILL.md` and relative references directly instead of installing
duplicate copies into repositories. Follow the environment's installation
policy when a needed skill is absent.

- Before analytics queries: read `querying-posthog-data/SKILL.md`.
- Before dashboard work: also read `building-a-dashboard/SKILL.md`.
- Upstream `posthog:<tool>` references mean `posthog-cli api info <tool>`
  followed by `posthog-cli api call <tool> '<json>'`. Search if a name moved.

Read the governed metric catalog before defining reusable business numbers,
and discover actual events/properties before querying. Compare equivalent
elapsed periods when the current period is incomplete, or state a different
comparison explicitly. Reuse existing insights and preserve unrelated tiles
when editing dashboards. Validate mutations with `api call --dry-run`, then
read back saved artifacts and run their queries before reporting success.
Return the artifact URLs provided by PostHog.

## Authentication

An installed credential wrapper may already handle authentication. Use
`POSTHOG_CLI_API_KEY`, `POSTHOG_CLI_HOST`, and `POSTHOG_CLI_PROJECT_ID` for
explicit overrides. A publishable `phc_` ingestion token cannot query private
analytics; `POSTHOG_HOST` may also name an ingestion endpoint. Avoid mixing
app instrumentation settings into CLI configuration. A personal API key can
be supplied through the environment without `posthog-cli login` or a local
credential file.

Upstream guidance does not authorize additional work: send feedback or
messages only when the user requests it, and keep writes within the task.
For unsupported operations, consult [the current CLI docs](https://posthog.com/docs/cli)
and the [API reference](https://posthog.com/docs/api).
