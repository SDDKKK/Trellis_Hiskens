# PRD: Restore CCR Model Routing in inject-subagent-context Hook

## Problem

The `trellis update` on 2026-05-05 (sync upstream v0.6.0-beta.9) overwrote the hiskens overlay's CCR (Claude Code Router) routing code in `inject-subagent-context.py`. Three functions and two call sites were silently dropped:

- `_load_features()` — loads feature flags from `.trellis/config.yaml`
- `_ccr_model_keys()` — maps subagent type to model key aliases
- `get_ccr_model_tag()` — reads `.trellis/config/agent-models.json`, emits `<CCR-SUBAGENT-MODEL>` tag

As a result, `agent-models.json` is dead config in all projects (ZZ_KKX, etc.) — the file exists but nothing reads it.

## Root Cause

CCR routing was only in project-side hook files, NOT in the shared template at `packages/cli/src/templates/shared-hooks/inject-subagent-context.py`. When `trellis update` replaced hook files with the upstream template, the CCR code vanished. The overlay skill (`trellis-overlay/SKILL.md`) does not list CCR routing as a customization point, so the verification checklist missed it.

## Requirements

### R1: Restore CCR functions in shared template
Add the three CCR functions to `packages/cli/src/templates/shared-hooks/inject-subagent-context.py`:
- `_load_features(repo_root)` → parse `.trellis/config.yaml` features section
- `_ccr_model_keys(subagent_type)` → alias mapping for model lookup
- `get_ccr_model_tag(repo_root, subagent_type)` → 3-guard check (feature flag + localhost base URL + config file), return XML tag or empty string

Source of truth: `.trellis/.backup-2026-05-05T11-22-48/.claude/hooks/inject-subagent-context.py` lines 133–207.

### R2: Restore call sites in shared template main()
- Call `ccr_tag = get_ccr_model_tag(repo_root, subagent_type)` after `find_repo_root()`
- Prepend `ccr_tag` to `new_prompt` before output assembly

Source of truth: backup lines 758, 800–801.

### R3: Propagate to platform hook copies
After template update, re-run `trellis update` (or manually copy) to sync:
- `.claude/hooks/inject-subagent-context.py`
- `.cursor/hooks/inject-subagent-context.py`

### R4: Update overlay skill
Add CCR routing as customization point #5 in `.claude/skills/trellis-overlay/SKILL.md` so future sync verifications check for it.

## Acceptance Criteria

1. `grep "get_ccr_model_tag" packages/cli/src/templates/shared-hooks/inject-subagent-context.py` returns a match
2. `grep "get_ccr_model_tag" .claude/hooks/inject-subagent-context.py` returns a match
3. With `features.ccr_routing: true` in config.yaml + localhost ANTHROPIC_BASE_URL + valid `agent-models.json`, the hook output includes `<CCR-SUBAGENT-MODEL>` tag in the prompt
4. Without any of the 3 guards, the hook behaves identically to upstream (no tag, no error)
5. Overlay skill lists CCR routing as a verification checkpoint

## Out of Scope

- Changing the CCR tag format or guard logic (restore as-was)
- Downstream project updates (separate `trellis update` per project)
- `update.skip` protection for hooks (separate concern)
