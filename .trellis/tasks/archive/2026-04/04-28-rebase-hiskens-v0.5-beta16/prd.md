# Rebase Hiskens Overlay to v0.5.0-beta.16

## Goal
Rebase PR #2 (`migrate/hiskens-v0.5`, based on `v0.5.0-beta.15`) onto `v0.5.0-beta.16` as a new branch `migrate/hiskens-v0.6`, resolving conflicts and incorporating 5 upstream bugfixes/features.

## Context
- PR #2 implements a small-patch overlay rebuild: generic overlay-loader + lightweight hiskens customization
- Between beta.15 and beta.16: 30 commits, 253 files changed (+18.7k / -7.1k)
- Overlay-relevant: 70 files changed (+3.6k / -776)

## Upstream Changes to Incorporate (beta.15 → beta.16)

| Commit | Description | Impact |
|--------|-------------|--------|
| `693db45` | `feat(task): scope active task state by session` | HIGH — changes `.current-task` to session-scoped |
| `6468b96` | `fix(update): preserve Claude statusline installs` | HIGH — modifies `update.ts` (same file PR touches) |
| `ccfcbdf` | `fix(cli): normalize hash keys to POSIX/LF for Windows` | MEDIUM — `template-hash.ts` |
| `431edbe` | `fix(scripts): align task.py archive input contract` | MEDIUM — task.py/task_store contract |
| `f931aa3` | `fix: support git-backed private registries` | LOW — template-fetcher.ts |

## Known Conflict Points

1. **`commands/update.ts`** (HIGH) — PR adds overlay loader hooks in `collectTemplateFiles()`; beta.16 adds statusline preservation in same region
2. **`commands/init.ts`** (MEDIUM) — PR adds overlay init flow; beta.16 adds registry fix (likely different regions)
3. **Overlay `paths.py`** (semantic) — overlay version lacks `normalize_task_ref`/`resolve_task_ref` that upstream beta.15 has; beta.16 adds session-scoping on top

## Execution Plan

### Step 1: Rebase onto beta.16
```bash
git rebase --onto v0.5.0-beta.16 v0.5.0-beta.15 migrate/hiskens-v0.6
```
This replays the 4 PR commits onto beta.16.

### Step 2: Resolve conflicts
- `update.ts`: accept beta.16 statusline preservation, re-apply overlay parameter injection
- `init.ts`: likely auto-merge; verify overlay flow still correct
- Other files: accept beta.16 changes, verify overlay content unaffected

### Step 3: Update overlay metadata
- `overlay.yaml`: update `compatible_upstream` to `>=0.5.0-beta.16 <0.6.0`

### Step 4: Sync overlay Python scripts
- `paths.py`: align with upstream's `normalize_task_ref`/`resolve_task_ref` + session-scoping
- `task_utils.py`: add backslash normalization from upstream

### Step 5: Validate
- `pnpm install && pnpm build && pnpm test`
- `python3 -m py_compile overlays/hiskens/templates/claude/hooks/*.py`
- Verify overlay init/update flow works

## Acceptance Criteria
- [ ] All 4 PR commits cleanly rebased onto beta.16
- [ ] `pnpm build && pnpm test` passes
- [ ] `overlay.yaml` compatible_upstream updated
- [ ] Overlay Python scripts aligned with beta.16 upstream
- [ ] No regressions in existing test coverage (770+ tests)

## Out of Scope
- Downstream consumer propagation
- New overlay features beyond what PR #2 already has
