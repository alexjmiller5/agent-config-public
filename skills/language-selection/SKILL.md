---
name: language-selection
description: Use when choosing a programming language or app stack, comparing Go, Rust, Zig or other languages, starting a new app whose stack is undecided, or proposing a language migration for an existing app. Do not use for routine changes within an established stack.
license: MIT
---

# Language selection

Choose for the product's workload, platform, reliability and maintenance.
An AI author's ability to write an unfamiliar language removes personal syntax
familiarity as a constraint; it does not remove integration or operational cost.

## Gates, in order

1. **Existing or new?** Keep an existing app's language unless a measured
   performance or concrete integration benefit justifies changing it. For a
   performance migration, set an end-to-end target, profile representative
   inputs and prefer replacing a hot component before a whole-app rewrite.
2. **Hard constraints.** Identify platform APIs, required libraries, hosting,
   signing, persistence and distribution. Consult the applicable deployment
   policy. A favorite language does not justify new hosting. Treat an
   unspecified host as unresolved before committing to a deployment plan.
3. **Resource targets.** State relevant startup, peak memory, throughput or
   latency targets. Separate CPU/allocation work from network/database/model
   waits. New apps may choose Rust prospectively for tight resource budgets or
   useful type/ownership guarantees; an existing incident is not required.
4. **Narrow the defaults.** Use the table below as a starting point, subordinate
   to hard constraints. Do not force one language across every layer.
5. **Prove uncertainty.** When two candidates differ materially, spike the
   difficult library, target deployment and resource budget. Record the chosen
   language, runner-up and reason in the project's AGENTS.md. Explain the
   recommendation during design; do not reopen a settled choice on every edit.

| Workload | First candidate | Switch when |
|---|---|---|
| Native Apple UI or Apple-bound integration | Swift | A measured/shared core justifies an additional language |
| Browser UI, extensions, thin API in an established web stack | TypeScript | A supported alternative has a specific integration or resource advantage |
| Ordinary portable service, sync tool, CLI or daemon | Go | Hosting/libraries or stronger ownership/invariant/resource requirements favor another language |
| Demanding native core, parser, tight memory/latency budget | Rust | Required interop, libraries or a measured spike favor a different implementation |
| ML/data libraries or Python-centric runtime integration | Python | The actual bottleneck and dependency path support moving a component |
| Specialized C-facing library or explicit allocator control | Evaluate Zig against Rust | Lifetime correctness, compiler/editor compatibility and the target build are proven |
| JVM/.NET/BEAM, shared mobile UI, scientific/GPU kernel requirements | Evaluate the matching ecosystem | A concrete platform/library/product need earns the extra runtime or toolchain |

A compile/typecheck pass is useful evidence, not proof of correct product
behavior. Verify external-input validation, tests, lint, realistic resource
behavior, packaging and the installed app. Do not promise a universal language
speed ranking or better AI coding success without measurements.

## Toolchains

Use the declared machine tools for common work and a pinned project development
environment for specialist compilers or different versions. Keep builds
reproducible and package installation declarative where the environment requires
it. A compiler's availability does not authorize changing the app's language.

For Go, use repository `just` verbs first; otherwise check formatting,
`go vet ./...`, `go test ./...`, `go test -race ./...` on supported targets,
and build/run the binary. Add representative benchmarks and native fuzzing when
useful. Inspect dependencies with `govulncheck`; the race detector only covers
executed paths. Disable automatic SDK/editor-tool downloads when Nix owns them.
Read [Go references](references/languages.md) for the relevant tool or language.
For Rust work, use the `rust` skill if available.

Credits: official language and platform documentation (constraints and tool
checks); Go's compatibility, GC and race-detector guides (maintenance and
runtime tradeoffs); Rust and Zig references (ownership and allocator choices).
