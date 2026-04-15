# Sync hiskens overlay v0.4.0 to downstream projects

**Type**: Ops / maintenance (not code development)
**Scope**: Two downstream projects — `Topo-Reliability`, `Anhui_CIM`
**Upstream**: `Trellis_Hiskens` fork at v0.4.0 with `overlays/hiskens/` aligned

**Rounds**:
- Round 1 (2026-04-15 morning): Anhui_CIM initial upgrade `beta.10 → 0.4.0`
- Round 2 (2026-04-15 afternoon): Anhui_CIM overlay resync after Hiskens overlay changes
- **Round 3 (current)**: Anhui_CIM third resync + Topo-Reliability initial upgrade, triggered by new Hiskens commits `c701579`/`c33569a`/`b7e2a31`

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
- Anhui_CIM overlay resync after later `overlays/hiskens/` changes:
  - Rebuilt `packages/cli` because `packages/cli/src/**` had newer commits than `dist/cli/index.js`
  - Created branch `trellis-overlay-resync-20260415`
  - Ran `node /home/hcx/github/Trellis_Hiskens/packages/cli/bin/trellis.js update --overlay hiskens --create-new`
  - Auto-updated 27 managed files and surfaced 18 `.new` conflicts
  - Conflict triage:
    - kept Anhui-local versions for `.trellis/worktree.yaml` and `.trellis/.gitignore`
    - kept generated/local equivalents for `.claude/settings.json`, `.claude/hooks/statusline.py`, `.cursor/commands/trellis-finish-work.md`, `.agents/skills/update-spec/SKILL.md`, `search/*`, and `.trellis/scripts/common/cli_adapter.py`
    - accepted latest overlay versions for `.claude/hooks/session-start.py`, `.codex/hooks/session-start.py`, `.claude/commands/trellis/finish-work.md`, and `.claude/agents/plan.md`
    - deleted all resolved `.new` files; repo left with no pending `.new`
  - Validation:
    - `uv run python .trellis/scripts/test_nocturne_client.py` → pass
    - `uv run python .trellis/scripts/test_nocturne_integration.py` initially failed on an outdated `session-start.py` import-path assertion; updated the test to check `SCRIPTS_DIR` + conditional `sys.path.insert(...)`, rerun passed
    - `uv run python -m pytest tests/test_context_assembly.py` → `41 passed`
    - `uv run python -m ruff check .claude/hooks/session-start.py .codex/hooks/session-start.py .trellis/scripts/test_nocturne_integration.py .trellis/scripts/add_session.py .trellis/scripts/common/context_assembly.py .trellis/scripts/common/task_context.py .trellis/scripts/create_bootstrap.py .trellis/scripts/multi_agent/plan.py` → pass after `--fix` reordered imports in `.trellis/scripts/common/task_context.py` and `.trellis/scripts/create_bootstrap.py`

---

## Round 3 (2026-04-15 evening)

### Trigger

Three new Hiskens commits appeared after Anhui Round 2 (`b7bec6f`):

| Commit | Impact | Class |
|---|---|---|
| `c701579` feat(hiskens): migrate overlay workflow to package-scoped specs | Large overlay rewrite: `trellis/scripts/common/{task_context,context_assembly}.py`, `add_session.py`, `create_bootstrap.py`, `multi_agent/plan.py`, `claude/hooks/session-start.py`, `claude/commands/trellis/{start,parallel,finish-work,before-python-dev,before-matlab-dev,check-python,check-matlab}.md`, `claude/agents/{implement,plan}.md`, `codex/agents/plan.toml` | (a) overlay |
| `c33569a` feat(cli): materialize hiskens package specs in monorepo init | `packages/cli/src/commands/init.ts` — `materializeOverlaySpecLayers()` new function | (b) CLI src (already in dist; effectively inert for existing downstream repos) |
| `b7e2a31` fix: harden task finish verification | `overlays/hiskens/templates/trellis/scripts/task.py` (finish path hardening) + `packages/cli/src/templates/claude/hooks/inject-subagent-context.py` (research agent gotcha docstring) + `packages/cli/test/regression.test.ts` | (a) overlay + (c) base template |

### Pre-Round-3 state verification

