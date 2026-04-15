# Sync hiskens overlay v0.4.0 to downstream projects

**Type**: Ops / maintenance (not code development)
**Scope**: Two downstream projects — `Topo-Reliability`, `Anhui_CIM`
**Upstream**: `Trellis_Hiskens` fork at v0.4.0 with `overlays/hiskens/` aligned

## Goal

Upgrade the two downstream projects from `.trellis/.version = 0.4.0-beta.10`
to `0.4.0` using the hiskens-fork CLI, preserving:

1. **All user data** in each project (tasks, workspace journals, spec, developer identity)
2. **All hiskens overlay customizations** (nocturne, thinking-framework, review agent, statusline-bridge, context-monitor/intent-gate/todo-enforcer/ralph-loop hooks)
3. **Project-specific local modifications** (if any) — surface them via dry-run so we can merge manually

## Core facts (verified from source)

| # | Fact | File | Implication |
|---|---|---|---|
| 1 | `BUILTIN_OVERLAYS_DIR` is a runtime relative path resolving to repo-root `overlays/` | `packages/cli/src/utils/overlay.ts:26` | Overlay file edits take effect immediately — no rebuild needed for overlay content |
| 2 | `copy-templates.js` does NOT copy `overlays/` into `dist/` | `packages/cli/scripts/copy-templates.js:50` | Same as above — overlays live at source, read at runtime |
| 3 | TypeScript source edits (e.g. `configurators/index.ts` droid entry) DO need rebuild | — | `dist/` is stale (~2 days old); must `pnpm run build` before use |
| 4 | `--overlay hiskens` is NOT persisted anywhere | `init.ts:1293`, `init.ts:1310`, `update.ts` | ⚠️ **Every `trellis update` MUST pass `--overlay hiskens` explicitly**, or the CLI will overwrite all overlay files with pure upstream base — silently erasing all hiskens customization |
| 5 | `PROTECTED_PATHS` excludes user data from any update write | `update.ts:79-87` | `.trellis/tasks/`, `.trellis/workspace/`, `.trellis/spec/`, `.trellis/.developer`, `.trellis/.current-task` are **never touched by update** |

## Preservation guarantees (what is safe)

Per `update.ts:79-87` (`PROTECTED_PATHS`) and `update.ts:645-646` (user data exclusions),
the following are guaranteed untouched by `trellis update`:

- `.trellis/tasks/**` — all existing task directories, PRDs, notes, context jsonl files
- `.trellis/workspace/**` — all developer workspaces and journal-*.md files
- `.trellis/spec/**` — all project-customized spec files
- `.trellis/.developer` — developer identity
- `.trellis/.current-task` — active task pointer

**One exception**: `update.ts:1616-1626` has a one-time migration that renames
`traces-*.md` → `journal-*.md` inside `workspace/`. This only runs if those legacy
files exist; it's a rename, not a destructive operation.

## What WILL change

1. **Upstream v0.4.0 new/modified files** — base templates under `.claude/`, `.trellis/workflow.md`,
   scripts, non-overlay platform commands
2. **Hiskens overlay v0.4.0 files** — the 4 files we fixed this session plus the rest of
   `overlays/hiskens/` synced to v0.4.0
3. **Migration manifests** — `0.4.0-rc.0.json`, `0.4.0-rc.1.json`, `0.4.0.json` will run in
   sequence. Possible `safe-file-delete` actions for files deemed obsolete and untouched by user.

## Risks (4)

### R1: Big-version jump (`beta.10` → `rc.0` → `rc.1` → `v0.4.0`)

Three migration manifests apply in one run. `safe-file-delete` actions may remove files
considered unmodified since install.

**Mitigation**: new git branch per project + `--dry-run` first + `git diff` review.

### R2: Hash conflicts from prior hand-edits OR overlay-version mismatch

`.template-hashes.json` records hash at install time. If a user hand-edited an overlay file
since install, or if beta.10 overlay hash ≠ v0.4.0 overlay hash for the same path, update
enters interactive conflict resolution (overwrite / skip / create-new).

**Unclear from my reading**: whether recorded hash is `base` or `base + overlay`. Will learn
from Topo dry-run output and document here.

