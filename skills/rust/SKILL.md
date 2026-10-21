---
name: rust
description: Use when writing, reviewing, debugging or profiling Rust code, touching Cargo.toml or .rs files, configuring a Rust toolchain, or assessing a Rust performance migration.
license: MIT
---

# Rust

## Read the authoritative source for the problem

Read the relevant chapter before relying on version-sensitive details:

- [The Rust Book](https://doc.rust-lang.org/book/): ownership, borrowing,
  traits, lifetimes, errors, concurrency and testing.
- [The Cargo Book](https://doc.rust-lang.org/cargo/): manifests, workspaces,
  features, lockfiles, build profiles and dependency resolution.
- [Rust Reference](https://doc.rust-lang.org/reference/): precise language rules.
- [Standard library](https://doc.rust-lang.org/std/): APIs and guarantees.
- [Edition Guide](https://doc.rust-lang.org/edition-guide/): edition changes.
- [Clippy](https://doc.rust-lang.org/clippy/): lint meanings and configuration.
- [rust-analyzer](https://rust-analyzer.github.io/book/): editor integration.
- [Tokio tutorial](https://tokio.rs/tokio/tutorial): async tasks and channels.
- [Rustonomicon](https://doc.rust-lang.org/nomicon/): consult when unsafe or FFI
  is necessary; document invariants and prove the safe alternative insufficient.

## Toolchain and verification

Respect the repository's edition, MSRV and toolchain pin. For new crates,
choose a stable edition supported by the deployment target. On a Nix-managed
machine, use its declared compiler, Cargo, rustfmt, Clippy, rust-analyzer and
standard-library sources; a missing rustup is not a broken installation.
Change declarative configuration when tools are missing. Keep project-specific
versions and cross-compilation targets in a pinned development environment.
Expose packages with `rustPlatform.buildRustPackage` and a committed lockfile
for applications; install through the supported package/module interface.

Use the repository's `just` verbs first. Otherwise run:

```sh
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --locked -- -D warnings
cargo test --workspace --locked
cargo test --workspace --doc --locked
cargo build --release --locked
```

Test supported feature combinations explicitly; `--all-features` is suitable
only when features can coexist. If nextest is used, run doctests separately.
Use cargo-audit for dependency advisories; investigate findings before changing
versions. Check compiler, Cargo and rust-analyzer versions and source lookup
when editor diagnostics disagree with the build.

## Performance work

Measure representative end-to-end release builds before changing languages.
Separate CPU, allocation and memory costs from network, storage and external
service latency. Keep an existing implementation when the bottleneck is
elsewhere; introduce Rust at a measured hot path before considering a rewrite.
State the speedup target and compare correctness, throughput, latency and peak
memory using the same inputs and concurrency. Performance is a hypothesis until
measured. Native platform APIs and library availability also constrain choice.

Use borrowing and streaming when they simplify ownership and bound memory.
Use bounded tasks/queues for large inputs. Keep blocking I/O and sleeps off async
executor threads; plan cancellation, timeouts and idempotent retries. Prefer
safe, concrete code; add abstractions and dependencies for a demonstrated need.
Propagate recoverable errors with context instead of panicking on user input.

Credits: official Rust, Cargo, rust-analyzer and Tokio documentation (reference
routing and verification); apollographql/skills@rust-best-practices (release
measurement), wshobson/agents@rust-async-patterns (bounded async work),
jeffallan/claude-skills@rust-engineer (ownership and safety review).
