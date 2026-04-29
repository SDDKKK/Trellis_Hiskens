---
name: fork-sync-strategy
description: >
  Explains the rebase-based upstream sync strategy for this fork repo (Trellis_Hiskens).
  Covers: why rebase not merge, what the overlay commit surface looks like, how to assess
  upstream deltas, resolve conflicts, validate, and merge back to main. Use when planning
  or executing an upstream sync, investigating a conflict, or onboarding someone to the
  fork maintenance model. Triggered by: "how do we sync", "upstream strategy", "rebase plan",
  "fork maintenance", "怎么同步上游", "rebase 策略".
---

# Fork Sync Strategy — Trellis_Hiskens

## Why Rebase, Not Merge

This fork carries a thin layer of overlay commits on top of an immutable upstream tag.
Rebase keeps that relationship explicit: the overlay branch is always "upstream tag + N commits."
A merge-based approach would interleave fork and upstream history, making it hard to tell
what the fork actually changed and impossible to cleanly re-derive the overlay on a new tag.

```
v0.5.0-beta.17  ←  overlay commit 1  ←  overlay commit 2  ←  ...  ←  HEAD
   (upstream)       (loader support)     (hiskens overlay)
```

## What the Overlay Touches

The fork modifies exactly these upstream files (plus everything under `overlays/hiskens/`):

| File | Purpose |
|------|---------|
| `packages/cli/src/utils/overlay.ts` | Overlay resolution, config loading, settings merge engine |
| `packages/cli/src/configurators/index.ts` | Overlay-aware template collection, path safety, conflict protection |
| `packages/cli/src/commands/init.ts` | `--overlay` flag wiring in init flow |
| `packages/cli/src/commands/update.ts` | `--overlay` flag wiring in update flow |
| `packages/cli/src/cli/index.ts` | CLI option registration |
| `packages/cli/scripts/copy-templates.js` | Packages `overlays/` into dist at build time |

Everything else in `packages/cli/src/` is pure upstream. If a file isn't in this list,
the fork doesn't touch it — upstream changes to it will never conflict.

## How to Sync

### 1. Fetch and assess

```bash
git fetch upstream --tags
CURRENT=$(cat .upstream-version)
NEW=<new-tag>
git log --oneline $CURRENT..$NEW                              # theme overview
git diff --stat $CURRENT..$NEW -- packages/cli/src/           # overlay-relevant changes
```

If the delta is large (30+ commits), use parallel research agents to categorize changes
by theme and flag which ones touch the 6 overlay files.

### 2. Rebase overlay commits

```bash
git checkout <overlay-branch>
git rebase --onto $NEW $CURRENT
```

Conflicts only happen when upstream changed the same region of one of the 6 overlay files.
In practice:
- `update.ts` conflicts most often (overlay adds parameters to `collectTemplateFiles`)
- `index.test.ts` occasionally (new upstream tests near overlay test block)
- `init.ts` rarely (overlay additions are in separate code blocks)

**Resolution principle**: accept upstream first, then re-apply overlay additions alongside.

### 3. Update metadata

| File | What to change |
|------|---------------|
| `overlays/hiskens/overlay.yaml` | `compatible_upstream` range |
| `.upstream-version` | New tag value |
| `HISKENS.md` | Base commit hash + diff script reference |

These three must always agree. A mismatch causes version validation warnings in consumers.

### 4. Validate

```bash
pnpm install && pnpm build && pnpm test
python3 -m py_compile overlays/hiskens/templates/claude/hooks/*.py
```

Sandbox smoke tests:
- `trellis init --claude --overlay hiskens -y --no-monorepo` in a temp dir
- `trellis update --overlay hiskens --dry-run` in the same dir
- Reinit with existing settings to verify conflict protection

### 5. Review

Run `/codex:adversarial-review --base <NEW>` for an independent code review of the
overlay diff. Focus on: write safety, settings merge correctness, hook compatibility.

### 6. Merge to main

For minor bumps (same major version): `git merge --no-ff`

For major version jumps (v0.4→v0.5) where main diverged significantly:
```bash
git checkout main
git merge -s ours <overlay-branch> -m "Merge: rebuild on <NEW> (ours strategy)"
git checkout <overlay-branch> -- .
git add -A && git commit --amend --no-edit
```