**Mitigation**: use `--create-new` for anything surprising to get `.new` files for manual merge.

### R3: Forgetting `--overlay hiskens` → disaster

Without the flag, upstream base overwrites every overlay file — nocturne, thinking-framework,
review agent, statusline-bridge gone. Hook files that exist only in hiskens (context-monitor.py,
intent-gate.py, todo-enforcer.py, ralph-loop.py) *may* be preserved because upstream has nothing
at those paths, but `session-start.py` and `statusline.py` would revert to upstream versions.

**Mitigation**: use shell aliases, never type the update command by hand:

```bash
alias trellis-update-topo='cd /mnt/e/Github/repo/Topo-Reliability && node /home/hcx/github/Trellis_Hiskens/packages/cli/bin/trellis.js update --overlay hiskens'
alias trellis-update-anhui='cd /mnt/e/Github/repo/Anhui_CIM && node /home/hcx/github/Trellis_Hiskens/packages/cli/bin/trellis.js update --overlay hiskens'
```

### R4: WSL ↔ Windows filesystem (`/mnt/e/...`)

- Line endings protected by `.gitattributes`
- Executable bit may be lost on NTFS; post-update `chmod +x` on `.claude/hooks/*.py`, `.trellis/scripts/*.py` if needed
- Symlink support limited on `/mnt/e/`

## Execution plan

### Step 0: Rebuild fork CLI (one-time)

```bash
cd /home/hcx/github/Trellis_Hiskens/packages/cli
pnpm install        # if deps changed
pnpm run build      # tsc + copy-templates
ls -la dist/cli/index.js   # verify timestamp updated
```

### Step 1: Session alias

```bash
alias htrellis='node /home/hcx/github/Trellis_Hiskens/packages/cli/bin/trellis.js'
```

### Step 2: Topo-Reliability flow

```bash
cd /mnt/e/Github/repo/Topo-Reliability

# 2.0 safety
git status                                # must be clean
git checkout -b trellis-update-v0.4.0

# 2.1 dry-run (read-only preview)
htrellis update --overlay hiskens --dry-run

# 2.2 review output; decide
# 2.3 execute
htrellis update --overlay hiskens

# 2.4 review diff
git status
git diff .claude/ .trellis/

# 2.5 sanity checks
ls -la .claude/hooks/*.py .trellis/scripts/*.py    # perm bits
ls .trellis/tasks/                                 # user tasks preserved
ls .trellis/workspace/                             # user workspace preserved
cat .trellis/.version                              # should be 0.4.0

# 2.6 run project's own tests (user decides which)

# 2.7 commit + merge
git add -A
git commit -m "chore(trellis): update to v0.4.0 (hiskens overlay)"
git checkout main
git merge --ff-only trellis-update-v0.4.0
```

### Step 3: Anhui_CIM flow

Same as Step 2, substitute path.

## Acceptance criteria

- [ ] `packages/cli/dist/cli/index.js` timestamp refreshed after rebuild
- [ ] `htrellis` alias defined in session
- [ ] Topo-Reliability dry-run reviewed and documented here
- [ ] Topo-Reliability update executed; `.trellis/.version` = `0.4.0`
- [ ] Topo-Reliability `.trellis/tasks/` and `.trellis/workspace/` byte-identical before/after
- [ ] Topo-Reliability hiskens overlay files (nocturne, thinking-framework, review agent, etc.) present and correct
- [ ] Topo-Reliability hooks have executable bit (if lost, restored via `chmod +x`)
- [ ] Topo-Reliability committed + merged to `main`
- [ ] Anhui_CIM: same 5 bullets

## Execution log

(append-only; record dry-run output, conflicts, decisions, surprises)

### 2026-04-15

- Task created. Verified `PROTECTED_PATHS` in `update.ts:79-87`.
- Waiting on user approval before Step 0.
- Step 0 complete. Rebuilt `packages/cli` via `pnpm run build`; `packages/cli/dist/cli/index.js` timestamp refreshed from `2026-04-13 11:38` to `2026-04-15 15:40`. Verified runtime entry with `node packages/cli/bin/trellis.js --version` → `0.4.0`.
- User requested handling `Anhui_CIM` first because `Topo-Reliability` has in-flight work.
- Anhui_CIM preflight: repo clean on `main`; `.trellis/.version` = `0.4.0-beta.10`; pre-update digests:
  - tasks = `cadcad203bc567d8c4b86c75fa5a18749e7c4723a9da035fb82da27e684e0952`
  - workspace = `bd3d0d42f0cad6380ace60a81ff64d027da2e846db2598f5d3dcea0aa8d4dd58`
