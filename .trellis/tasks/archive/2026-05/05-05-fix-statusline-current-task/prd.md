# Fix statusline _get_current_task to use session-aware resolver

## Problem

`_get_current_task()` in `packages/cli/src/templates/shared-hooks/statusline.py` (L92-108) reads the deprecated `.trellis/.current-task` file. Since `task.py start` now writes session-scoped state via `set_active_task()` → `.trellis/.runtime/sessions/<context_key>.json`, the statusline never shows the active task.

## Solution

Replace the `.current-task` file read with a call to `resolve_active_task()` from `common.active_task`, passing the stdin JSON (`cc_data`) as `platform_input`. This is the same pattern already proven in `inject-workflow-state.py`.

## Scope

- **Change**: `packages/cli/src/templates/shared-hooks/statusline.py` — rewrite `_get_current_task()` to use session resolver
- **No fallback** to `.current-task` file (deprecated, never written to)
- **No change** to `.claude/hooks/statusline.py` directly (synced via overlay)

## Implementation

1. Add sys.path manipulation to import `common.active_task.resolve_active_task` (same pattern as `inject-workflow-state.py` L97-103)
2. Change `_get_current_task(trellis_dir)` → `_get_current_task(trellis_dir, cc_data)` 
3. Call `resolve_active_task(repo_root, cc_data, platform=<detected>)` to get active task
4. Update call site in `main()` to pass `cc_data`

## Verification

- `task.py start <dir>` → statusline shows task title/status/priority
- No active session → statusline omits task line (same as before)
