# Sync upstream v0.5.0-beta.18

## Goal
Merge upstream Trellis `v0.5.0-beta.18` into the Hiskens fork while preserving the overlay layer.

## Core Principle
Everything outside `overlays/` and the 6 overlay-loader files must match upstream exactly. The fork's value lives entirely in the overlay layer — upstream content is the immutable base.

## Overlay Files (fork touches these only)
1. `packages/cli/src/utils/overlay.ts`
2. `packages/cli/src/configurators/index.ts`
3. `packages/cli/src/commands/init.ts`
4. `packages/cli/src/commands/update.ts`
5. `packages/cli/src/cli/index.ts`
6. `packages/cli/scripts/copy-templates.js`

## Steps
1. Assess delta: check which of the 6 overlay files changed in beta.18
2. Create overlay branch from beta.18 tag, replay overlay commits
3. Resolve conflicts (upstream first, re-apply overlay additions)
4. Update metadata: `.upstream-version`, `HISKENS.md`, `overlay.yaml`
5. Validate: build, test, py_compile, smoke test
6. Merge to main (minor bump → `--no-ff`)
7. Verify: non-overlay content matches upstream exactly

## Acceptance Criteria
- [ ] `git diff v0.5.0-beta.18 HEAD -- . ':!overlays/'` shows only the 6 overlay files + fork-specific metadata
- [ ] `.upstream-version` = `v0.5.0-beta.18`
- [ ] `.trellis/.version` matches upstream
- [ ] Build, lint, typecheck pass
- [ ] Smoke test: init + update with overlay works
