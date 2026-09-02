---
name: nix-mechanics
description: Nix language and tooling mechanics - flakes, overlays, nix-darwin/home-manager options, packaging, searching nixpkgs, and debugging rebuild failures. Shareable/generic (no personal-machine specifics - those live in dev-env). Use when touching any .nix file, writing a flake, packaging software, verifying an option exists, or debugging "package not found" / "option does not exist" / overlay-not-applying / rebuild issues.
---

# Nix Mechanics

Core rule: **verify before you write** - check that a package/option actually
exists before using it, and read error messages completely before changing
anything.

## Searching nixpkgs and options

Option-name discovery is the painful part of nix-darwin/home-manager work. In
order of preference:

1. **mcp-nixos MCP server** (available - registered in
   `skills/mcp/.mcp.json`): API search over nixpkgs packages,
   NixOS options, **home-manager options, and nix-darwin options**. Use it
   first for "does option X exist" and "what's this package called".
2. **CLI, zero install:**
   ```bash
   nix search nixpkgs <pkg>                 # package search (regex ok)
   nix eval nixpkgs#<pkg>.version           # confirm exact attr exists
   nix eval nixpkgs#legacyPackages.aarch64-darwin.<pkg>.meta.platforms  # darwin support?
   ```
3. **Web UIs**: search.nixos.org (packages + NixOS options),
   home-manager-options.extranix.com, daiderd.com/nix-darwin/manual.

**Never assume an option exists.** `programs.npm` famously doesn't (use
`home.file.".npmrc"`). If search can't find it, it doesn't exist - configure
via `home.file` / `environment.etc` / `launchd.user.agents` instead. Attr
names differ from brew formula names more often than you'd think (brew
`sevenzip` → nixpkgs `_7zz`; brew `yq` → nixpkgs `yq-go`).

## Flake best practices

- **Every input `follows` the parent nixpkgs** -
  `some-input.inputs.nixpkgs.follows = "nixpkgs";`. Skipping this = duplicate
  nixpkgs downloads, slow evals, version skew.
- **Every input must appear in the `outputs` arg set** (or use `...`), else
  "unexpected argument".
- Need `inputs` inside modules? Pass via `specialArgs = { inherit inputs; }`
  (darwin/NixOS) or `extraSpecialArgs` (home-manager) - "undefined variable
  'inputs'" means this is missing.
- `imports = [ ./name ]` resolves `name/default.nix`; `./name.nix` resolves
  the file. Mismatched form → "path does not exist".
- **Flakes only see git-tracked files** - a brand-new file must be `git add`ed
  before `nix build` can import it ("path does not exist" on a file that
  clearly exists = this).
- Unfree packages: `config.allowUnfree` in a flake does NOT propagate to
  `nix develop`. Use `NIXPKGS_ALLOW_UNFREE=1 nix develop --impure` or
  (darwin config) `nixpkgs.config.allowUnfree = true;` in a module.
- Direnv: `.envrc` = `use flake`.

Commands: `nix flake check` · `nix flake update [input]` · `nix flake metadata`
· `nix develop [-c cmd]` · `nix build .#pkg` · `nix run nixpkgs#tool -- args`.

## Overlays

Apply at nixpkgs import, or via `nixpkgs.overlays` in a **system-level module**.
With home-manager's `useGlobalPkgs = true`, overlays in `home.nix` are
**silently ignored** - the most common overlay failure mode. Debug "attribute
not found despite overlay": check the overlay is at the system level
(`grep -rn "nixpkgs.overlays"`), then
`nix eval .#<config>.config.nixpkgs.overlays`.

```nix
nixpkgs.overlays = [
  inputs.something.overlays.default
  (final: prev: { myTool = prev.myTool.override { ... }; })
];
```

## Packaging

- Shell scripts → `pkgs.writeShellApplication { name; runtimeInputs; text; }`
  - deps on PATH, shellcheck for free.
- Python → `buildPythonApplication` with `pyproject = true`, or keep uv and
  wrap entrypoints with writeShellApplication; expose as `packages.default`.
- Upstream binary → fetchurl-per-system:

```nix
let
  version = "1.0.0";
  sources = {
    aarch64-darwin = { url = "..."; sha256 = "sha256-..."; };
    x86_64-linux  = { url = "..."; sha256 = "sha256-..."; };
  };
  source = sources.${system} or (throw "Unsupported system: ${system}");
in pkgs.stdenv.mkDerivation {
  pname = "tool"; inherit version;
  src = pkgs.fetchurl { inherit (source) url sha256; };
  dontUnpack = true;
  installPhase = ''
    mkdir -p $out/bin && cp $src $out/bin/tool && chmod +x $out/bin/tool
  '';
}
```

Hashes: `nix-prefetch-url <url>` then `nix hash to-sri --type sha256 <hash>`;
or build with `lib.fakeSha256` and copy the real one from the mismatch error.

## Common mistakes checklist

- [ ] ONE `environment.systemPackages` / `home.packages` list per file - a
      second assignment overwrites (or use `lib.mkAfter`)
- [ ] No package declared in both system and home-manager
- [ ] No absolute paths - reference `pkgs.foo` or `${pkgs.foo}/bin/foo`
- [ ] Flake-input packages referenced as `inputs.x.packages.${pkgs.system}.default`

## Troubleshooting

Order: read the FULL error → `--show-trace` → check scope (overlay/module
location) → check inputs. Never fix by rebuilding repeatedly with guesses;
batch all fixes into one rebuild.

```bash
# Evaluate without switching (darwin)
nix build .#darwinConfigurations.<host>.system   # full eval + build, no activation
nix eval .#darwinConfigurations.<host>.config.<some.option>

# Generations / rollback
darwin-rebuild --list-generations
darwin-rebuild switch --rollback
nix diff-closures /nix/var/nix/profiles/system-{N,M}-link

# launchd jobs (darwin's systemctl+journalctl)
launchctl print gui/501/<label>            # status, last exit code
# StandardOut/ErrorPath in the agent definition beat `log show` for debugging

# REPL spelunking
nix repl --expr 'builtins.getFlake "'$PWD'"'
```

- "infinite recursion" → circular module deps; `--show-trace`, break with
  `lib.mkBefore`/`mkAfter` or restructure.
- Config "not applying" → did the rebuild succeed? right host? launchd agent
  needs `launchctl kickstart -k gui/501/<label>`?
- NixOS servers: missing shared libs → `ldd <bin> | grep "not found"` then
  `nix-locate lib.so`, add ALL at once; `nixos-rebuild test` before `switch`.

## Store hygiene

```bash
nix store gc                          # free space
sudo nix-collect-garbage --delete-older-than 30d   # also drops old generations (kills rollbacks)
nix why-depends .#pkg nixpkgs#openssl # why is this in my closure
nix path-info -Sh .#pkg               # closure size
```