- **Hiskens dist drift**: `dist/templates/claude/hooks/inject-subagent-context.py` was stale (old docstring `"Research doesn't need much preset context"`), src had new gotcha docstring. Confirmed only this one file was drifted; `dist/commands/init.js` already had `materializeOverlaySpecLayers` so c33569a was built; `task.py` src matches dist.
- **Topo-Reliability status** (pre-Round-3):
  - `.trellis/.version` = `0.4.0-beta.10`
  - hiskens overlay already fully installed (all 7 hooks present + `statusline.py`); this is an incremental upgrade, not a fresh install
  - `.trellis.bak/` and `.claude.bak/` residuals from prior upgrade — **decision: delete before upgrade**
  - main is ahead of origin/main — **decision: push first, then upgrade**
- **Anhui_CIM status** (pre-Round-3): `.trellis/.version` = `0.4.0`, clean on main
- **Migration manifests** for `beta.10 → 0.4.0`: `0.4.0-rc.0.json` / `0.4.0-rc.1.json` / `0.4.0.json` **all have `migrations: []`** — no manifest actions, everything goes through template file-sync

### Round 3 Execution plan

**Phase 0: Hiskens side rebuild** (required first to fix dist drift)

```bash
cd /home/hcx/github/Trellis_Hiskens/packages/cli
pnpm run build
grep -c "Research is intentionally lightweight" \
  dist/templates/claude/hooks/inject-subagent-context.py  # must be ≥ 1
```

**Phase 1: Anhui_CIM third resync** (known-good path first, validates Hiskens rebuild)

```bash
cd /mnt/e/Github/repo/Anhui_CIM
git status -sb                                 # must be clean
git checkout -b trellis-overlay-resync-round3
node /home/hcx/github/Trellis_Hiskens/packages/cli/bin/trellis.js update \
  --overlay hiskens --dry-run 2>&1 | tee /tmp/anhui-r3-dryrun.log
node /home/hcx/github/Trellis_Hiskens/packages/cli/bin/trellis.js update \
  --overlay hiskens --create-new 2>&1 | tee /tmp/anhui-r3-update.log
# conflict strategy: keep Anhui-local .trellis/worktree.yaml & .gitignore; prefer upstream for the rest
# validation: pytest tests/test_context_assembly.py + test_nocturne_integration.py + verify_baseline.py + ruff
```

**Phase 2: Topo-Reliability initial upgrade**

```bash
cd /mnt/e/Github/repo/Topo-Reliability

# 0. Pre-flight cleanup (user-approved)
git push origin main                           # push the 1 ahead commit
rm -rf .trellis.bak .claude.bak
git status -sb                                 # must be clean after .bak removal

# 1. Pre-update digest snapshot
mkdir -p /tmp/topo-v0.4.0-snapshot
find .trellis/tasks .trellis/workspace -type f \
  \( -name "*.md" -o -name "*.json" -o -name "*.jsonl" -o -name "*.yaml" \) \
  -print0 | sort -z | xargs -0 sha256sum > /tmp/topo-v0.4.0-snapshot/pre.sha256

# 2. Upgrade branch
git checkout -b trellis-update-v0.4.0

# 3. Dry-run
node /home/hcx/github/Trellis_Hiskens/packages/cli/bin/trellis.js update \
  --overlay hiskens --dry-run 2>&1 | tee /tmp/topo-v0.4.0-snapshot/dryrun.log

# 4. Execute with --create-new (same strategy as Anhui)
node /home/hcx/github/Trellis_Hiskens/packages/cli/bin/trellis.js update \
  --overlay hiskens --create-new 2>&1 | tee /tmp/topo-v0.4.0-snapshot/update.log

# 5. Post-update verify
cat .trellis/.version                          # expect 0.4.0
find . -maxdepth 3 -name '*.new' -not -path './.git/*' -not -path './.venv/*'
find .trellis/tasks .trellis/workspace -type f \
  \( -name "*.md" -o -name "*.json" -o -name "*.jsonl" -o -name "*.yaml" \) \
  -print0 | sort -z | xargs -0 sha256sum > /tmp/topo-v0.4.0-snapshot/post.sha256
diff /tmp/topo-v0.4.0-snapshot/pre.sha256 /tmp/topo-v0.4.0-snapshot/post.sha256

# 6. Conflict resolution (.new files)
# Expected: at least .trellis/worktree.yaml.new + .trellis/.gitignore.new → keep Topo-local
# Others → usually accept upstream (Anhui experience: mostly whitespace)

# 7. Topo validation
uv run ruff check .
uv run ruff format --check .
uv run pytest TopoDetectionBIBC/tests -x --no-header -q
```

