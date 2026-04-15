# Sync hiskens overlay drift after upstream v0.4.0 merge

## Goal

Resolve semantic drift between `overlays/hiskens/templates/` and upstream's v0.4.0 updates to corresponding source files. After the upstream sync merge (`6ef8e5b`), three overlay mirrors need manual reconciliation because the overlay versions were derived from v0.4.0-beta.10 and upstream has since changed the upstream originals.

## Context

- **Merge commit**: `6ef8e5b merge: sync upstream v0.4.0 into hiskens fork`
- **Merge-base**: `737f750` (v0.4.0-beta.10)
- **Branch**: `sync/upstream-v0.4.0`
- **Overlay dir**: `overlays/hiskens/templates/`
- **Total drift inventory**: 4 files; 1 already resolved via alternate implementation; 3 actionable.

## Requirements

### R1 — Port upstream workflow.md TOC refactor into overlay session-start.py (claude)

**File**: `overlays/hiskens/templates/claude/hooks/session-start.py` (432 lines)

**Upstream change** (`packages/cli/src/templates/claude/hooks/session-start.py`, +29/−12):
- Introduced `_build_workflow_toc()` helper that returns only `## ` section headers from `workflow.md`, prefixed with instructions to use the Read tool for full content.
- Replaced `read_file(trellis_dir / "workflow.md")` (full injection) with `_build_workflow_toc(trellis_dir / "workflow.md")`.
- Removed `<instructions>` block that inlined `.claude/commands/trellis/start.md`.
- Updated `<ready>` banner text to match (no more "Steps 1-3" / "Step 4" language).

**Observable symptom in current overlay**: SessionStart hook additionalContext exceeds 34KB per session because overlay still full-injects workflow.md.

**Constraint**: The overlay file is a hiskens-specific rewrite and may contain customizations that MUST be preserved. The port should be **surgical**: only touch the workflow injection path and the `<ready>` banner. Do not mass-replace the file with upstream's version.

### R2 — Port upstream workflow.md TOC refactor into overlay session-start.py (codex)

**File**: `overlays/hiskens/templates/codex/hooks/session-start.py` (205 lines)

Same refactor as R1, plus remove the codex-specific start-skill injection block (upstream dropped it). Same surgical approach; preserve hiskens customizations.

### R3 — Port upstream droid platform support into overlay cli_adapter.py

**File**: `overlays/hiskens/templates/trellis/scripts/common/cli_adapter.py` (648 lines)

**Upstream change** (`packages/cli/src/templates/trellis/scripts/common/cli_adapter.py`, +27/−2):
- Added `"droid"` to `Platform = Literal[...]` union.
- Added droid branches in 5 methods:
  - `config_dir_name` → returns `.factory`
  - `command_path` → returns `.factory/commands/trellis/{name}.md`
  - `env_for_cli` → returns `{}`
  - `run_agent` → raises "not yet integrated"
  - `resume_session` → raises "not yet integrated"
  - `platform_name_display` (or similar — verify exact method name during implementation)
- Updated module docstring to mention Factory Droid.

**Constraint**: The overlay cli_adapter is larger than upstream (648 vs ~500 lines). Do not disturb hiskens customizations; only add droid branches where upstream added them and in the same positions relative to existing branches.

## Out of scope (explicitly not doing in this task)

- ❌ `overlays/hiskens/templates/claude/hooks/statusline-bridge.py` — already has GBK fix via `sys.stdout.reconfigure("utf-8")` (more modern than upstream's `io.TextIOWrapper` approach). No action.
- ❌ opencode / iflow / copilot hook updates — upstream changed these but overlay has no mirror, no drift.
- ❌ droid overlay directory creation (`overlays/hiskens/templates/droid/`) — the fork's hiskens overlay can add droid customizations in a future task if/when you actually adopt droid as a platform.
- ❌ Merging `sync/upstream-v0.4.0` into `main` — user wants to review drift resolution first.

## Acceptance Criteria

- [ ] **R1**: `overlays/hiskens/templates/claude/hooks/session-start.py` uses `_build_workflow_toc()` instead of full `workflow.md` injection; removes the inlined `<instructions>` start.md block; updates `<ready>` banner text.
- [ ] **R2**: `overlays/hiskens/templates/codex/hooks/session-start.py` uses `_build_workflow_toc()`; removes the start-skill injection block.
- [ ] **R3**: `overlays/hiskens/templates/trellis/scripts/common/cli_adapter.py` has full droid platform support matching upstream's additions (type literal + 5 method branches + docstring).
- [ ] Python files parse clean (`python3 -m py_compile` on each).
- [ ] All overlay files retain their pre-existing hiskens customizations (verify with `git diff --stat` — only the upstream-port-related lines should change; no accidental removals).
- [ ] `packages/cli` test suite still 624/624 green (overlay templates are text-embedded, so they shouldn't break cli tests, but verify).
- [ ] SessionStart hook additionalContext size is measurably smaller after R1+R2 (sanity-check the hook output file in the next session or via a direct script run).

## Technical Notes

- **Merge-base SHA for reference**: `737f7508f073ebd5d8a2a76f4bbd3c4aacc8793e`
- **Upstream v0.4.0 tip**: `5a08d67`
- **Three-way diff workflow for each file**:
  ```
  git show 737f750:<upstream_source_path>  # old upstream (what overlay was derived from)
  git show 5a08d67:<upstream_source_path>  # new upstream (with v0.4.0 changes)
  cat overlays/hiskens/templates/<overlay_path>  # current overlay (heavily customized)
  ```
- **Strategy**: Do NOT attempt a 3-way merge tool. Read the upstream diff, identify the exact lines to change in the overlay, and make targeted edits. Overlay files are customized enough that automated merges will produce garbage.
- **Order**: Tackle in order R1 → R2 → R3. R1 and R2 share the same refactor pattern (port helper function + change one call site + remove one block). R3 is independent.
- **Risk**: R1/R2 may be non-trivial if the overlay session-start files have their own workflow-injection logic that conflicts with the TOC approach. Implementer must read the overlay files fully before editing to understand the hiskens customizations.