This replaces main's tree entirely with the overlay branch while preserving merge history.

## Common Conflict Patterns

| Upstream change | Where it conflicts | How to resolve |
|----------------|-------------------|----------------|
| New function in `update.ts` near `collectTemplateFiles` | Overlay adds `overlayName` parameter | Keep upstream function, add overlay parameter after |
| New test block in `index.test.ts` | Near overlay's test block boundary | Keep both blocks, fix imports if needed |
| New platform added to configurators | `PLATFORM_OVERLAY_TARGETS` needs entry | Add the new platform's overlay mapping |
| Hook file renamed/moved in shared-hooks | Overlay's `inject-subagent-context.py` OVERRIDE | Verify overlay version still a valid superset |
| `settings.json` base template changed | Overlay `settings.overlay.json` merge | Test merged output, verify hook event names still valid |

## Two-Layer Architecture

The fork has two layers of files that combine at install time:

```
packages/cli/src/templates/   ← Layer 1: upstream base (all Trellis users)
overlays/hiskens/templates/   ← Layer 2: Hiskens additions (--overlay hiskens users only)

User project = Layer 1 + Layer 2 (overlay overwrites same-path files)
```

### Where to Make Changes — Decision Flow

```
Want to modify a file (e.g., trellis-research.md)?
│
├─ Is the change Hiskens-specific? (scientific computing, CCR, Nocturne, etc.)
│  └─ YES → Create/edit in overlays/hiskens/templates/<same-path>
│           The overlay copy replaces the upstream version at install time.
│
├─ Is the change useful for ALL Trellis users?
│  └─ YES → Submit a PR to upstream. After merge, sync down via the
│           rebase workflow above. Do NOT modify packages/cli/src/ directly.
│
└─ Is it a new file that doesn't exist upstream?
   └─ YES → Add to overlays/hiskens/templates/<target-path>
            It will be installed alongside upstream files.
```

### Rules

- **Never modify upstream template files in `packages/cli/src/templates/`** — except the 6 overlay-loader files listed above. Every additional modified file is a future conflict surface during sync.
- **Overlay is whole-file replacement, not patch** — if you create `overlays/hiskens/templates/claude/agents/trellis-research.md`, it entirely replaces the upstream version. When upstream updates that file in a future release, your overlay copy will NOT inherit those changes automatically.
- **Minimize overlay overrides** — only override upstream files when genuinely needed. Each override is a maintenance burden: you must manually check upstream changes to overridden files during every sync.
- **Root-level files are derived, not source** — `.claude/`, `.agents/`, etc. are installed copies. Edit the source (`overlays/hiskens/templates/` or upstream), then run `trellis update --overlay hiskens` to refresh.

### Overlay Sync Maintenance

When syncing to a new upstream tag, check each overlay file:

```bash
# List overlay files that also exist in upstream
for f in $(find overlays/hiskens/templates/ -type f | sed 's|overlays/hiskens/templates/||'); do
  git show v0.5.0-beta.18:packages/cli/src/templates/$f >/dev/null 2>&1 && echo "OVERRIDE: $f"
done
```

For each OVERRIDE file: compare upstream's new version with your overlay version. Merge upstream improvements into the overlay copy if needed.

## What NOT to Do

- **Don't merge upstream into main directly** — creates an unmaintainable tangle of v0.4 fork code + v0.5 upstream
- **Don't edit upstream files beyond the 6 listed** — every extra file is a future conflict surface
- **Don't skip the metadata update** — stale `.upstream-version` causes silent version mismatch in consumers
- **Don't rebase onto a branch tip** — always rebase onto an immutable tag for reproducibility
- **Don't push to main without smoke tests** — consumers read from main's working tree at runtime

## Related

- `overlays/hiskens/MAINTENANCE.md` — rules for editing overlay content
- `scripts/upstream-diff.sh` — helper for comparing upstream tags
- `HISKENS.md` — top-level fork documentation
- `/trellis-upgrade` skill — full lifecycle including downstream consumer propagation
