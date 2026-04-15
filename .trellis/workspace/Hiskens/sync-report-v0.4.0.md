# Hiskens Overlay Sync Report — Upstream v0.4.0

## Merge Metadata

- **Merge commit**: `6ef8e5b` (merge: sync upstream v0.4.0 into hiskens fork)
- **Merge-base**: `737f750` (v0.4.0-beta.10)
- **Upstream tip**: `5a08d67`
- **Sync branch**: `sync/upstream-v0.4.0`
- **Resolution date**: 2026-04-15
- **Task**: `04-15-overlay-drift-v0.4.0`

## Drift Inventory

| # | Overlay file | Upstream change | Status |
|---|---|---|---|
| 1 | `claude/hooks/session-start.py` | `_build_workflow_toc` refactor + `<ready>` banner update | Resolved (R1) |
| 2 | `codex/hooks/session-start.py` | `_build_workflow_toc` refactor + drop start-skill block | Resolved (R2) |
| 3 | `trellis/scripts/common/cli_adapter.py` | Add `droid` (Factory Droid) platform support | Resolved (R3) |
| 4 | `claude/hooks/statusline-bridge.py` | Upstream GBK fix via `io.TextIOWrapper` | Skipped — overlay already has equivalent fix via `sys.stdout.reconfigure("utf-8")` (more modern) |

## Diff Summary

```
overlays/hiskens/templates/claude/hooks/session-start.py        | 45 +++++++++-------
overlays/hiskens/templates/codex/hooks/session-start.py         | 43 +++++++++------
overlays/hiskens/templates/trellis/scripts/common/cli_adapter.py| 36 ++++++++++---
3 files changed, 91 insertions(+), 33 deletions(-)
```

Within expected envelope.

## Guardrail Verification

### R1 — claude session-start.py

- [x] No `hookSpecificOutput` / `json.dumps` (still plain `print()` to stdout — claude hook design)
- [x] `get_nocturne_context` present (line 110)
- [x] `get_memory_summary` present (line 62)
- [x] `get_stale_session_warning` present (line 238)
- [x] `<thinking-framework>` block present (lines 373–405)
- [x] `_get_task_status` NOT present (0 hits)
- [x] `_load_trellis_config`, `_check_legacy_spec`, `_resolve_spec_scope` NOT present (0 hits)
- [x] `_build_workflow_toc` function added (line 300)
- [x] `main()` calls `_build_workflow_toc(trellis_dir / "workflow.md")` (line 410), full `read_file(...workflow.md...)` removed
- [x] `<instructions>` block reading `claude_dir/commands/trellis/start.md` removed (0 hits)
- [x] Dead `claude_dir = project_dir / ".claude"` removed
- [x] `<ready>` banner uses upstream's new text — no "Steps 1-3" / "Step 4" language

### R2 — codex session-start.py

- [x] Overlay's simpler `_get_task_status()` retained (line 54)
- [x] `_normalize_task_ref` NOT present (0 hits)
- [x] `_resolve_task_dir` NOT present (0 hits)
- [x] `_build_workflow_toc` function added (line 105)
- [x] `main()` calls `_build_workflow_toc` for workflow injection (line 159)
- [x] `start/SKILL.md` block removed (0 hits)
- [x] `codex_dir = project_dir / ".codex"` removed
- [x] `<ready>` banner updated to upstream text
- [x] Note: codex hook intentionally keeps `hookSpecificOutput` JSON envelope — this is its protocol, not a guardrail violation

### R3 — cli_adapter.py

- [x] `"droid"` in `Platform = Literal[...]` (line 49)
- [x] `"droid"` branch in `config_dir_name` (line 116)
- [x] `"droid"` branch in `get_trellis_command_path` (line 213)
- [x] `"droid"` branch in `get_non_interactive_env` (line 244)
- [x] `"droid"` branch in `build_run_command` (line 317) raising `"Factory Droid CLI agent run is not yet integrated with Trellis multi-agent."`
- [x] `"droid"` branch in `build_resume_command` (line 373) raising `"Factory Droid CLI resume is not yet integrated with Trellis multi-agent."`
- [x] `"droid"` branch in `cli_name` (lines 443–444)
- [x] `"droid"` in `get_cli_adapter` factory validation (lines 509, 529, 532)
- [x] `"droid"` in `_ALL_PLATFORM_CONFIG_DIRS` / detect_platform env tuple (line 605)
- [x] `"droid"` body branch in `detect_platform` `.factory` dir probe (line 659)
- [x] `"droid"` in detect_platform docstring (lines 580, 587)
- [x] `"droid"` in module docstring header (line 18 — "droid: Factory Droid (commands-based)")
- [x] No `"windsurf"` added (0 hits)
- [x] No `"copilot"` added (0 hits)
- [x] Both ValueError messages match upstream verbatim

## Test Results

- **`python3 -m py_compile`**: All 3 modified files compile clean (zero errors)
- **`pnpm typecheck`** in `packages/cli`: clean (zero errors, `tsc --noEmit` exit 0)
- **`pnpm test`** in `packages/cli`: **624/624 passed** (31 test files, ~2.4s)
  - Including `test/regression.test.ts > [current-task] Python session-start hooks resolve legacy backslash refs without stale pointer`
- **`pnpm lint`** in `packages/cli`: **5 pre-existing errors in `test/utils/overlay.test.ts`** (unrelated to this task — file last modified in commit `ca4267d` "feat: add hiskens overlay templates and loader", before this task started). Errors:
  - 1× `@typescript-eslint/no-empty-function` (line 43, empty arrow in `mockImplementation(() => {})`)
  - 4× `@typescript-eslint/no-non-null-assertion` (lines 53, 62, 75, 77 — `overlayPath!` and `templatePath!`)
  - **Not fixed by this task** — out of PRD scope (R1/R2/R3 are Python-only). Recommended as separate follow-up task.

## Known Pre-existing Noise (Not Introduced By This Task)

- `ty` static type checker warnings about `nocturne_client` and `yaml` imports in `claude/hooks/session-start.py` — these are template-vs-runtime path artifacts. The overlay is a template embedded as text in the cli package; the imports resolve only after the template is materialized into a target project. Confirmed pre-existing before this task.

## Recommended Follow-up

1. **Pre-existing lint debt (medium priority)**: Fix the 5 ESLint errors in `packages/cli/test/utils/overlay.test.ts` (1× empty arrow function, 4× non-null assertion). These were introduced in the hiskens overlay loader commit (`ca4267d`) and block clean lint runs. Trivial fix: replace `() => {}` with `() => undefined` and replace `x!` with `if (x) { ... }` guards or `expect(x).not.toBeNull()` followed by typed local.
2. **Future task (low priority)**: Configure `ty` to ignore `overlays/` directory (or add per-file `# ty: ignore` markers) to silence the nocturne_client/yaml false positives. Not blocking.
3. **Future task (deferred)**: If the fork ever adopts Factory Droid as a real platform, add `overlays/hiskens/templates/droid/` with hiskens-specific droid customizations (currently no overlay mirror exists).
4. **Manual verification**: After next session start, sanity-check that `additionalContext` size from claude SessionStart hook is measurably smaller (workflow.md TOC vs full file) — should drop ~25-30KB.

## Conclusion

All 3 actionable drift items resolved. All guardrails verified. Test suite green. Ready for merge into `main` after user review.