### Round 3 Acceptance criteria

- [ ] Phase 0: `dist/templates/claude/hooks/inject-subagent-context.py` contains new "Research is intentionally lightweight" docstring
- [ ] Phase 1: Anhui_CIM post-Round-3 `session-start.py`, `commands/trellis/{start,parallel,finish-work,before-*,check-*}.md`, `agents/{implement,plan}.md` match `overlays/hiskens/templates/...`
- [ ] Phase 1: Anhui_CIM `.claude/hooks/inject-subagent-context.py` contains new docstring
- [ ] Phase 1: Anhui_CIM `.trellis/scripts/task.py` finish path tests pass
- [ ] Phase 1: Anhui_CIM `.trellis/tasks/` and `.trellis/workspace/` digests unchanged
- [ ] Phase 1: Anhui_CIM pytest + nocturne + ruff all pass
- [ ] Phase 2: Topo `.trellis.bak/` and `.claude.bak/` removed; ahead commit pushed to origin
- [ ] Phase 2: Topo `.trellis/.version` = `0.4.0`
- [ ] Phase 2: Topo `.trellis/tasks/` and `.trellis/workspace/` digests unchanged
- [ ] Phase 2: Topo ruff + pytest TopoDetectionBIBC/tests all pass
- [ ] Phase 2: Topo committed + merged to main

### Round 3 Execution log

(append-only)

- **2026-04-15 evening** — Round 3 task activated (`task.py start`); task.json status → `in_progress`, phase 3.
- **Phase 0 complete**: `pnpm run build` in `packages/cli/` succeeded (tsc + copy-templates). Verified `dist/templates/claude/hooks/inject-subagent-context.py` now contains `"Research is intentionally lightweight"` (drift resolved). `dist/cli/index.js` timestamp refreshed.
- **Finding (cross-task, not blocking Round 3)**: b7e2a31 is an incomplete fix. It updated the base template `packages/cli/src/templates/claude/hooks/inject-subagent-context.py` (which defines `get_research_context` inline) and `overlays/hiskens/templates/claude/commands/trellis/start.md` (user-facing gotcha), but the **overlay runtime path** goes through `overlays/hiskens/templates/trellis/scripts/common/context_assembly.py:691` (shared module; the overlay hook imports from here). That file still has the old docstring `"Research doesn't need much preset context"`. Even the sibling planning task `04-15-finish-exit-and-research-gotcha/implement.jsonl` does not list `context_assembly.py` — meaning if that task is implemented as currently scoped, the overlay docstring will **still** be missed. → Action item for `04-15-finish-exit-and-research-gotcha`: add `overlays/hiskens/templates/trellis/scripts/common/context_assembly.py` to its implement.jsonl before implementation. No action required in Round 3.
- **Phase 1 complete (Anhui_CIM Round 3)**:
  - Created branch `trellis-overlay-resync-round3`
  - Ran `update --overlay hiskens --dry-run` → 1 auto-update + 23 "user-modified" conflicts
  - Ran `update --overlay hiskens --create-new` → 23 `.new` files generated, backup at `.trellis/.backup-2026-04-15T14-11-08/`
  - Conflict resolution: 11 accept-upstream (`session-start.py` x2, `agents/{implement,plan}.md`, `codex/agents/plan.toml`, `check-cross-layer{,-base}.md`, `task_context.py`, `context_assembly.py`, `create_bootstrap.py`, `multi_agent/plan.py`) + 12 keep-local (Anhui-specific: `worktree.yaml`, `.gitignore`, `settings.json`, `statusline.py`, `cursor/trellis-finish-work.md`, `update-spec/SKILL.md`, `cli_adapter.py`, `search/*`)
  - **Surprise finding**: only 3 of the 23 "conflicts" had real content diffs vs HEAD — `start.md`, `check-cross-layer.md`, `check-cross-layer-base.md`. The other 20 were **false positives** caused by stale `.template-hashes.json` records; verified by `git hash-object` vs HEAD blob. Round 2 had already absorbed all of c701579's overlay rewrites.
  - Validation: `pytest tests/test_context_assembly.py` → 41 passed; `test_nocturne_client.py` → 6/6; `test_nocturne_integration.py` → all pass; `verify_baseline.py` → 10/10; `ruff check` → 2 import-order issues autofixed in `task_context.py` and `create_bootstrap.py`
  - Commit: `7d73209 chore(trellis): round 3 overlay resync (b7e2a31 gotcha propagation)` — 3 files changed, 6 insertions, 4 deletions
  - Fast-forward merged to Anhui `main`. Anhui now has 3 un-pushed trellis commits (Round 1/2/3) ahead of origin/main — user to push at their discretion.
