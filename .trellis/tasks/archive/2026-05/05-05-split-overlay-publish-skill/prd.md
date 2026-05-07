# Split trellis-overlay: extract publish-and-dogfood workflow

## Problem

`trellis-overlay` skill is too long — it mixes upstream sync (Steps 1-4) with build/publish/dogfood (Steps 5-9). The publish workflow is also used standalone (after any template change, not just upstream syncs). Current dogfood uses `node packages/cli/dist/cli/index.js update` which bypasses the published package.

## Solution

Create a new skill `trellis-publish` that covers:
1. Version bump
2. Build
3. npm publish (with `--tag rc` + `npm dist-tag add ... latest`)
4. `npm install -g @hiskens/trellis` (install the published version)
5. `trellis update --force` (dogfood via published CLI)
6. Commit dogfood + version bump

Update `trellis-overlay` to end at Step 4 (metadata) and reference `trellis-publish` for the rest.

## Scope

- **New file**: `.claude/skills/trellis-publish/SKILL.md`
- **Modify**: `.claude/skills/trellis-overlay/SKILL.md` — remove Steps 5-9, add cross-reference

## Key Design Decisions

- Dogfood uses `trellis update --force` (global CLI from npm) not `node dist/cli/index.js update` (local build)
- Always publish as prerelease (`--tag rc`) then promote to latest — safer than direct `latest` publish
- Version format stays `{upstream}-hiskens` with no trailing build number
