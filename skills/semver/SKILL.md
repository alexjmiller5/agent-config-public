---
name: semver
description: Use when about to change a version number (package.json, pyproject.toml, Cargo.toml, MARKETING_VERSION, CFBundleShortVersionString, a VERSION file), create or push a release tag, cut or publish a release, or when the user says ship, release, publish or cut a version, or asks which version comes next.
---

# Semver: when to release, and which number

A version names a release people can install ([semver.org](https://semver.org)).
Changes pile up on the main branch unversioned; the number moves only when a
release is cut.

## The rule

- **An ordinary change commits without touching the version and without a
  tag** - a fix, a tweak and a feature alike.
- **A release happens only when the user asks for one** ("ship it",
  "release", "cut a version") **or approves your suggestion to cut one.**
- **A release is one commit plus one tag:** the commit sets every version
  field to the new number, and `vX.Y.Z` tags that commit. Where pushing a tag
  publishes (a release workflow on tags), push it only when the user asked to
  ship.

Earlier commits that bumped the version every time are not precedent to
follow; they are the mess this rule exists to stop.

Installing a dev or ad hoc build on your own machine or phone is not a
release and needs no version.

## Suggesting a release

Suggest one, never cut it, when a user-visible change is finished and
verified and the user will want it installed, or when several unreleased
changes have piled up:

> Unreleased since v1.5.0: global shortcut setting, panel spacing fix.
> Suggest v1.6.0 (minor: new setting). Ship it?

While the user is still iterating on how something looks or feels, offer the
local dev build (`just run`, `just dev`) instead, and release once they are
happy - not once per iteration.

## Which number

Compare the whole release to the previous tag; the highest-impact change
decides.

| Bump | When the release... |
|---|---|
| **major** | breaks something users relied on or makes them act: removed feature, renamed URL scheme / CLI flag / config key, one-way data migration, new required setup |
| **minor** | adds a capability users can see or call, backwards compatible: new feature, setting, command, option, endpoint |
| **patch** | only fixes and polishes: bug fix, layout or copy tweak, performance, refactor, dependency update |

- Several tweaks to a feature after it shipped go out as one patch, not a
  patch each.
- `0.y.z` is initial development: a breaking change bumps minor. Go to
  `1.0.0` once something depends on it or it is in daily use.
- Pre-release suffixes (`-beta.1`) only when the pipeline actually ships
  pre-releases to a separate channel.

## One source of truth

The tag is the release's identity. A version the build stamps (Info.plist,
package metadata) equals the tag: set in the release commit, or better,
derived from the tag by CI. Found a version field that disagrees with the
latest tag? Report it; never "fix" it with another bump.

## When a release fails

- **Nothing reached users** (CI failed before any GitHub release, artifact or
  package/cask update): fix it, delete the tag locally and on the remote, and
  re-tag the same version on the fix commit.
- **Anything was published:** that version is immutable. Fix forward with the
  next patch. Never move or force-push a published tag.

## Red flags

| Thought | Reality |
|---|---|
| "Each earlier change got its own bump" | Precedent of the mess; commit without the bump |
| "I'll tag it so it's ready" | An unrequested tag is a release nobody asked for |
| "Bump now, release later" | An unreleased bump makes the next agent bump again |
| Patch release minutes after the last one for the same feature | Batch it; offer the dev build while iterating |