- **Phase 2 complete (Topo-Reliability initial upgrade)** — delegated to implement agent:
  - Pre-flight: `.trellis.bak/` and `.claude.bak/` removed; `.trellis/.version` confirmed `0.4.0-beta.10`
  - Branch `trellis-update-v0.4.0` created
  - Dry-run: 88 auto-update candidates + 12 "Modified by you" conflicts
  - Execution: `yes | ... update --overlay hiskens --create-new` succeeded; backup at `.trellis/.backup-2026-04-15T14-21-38/`
  - **Conflict resolution (12 `.new` files)** — per-file `git hash-object` diff check:
    - **False positive (2)**: `.trellis/scripts/search/API_CONFIG.md`, `.agents/skills/update-spec/SKILL.md`
    - **Keep-local (7)**: `.trellis/worktree.yaml` (Topo verify hooks), `.trellis/.gitignore` (Topo ignores), `.claude/settings.json` (upstream added GROK_API_URL env; Topo doesn't need), `.codex/config.toml` (upstream added TUI notification config; non-critical), `.claude/commands/trellis/check-cross-layer{,-base}.md` (trailing-whitespace-only diff), `.claude/agents/research.md` (only diff is `model: opus → sonnet`; Topo prefers opus)
    - **Accept upstream (2)**: `.claude/agents/plan.md` (c701579 package-scoped workflow + `PLAN_PACKAGE` env var), `.claude/commands/trellis/finish-work.md` (package-scoped spec updates + `uv run` unification)
    - **Accept upstream + patch (1)**: `.claude/agents/implement.md` — accepted package-scoped spec references, then `sed` restored `model: opus` over upstream `model: sonnet`
  - Post-update: `.trellis/.version` = `0.4.0`; tasks/workspace digests (229 files) byte-identical pre/post; executable bits preserved
  - Validation: `ruff check` clean (no autofix needed, unlike Phase 1); `ruff format --check` pass; `pytest TopoDetectionBIBC/tests` → **10 passed** in 120.25s (pre-existing pandapower DeprecationWarnings unrelated)
  - Commit: `6238adf chore(trellis): update to v0.4.0 (hiskens overlay, round 3)` — 26 files changed, 1175 insertions, 494 deletions
  - Fast-forward merged to Topo `main` (`4cf5b2f..6238adf`). Topo now has 1 un-pushed commit ahead of origin/main.
- **Round 3 surprises / learnings**:
  - **Real-diff ratio differs dramatically**: Anhui Round 3 = 3/23 (13%), Topo Phase 2 = 10/12 (83%). The difference is Anhui had already absorbed c701579 in Round 2; Topo was jumping `beta.10 → 0.4.0` in one shot, so it got the full c701579 + rc.0/rc.1 backlog.
  - **Upstream v0.4.0 flips several agents `opus → sonnet`** (research.md, implement.md). Both Topo and Anhui have an implicit preference for `opus`. This is a recurring drift point worth spec-ing. See action items below.
  - **CRLF vs LF warnings on `/mnt/e/`**: autocrlf=true triggers `"LF will be replaced by CRLF"` warnings for ~46 files during `git add` on Topo. Blob content is correct; warning is cosmetic.
  - **Trellis update auto-update count ≠ actually modified file count**: dry-run "88 auto-update candidates" produced only 26 real file changes. Rest were byte-identical writes. Cosmetic reporting artifact.
  - **Topo ships no `test_nocturne_*` harness** (unlike Anhui), so no contract-drift test-fix was needed.
  - **Interactive prompt confirmed**: `trellis update` hangs without stdin. `yes |` pattern is the correct invocation for scripted/agent use.