- Anhui_CIM dry-run (`update --overlay hiskens --dry-run`) results:
  - 3 new files: `.trellis/scripts/search/_common.py`, `.cursor/commands/trellis-before-dev.md`, `.cursor/commands/trellis-check.md`
  - 85 template auto-updates
  - 4 deprecated Cursor command files cleaned automatically
  - 8 user-modified conflicts surfaced:
    - `.trellis/worktree.yaml`
    - `.trellis/.gitignore`
    - `.claude/commands/trellis/check-cross-layer.md`
    - `.claude/commands/trellis/finish-work.md`
    - `.claude/agents/plan.md`
    - `.claude/settings.json`
    - `.claude/commands/trellis/check-cross-layer-base.md`
    - `.agents/skills/update-spec/SKILL.md`
  - User data explicitly preserved in dry-run output: `.trellis/workspace/`, `.trellis/tasks/`, `.trellis/spec/`, `.trellis/.developer/`
- Anhui_CIM execution:
  - Created branch `trellis-update-v0.4.0`
  - Ran `node /home/hcx/github/Trellis_Hiskens/packages/cli/bin/trellis.js update --overlay hiskens --create-new`
  - Backup created: `.trellis/.backup-2026-04-15T07-47-46/`
  - Conflict strategy: `--create-new` for all 8 modified files to avoid overwriting project-local customizations
  - Created `.new` files:
    - `.agents/skills/update-spec/SKILL.md.new`
    - `.claude/agents/plan.md.new`
    - `.claude/commands/trellis/check-cross-layer-base.md.new`
    - `.claude/commands/trellis/check-cross-layer.md.new`
    - `.claude/commands/trellis/finish-work.md.new`
    - `.claude/settings.json.new`
    - `.trellis/.gitignore.new`
    - `.trellis/worktree.yaml.new`
- Anhui_CIM post-check:
  - `.trellis/.version` = `0.4.0`
  - tasks digest unchanged = `cadcad203bc567d8c4b86c75fa5a18749e7c4723a9da035fb82da27e684e0952`
  - workspace digest unchanged = `bd3d0d42f0cad6380ace60a81ff64d027da2e846db2598f5d3dcea0aa8d4dd58`
  - `.claude/hooks/*.py` and `.trellis/scripts/*.py` remain executable on `/mnt/e/`
  - Project tests not run yet; user to decide project-specific validation
- Anhui_CIM validation:
  - `uv run pytest tests/test_context_assembly.py` → `41 passed`
  - `uv run python .trellis/scripts/test_nocturne_client.py` → pass
  - `uv run python .trellis/scripts/test_nocturne_integration.py` initially failed because the test still expected `inject-subagent-context.py` to define `get_nocturne_hints()` inline; in v0.4.0 that helper now lives in `.trellis/scripts/common/context_assembly.py`
  - Verified actual hook behavior with a temporary `.trellis/.current-task` smoke test: hook returned valid JSON and produced `updatedInput.prompt` (`prompt_len=170061`)
  - Updated `.trellis/scripts/test_nocturne_integration.py` to assert the current contract (hook imports shared hints; hints text lives in `common/context_assembly.py`); rerun passed
  - `uv run ruff check .trellis/scripts/test_nocturne_integration.py` → pass
  - Business smoke test: `uv run python tests/verify_baseline.py` → all 10 XML baseline cases passed
- Anhui_CIM conflict resolution:
  - Reviewed all 8 generated `.new` files
  - Kept current project-local versions for `.trellis/worktree.yaml` and `.trellis/.gitignore`; upstream candidates would have removed Anhui-specific worktree copy/verify settings and local ignore rules
  - Other 6 `.new` files were whitespace/newline-only diffs; no semantic content to merge
  - Deleted all `.new` files after review; no `.new` files remain in the repo
