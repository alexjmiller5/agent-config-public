# Primary references

Read the relevant documentation when choosing a language or relying on
version-sensitive behavior. These are capability references, not universal
performance rankings.

| Topic | Source |
|---|---|
| Go design and compatibility | https://go.dev/doc/faq and https://go.dev/doc/go1compat |
| Go memory and profiling | https://go.dev/doc/gc-guide and https://go.dev/doc/diagnostics |
| Go tests, races and security | https://go.dev/doc/articles/race_detector and https://go.dev/doc/security/ |
| Go editor tools under Nix | https://github.com/golang/vscode-go/wiki/settings (`go.toolsManagement.autoUpdate`, `go.toolsManagement.checkForUpdates`, `go.alternateTools`) |
| Go native dependencies | https://pkg.go.dev/cmd/cgo |
| Rust | https://doc.rust-lang.org/book/ and https://doc.rust-lang.org/cargo/ |
| Zig lifetimes and build behavior | https://ziglang.org/documentation/ (select the pinned version) |
| Zig language-server compatibility | https://zigtools.org/zls/install/ |
| Swift platforms and app types | https://www.swift.org/getting-started/ |
| TypeScript | https://www.typescriptlang.org/docs/handbook/intro.html |
| Workers language support and Wasm | https://developers.cloudflare.com/workers/languages/ |
| Modal Go/JS SDK scope | https://modal.com/docs/guide/sdk-javascript-go |
| .NET Native AOT capabilities/limits | https://learn.microsoft.com/en-us/dotnet/core/deploying/native-aot/ |
| Kotlin / JVM integration | https://kotlinlang.org/docs/server-overview.html |
| Erlang-runtime choices | https://elixir-lang.org/ and https://gleam.run/ |
| Shared client UI | https://dart.dev/overview |
| Scientific computing | https://docs.julialang.org/en/v1/manual/performance-tips/ |
| CPU/GPU kernels | https://mojolang.org/docs/faq/ |
| Other native candidates | https://nim-lang.org/, https://crystal-lang.org/, https://odin-lang.org/ |

Check actual deployment support: Rust on Workers uses Wasm; Go/JS Modal client
SDKs do not imply the same scope as Python Function definitions. Zig and ZLS
must be compatible. Cgo affects Go cross-compilation. Native AOT requires
compatible dependencies. Verify current details instead of freezing release
numbers or temporary limitations into policy.
