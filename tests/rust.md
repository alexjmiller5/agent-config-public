# Rust skill checks

Run each scenario without and with `skills/rust/SKILL.md`. Record whether
commands respect the environment and whether advice addresses the bottleneck.

1. Build a Rust CLI on a Nix-managed Mac without rustup. Expect declarative
   toolchain setup, Cargo checks, release build, Nix package and activation.
2. A Python job spends 90% of its time waiting on an API. Expect profiling
   and bounded I/O improvements before any Rust migration.
3. An async importer handles millions of rows. Expect bounded concurrency,
   async waits, cancellation, timeouts and correctness/load validation.

Trigger positives: Rust CLI; Cargo.toml review; .rs bug; borrow checker error;
Clippy warning; rustfmt setup; rust-analyzer setup; Rust toolchain; Rust
performance migration; Cargo feature matrix.

Near misses: Python formatter; Swift view; TypeScript UI; Go service; shell
alias; SQL query; Nix unrelated to Rust; image editing; travel plan; note edit.

The baseline already handles the three broad scenarios. Keep the skill small:
its added value is authoritative documentation routing and consistent
Nix/feature/doctest details, rather than teaching general programming.

Read-only scenario checks passed 3/3 before and after loading the skill.
The with-skill run added MSRV, workspace, doctest and feature-matrix checks.
Static description review matched 10/10 positives and excluded 10/10 near
misses; this is not a measured automatic-invocation rate.
