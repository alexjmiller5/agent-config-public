# Language-selection skill checks

Compare responses without and with the skill for these scenarios:

1. A portable API-polling daemon has mostly network latency and unspecified
   hosting. Go is provisional; resolve hosting and resource targets first.
2. A native iPhone feed plus thin Workers API should not use Rust everywhere
   just because performance is desirable. Evaluate Swift and TypeScript per layer.
3. An existing Python Modal pipeline waits on models and uses Python-only
   libraries. Keep its language; profile before any performance migration.
4. A new CPU-heavy parser has C callers and a strict memory budget. Compare
   Rust/Zig with a focused allocator, lifetime, ABI and deployment spike.

The baseline selected reasonable languages in all four cases. The with-skill
run retained those outcomes and added explicit hosting uncertainty, per-layer
choices, end-to-end targets and component-first migration, and a focused ABI
spike. The purpose is consistency at these gates, not elementary language advice.

Static trigger positives: choose app language; compare Rust/Go/Zig; undecided
new app stack; Python migration; C ABI core language; native mobile language;
backend stack choice; language ecosystem selection; new CLI language;
performance rewrite language.

Static near misses: fix a Go typo; existing Rust borrow error; format .rs;
implement approved TypeScript UI; Swift layout; SQL debugging; read a note;
travel; image editing; install an app unchanged. Choosing only a compiler version
within an established language is also outside scope.

Read-only scenario review passed 4/4; static description review matched 10/10
positives and excluded 10/10 near misses. This is not a measured automatic
invocation rate. Recheck these scenarios when modifying the gates.

Local-library candidates: Rust (implementation references, narrower scope),
scout (research, not operational selection), and new-project (private scaffold
routing). Public skill searches yielded no suitable generic gate skill.
The resulting skill uses the approved gates and primary documentation; no
external skill text was copied.
