# Research: Overlay Stale Audit vs Upstream v0.5.0-beta.18

- **Query**: Full audit of `overlays/hiskens/templates/` against upstream v0.5.0-beta.18
- **Scope**: internal
- **Date**: 2026-04-29

---

## Summary

The overlay was built on top of an older upstream (roughly beta.5–beta.10 era). Upstream removed
the multi-agent pipeline, Ralph Loop, dispatch agent, and plan agent in commit `efccf6f`
("feat: add hooks + agents for 7 platforms, remove iFlow/multi-agent/Ralph Loop"). The overlay
still carries all of those. Additionally the overlay `agents/skills/trellis-meta` and
`claude/skills/trellis-meta` both track the beta.5 version of that skill (header says
`0.3.0-beta.5` / `2026-01-31`), while upstream significantly restructured its reference tree in
later betas.

Key structural change: upstream renamed all core agents to `trellis-*` prefix. Overlay still
ships the old bare names (`check`, `debug`, `dispatch`, `implement`, `plan`, `research`,
`review`, `codex-implement`).

---

## Master Table: All Overlay Files

### 1. `claude/agents/` — Old-name agents (8 files)

| File | Upstream equivalent at beta.18 | Status | Recommended Action |
|---|---|---|---|
| `claude/agents/check.md` | `.claude/agents/trellis-check.md` | **STALE — old name** | REMOVE |
| `claude/agents/debug.md` | None (debug was removed upstream) | **STALE — removed upstream** | REMOVE |
| `claude/agents/dispatch.md` | None (removed in `efccf6f`) | **STALE — removed upstream** | REMOVE |
| `claude/agents/implement.md` | `.claude/agents/trellis-implement.md` | **STALE — old name** | REMOVE |
| `claude/agents/plan.md` | None (removed in `efccf6f`) | **STALE — removed upstream** | REMOVE |
| `claude/agents/research.md` | `.claude/agents/trellis-research.md` | **STALE — old name** | REMOVE |
| `claude/agents/review.md` | None (upstream has no review agent) | Hiskens-specific but listed in `exclude.yaml` | KEEP (already excluded by `exclude.yaml`) |
| `claude/agents/codex-implement.md` | None | **Hiskens-specific addition** | KEEP (but confirm it still works with beta.18 hooks) |

Notes:
- `check.md`, `implement.md`, `research.md` have old `name:` values in frontmatter (`check`, `implement`, `research`). Upstream now uses `trellis-check`, `trellis-implement`, `trellis-research`. Installing these would shadow upstream agents under wrong names.
- `debug.md`, `dispatch.md`, `plan.md` were explicitly deleted upstream ("remove iFlow/multi-agent/Ralph Loop"). They implement a multi-agent pipeline architecture that no longer exists in beta.18.
- `review.md` is already excluded via `exclude.yaml` — no action needed.

### 2. `codex/agents/` — Old-name codex agents (6 files)

| File | Upstream equivalent at beta.18 | Status | Recommended Action |
|---|---|---|---|
| `codex/agents/check.toml` | `.codex/agents/trellis-check.toml` | **STALE — old name** | REMOVE |
| `codex/agents/debug.toml` | None (removed upstream) | **STALE — removed upstream** | REMOVE |
| `codex/agents/implement.toml` | `.codex/agents/trellis-implement.toml` | **STALE — old name** | REMOVE |
| `codex/agents/plan.toml` | None (removed upstream) | **STALE — removed upstream** | REMOVE |
| `codex/agents/research.toml` | `.codex/agents/trellis-research.toml` | **STALE — old name** | REMOVE |
| `codex/agents/review.toml` | None | **Hiskens-specific addition** | KEEP (if used) |

### 3. `claude/commands/trellis/` — Commands (20 files)

Upstream beta.18 provides: `continue.md`, `create-manifest.md`, `finish-work.md`, `improve-ut.md`, `publish-skill.md`

| File | In Upstream? | Status | Recommended Action |
|---|---|---|---|
| `finish-work.md` | YES but different content | **OVERRIDE** — overlay version is a pre-commit checklist; upstream is a session-wrap command | KEEP (genuine content difference) |
| `improve-ut.md` | YES but different content | **OVERRIDE** — different scope/flow | KEEP (genuine content difference) |
| `start.md` | NO | **Hiskens addition** | KEEP |
| `update-spec.md` | NO | **Hiskens addition** | KEEP |
| `brainstorm.md` | NO (upstream has skill, not command) | **Hiskens addition** | KEEP |
| `brainstorm-base.md` | NO | **Hiskens addition** | KEEP |
| `break-loop.md` | NO (upstream has skill, not command) | **Hiskens addition** | KEEP |
| `break-loop-base.md` | NO | **Hiskens addition** | KEEP |
| `check-cross-layer.md` | NO | **Hiskens addition** | KEEP |
| `check-cross-layer-base.md` | NO | **Hiskens addition** | KEEP |
| `check-matlab.md` | NO | **Hiskens addition** | KEEP |
| `check-python.md` | NO | **Hiskens addition** | KEEP |
| `before-matlab-dev.md` | NO | **Hiskens addition** | KEEP |
| `before-python-dev.md` | NO | **Hiskens addition** | KEEP |
| `create-command.md` | NO | **Hiskens addition** | KEEP |
| `integrate-skill.md` | NO | **Hiskens addition** | KEEP |
| `onboard.md` | NO | **Hiskens addition** | KEEP |
| `parallel.md` | NO (parallel skill/multi-agent removed upstream) | **STALE — references removed multi-agent pipeline** | INVESTIGATE (may reference dispatch/plan agents) |
| `record-session.md` | NO | **Hiskens addition** | KEEP |
| `retro.md` | NO | **Hiskens addition** | KEEP |

Note: `parallel.md` should be checked — its content may invoke `dispatch` or `plan` agents that no longer exist in beta.18. If so, it is stale.

### 4. `claude/hooks/` — Hook files (9 Python files + `__pycache__/`)

Upstream beta.18 provides: `inject-subagent-context.py`, `inject-workflow-state.py`, `session-start.py`

| File | Upstream equivalent | Status | Notes |
|---|---|---|---|
| `inject-subagent-context.py` | YES — upstream `inject-subagent-context.py` | **OVERRIDE** (+98 lines vs upstream) | Overlay adds `_load_features()` for CCR routing, updated docstring for trellis-* agent names. Genuine functional addition. KEEP |
| `session-start.py` | YES — upstream `session-start.py` | **OVERRIDE** (modified) | Overlay adds `FIRST_REPLY_NOTICE` (Chinese session start prompt), `configure_project_encoding()` helper, moves `warnings` import earlier. Hiskens-specific customization. KEEP |
| `ralph-loop.py` | NO — **explicitly deleted** in `efccf6f` | **STALE — removed upstream** | 20-line header says "SubagentStop Hook for Check/Review Agent Loop Control". Upstream commit message says "remove Ralph Loop". Not referenced in `settings.overlay.json`. REMOVE |
| `context-monitor.py` | NO | **Hiskens addition** | Referenced in `settings.overlay.json` PostToolUse. Reads from statusline bridge file to warn about context exhaustion. KEEP |
| `intent-gate.py` | NO | **Hiskens addition** | Referenced in `settings.overlay.json` UserPromptSubmit. KEEP |
| `todo-enforcer.py` | NO | **Hiskens addition** | Referenced in `settings.overlay.json` PostToolUse + Stop. KEEP |
| `statusline.py` | NO | **Hiskens addition** | Referenced only by `context-monitor.py` and `statusline-bridge.py` — part of context monitoring subsystem. Not in `settings.overlay.json`. KEEP |
| `statusline-bridge.py` | NO | **Hiskens addition** | Part of context monitoring subsystem; writes `/tmp/claude-ctx-{session_id}.json` bridge file for `context-monitor.py`. KEEP |
| `parse_sub2api_usage.py` | NO | **Hiskens addition** | Not referenced in `settings.overlay.json`. Unclear if actively used. INVESTIGATE |
| `__pycache__/` (all `.pyc` files) | N/A | **Should not be in template** | Compiled bytecode should not be installed into user projects. REMOVE ALL `.pyc` files |

### 5. `claude/settings.overlay.json`

| Item | Status | Notes |
|---|---|---|
| `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` | Current | Valid env flag |
| `ENABLE_TOOL_SEARCH` | Current | Valid env flag |
| `enabledPlugins` | Current | Hiskens-specific plugin set |
| `model: opus[1m]` | Current | Hiskens preference |
| `hooks.UserPromptSubmit → intent-gate.py` | OK | File exists in overlay |
| `hooks.PreToolUse → rtk hook claude` | OK | rtk is Hiskens-specific tool |
| `hooks.PostToolUse → todo-enforcer.py` | OK | File exists |
| `hooks.PostToolUse → context-monitor.py` | OK | File exists |
| `hooks.Stop → todo-enforcer.py` | OK | File exists |
| Missing: `inject-subagent-context.py` hook | **GAP** | Upstream registers this in `settings.json` under PreToolUse for Task+Agent matchers. Overlay's `settings.overlay.json` does NOT wire it, so the CCR feature in the overlay's `inject-subagent-context.py` may not be triggered. |
| Missing: `session-start.py` hook | **GAP** | Upstream registers this in `settings.json` under SessionStart. Overlay has modified `session-start.py` but does not register it in `settings.overlay.json`. |

### 6. `claude/skills/` — Claude-local skills (5 directories)

| Directory | In Upstream? | Status | Notes |
|---|---|---|---|
| `claude/skills/trellis-meta/` | YES — upstream has `trellis-meta` skill | **STALE OVERRIDE** — overlay version says `0.3.0-beta.5 / 2026-01-31`. Upstream has been restructured (new `customize-local/`, `local-architecture/`, `platform-files/` ref dirs). | REMOVE (let upstream provide it) |
| `claude/skills/fork-sync-strategy/` | NO | **Hiskens-specific addition** | KEEP |
| `claude/skills/github-explorer/` | NO | **Hiskens addition** | KEEP |
| `claude/skills/grok-search/` | NO | **Hiskens addition** | KEEP |
| `claude/skills/with-codex/` | NO | **Hiskens addition** | KEEP |

### 7. `agents/skills/` — Global shared skill layer (11 directories)

Upstream beta.18 `agents/skills/` provides: `contribute`, `first-principles-thinking`, `python-design`, `trellis-before-dev`, `trellis-brainstorm`, `trellis-break-loop`, `trellis-check`, `trellis-continue`, `trellis-finish-work`, `trellis-meta`, `trellis-update-spec`

| Directory | In Upstream? | Status | Notes |
|---|---|---|---|
| `agents/skills/trellis-meta/` | YES — upstream has it | **STALE OVERRIDE** — overlay version is old (beta.5 era). Missing `customize-local/`, `local-architecture/`, `platform-files/` reference subdirs that upstream added. SKILL.md description text differs significantly. | REMOVE (let upstream provide it) |
| `agents/skills/before-matlab-dev/` | NO | **Hiskens addition** | KEEP |
| `agents/skills/before-python-dev/` | NO | **Hiskens addition** | KEEP |
| `agents/skills/brainstorm/` | NO (upstream has `trellis-brainstorm`) | **Hiskens addition** (non-trellis-prefixed version) | KEEP if content differs from upstream `trellis-brainstorm` |
| `agents/skills/check-matlab/` | NO | **Hiskens addition** | KEEP |
| `agents/skills/check-python/` | NO | **Hiskens addition** | KEEP |
| `agents/skills/finish-work/` | NO (upstream has `trellis-finish-work`) | **Hiskens addition** or old alias | INVESTIGATE content overlap with upstream `trellis-finish-work` |
| `agents/skills/improve-ut/` | NO | **Hiskens addition** | KEEP |
| `agents/skills/parallel/` | NO (parallel was removed upstream in `efccf6f`) | **STALE — removed upstream** | INVESTIGATE (may reference dispatch/multi-agent) |
| `agents/skills/record-session/` | NO | **Hiskens addition** | KEEP |
| `agents/skills/retro/` | NO | **Hiskens addition** | KEEP |

### 8. `codex/hooks/` and `codex/` (4 files)

| File | Upstream equivalent | Status | Notes |
|---|---|---|---|
| `codex/hooks/session-start.py` | YES — upstream `session-start.py` | **OVERRIDE** — overlay adds `FIRST_REPLY_NOTICE` Chinese prompt, `configure_project_encoding()`, `LEGACY_MONOREPO_SPEC_MOVES` dict | Hiskens-specific. KEEP |
| `codex/hooks/post-tool-use.py` | NO (upstream has `inject-workflow-state.py` instead) | **Hiskens addition** | KEEP |
| `codex/hooks.json` | YES — upstream `hooks.json` | **OVERRIDE** — overlay replaces `UserPromptSubmit → inject-workflow-state.py` with `PostToolUse → post-tool-use.py` | Structural difference. KEEP (intentional replacement) |
| `codex/scripts/load-trellis-context.py` | NO (upstream has no `codex/scripts/`) | **Hiskens addition** | KEEP |

### 9. `trellis/scripts/` — Core Python scripts

#### Top-level scripts

| File | In Upstream beta.18? | Status | Notes |
|---|---|---|---|
| `add_session.py` | YES | Likely modified version | Compare separately |
| `create_bootstrap.py` | **DELETED** from upstream (commit `b323e93` "remove create_bootstrap.py") | **STALE — removed upstream** | REMOVE unless Hiskens uses it for nocturne workflow |
| `get_context.py` | YES | **OVERRIDE** — trivial whitespace diff (one blank line), functionally same | KEEP (or let upstream version win) |
| `get_developer.py` | YES | Present in upstream | Compare separately |
| `init_developer.py` | YES | Present in upstream | Compare separately |
| `init-nocturne-namespace.py` | NO | **Hiskens addition** (Nocturne memory integration) | KEEP |
| `nocturne_client.py` | NO | **Hiskens addition** (Nocturne SQLite client) | KEEP |
| `promote-to-nocturne.py` | NO | **Hiskens addition** | KEEP |
| `sync-trellis-to-nocturne.py` | NO | **Hiskens addition** | KEEP |
| `task.py` | YES | **OVERRIDE** — overlay version has `init-context`, `complete`, `set-status`, `create-pr` subcommands not in upstream | Genuine functional extension. KEEP |
| `__init__.py` | YES | Likely identical | KEEP |

#### `trellis/scripts/multi_agent/` — 6 files

All of these were **explicitly deleted** in upstream commit `efccf6f`:

| File | Status |
|---|---|
| `multi_agent/__init__.py` | **STALE — removed upstream** |
| `multi_agent/cleanup.py` | **STALE — removed upstream** |
| `multi_agent/create_pr.py` | **STALE — removed upstream** |
| `multi_agent/plan.py` | **STALE — removed upstream** |
| `multi_agent/start.py` | **STALE — removed upstream** |
| `multi_agent/status.py` | **STALE — removed upstream** |

Upstream commit message: "remove iFlow/multi-agent/Ralph Loop — debug/plan/dispatch agents (unused)".

Recommended action: **REMOVE all** — unless Hiskens has an active multi-agent workflow that depends on them (but no active task in the overlay appears to use dispatch/plan/multi_agent anymore).

#### `trellis/scripts/search/` — 4 files (not in upstream)

| File | Status |
|---|---|
| `search/API_CONFIG.md` | **Hiskens addition** |
| `search/_common.py` | **Hiskens addition** |
| `search/web_fetch.py` | **Hiskens addition** |
| `search/web_search.py` | **Hiskens addition** |
| `search/web_map.py` | **Hiskens addition** |

All are Hiskens-specific web search utilities. KEEP.

#### `trellis/scripts/common/` — Script differences

Files in overlay NOT in upstream:

| File | Status | Notes |
|---|---|---|
| `common/context_assembly.py` | **Hiskens addition** | Context assembly shared between hooks and Codex scripts (CCR routing, spec injection logic) |
| `common/phase.py` | **STALE — removed upstream** | Was `workflow_phase.py` in upstream before rename/removal. Removed in `efccf6f`. |
| `common/registry.py` | **STALE — removed upstream** | Removed in `efccf6f`. Used by old multi-agent pipeline. |
| `common/worktree.py` | **STALE — removed upstream** | Removed in `efccf6f`. Used by old worktree-based multi-agent dispatch. |

Files in upstream NOT in overlay (overlay is missing these):

| File | Impact |
|---|---|
| `common/active_task.py` | **MISSING** — upstream beta.18 uses this module. Overlay uses older task management approach. |
| `common/workflow_phase.py` | **MISSING** — upstream beta.18 replacement for old `phase.py`. |

### 10. `trellis/spec/` — Spec files

All spec files in the overlay are **Hiskens-specific content** — upstream's spec templates are generic (`backend/`, `frontend/`, `guides/`), while the overlay has domain-specific scientific computing specs (`python/`, `matlab/`). The two guides that share names with upstream templates are:

| File | Upstream equivalent | Status |
|---|---|---|
| `spec/guides/code-reuse-thinking-guide.md` | `packages/cli/src/templates/markdown/spec/guides/code-reuse-thinking-guide.md.txt` | **HISKENS VERSION** — overlay version is a Python/MATLAB-specific guide; upstream is generic. Content is different. KEEP |
| `spec/guides/cross-platform-thinking-guide.md` | `packages/cli/src/templates/markdown/spec/guides/cross-platform-thinking-guide.md.txt` | **HISKENS VERSION** — overlay is WSL2/Windows/MATLAB-specific; upstream is generic. Content is different. KEEP |

All other spec files in `trellis/spec/guides/`, `trellis/spec/python/`, `trellis/spec/matlab/` are **genuine Hiskens additions**. KEEP all.

### 11. `trellis/config/` and `trellis/config.yaml`

| File | Status |
|---|---|
| `trellis/config.yaml` | **OVERRIDE** — overlay adds `session.spec_scope: active_task`, `features:` block (ccr_routing, reference_support, java_support, extra_platforms) not in upstream config.yaml |
| `trellis/config/agent-models.example.json` | **Hiskens addition** — CCR model routing config for both old-name and trellis-prefixed agents. KEEP |

The overlay `config.yaml` override is intentional and contains Hiskens-specific features. KEEP.

### 12. `trellis/templates/prd-template.md`

Not in upstream beta.18. **Hiskens addition** (Chinese-language PRD template). KEEP.

### 13. `trellis/worktree.yaml`

Not in upstream beta.18 (upstream has a `.txt` template only). **Hiskens-specific** (already excluded by `exclude.yaml`). KEEP.

### 14. `codex/hooks/__pycache__/` and `claude/hooks/__pycache__/` and `trellis/scripts/common/__pycache__/` and `trellis/scripts/__pycache__/` and `trellis/scripts/multi_agent/__pycache__/` and `trellis/scripts/search/__pycache__/`

All compiled `.pyc` bytecode files. **Should not be tracked or installed** into user projects.

---

## Section A: Files to REMOVE from Overlay

These are definitively stale — either removed from upstream or using old names.

### Old-name agents (shadow upstream trellis-* agents)
- `overlays/hiskens/templates/claude/agents/check.md`
- `overlays/hiskens/templates/claude/agents/debug.md`
- `overlays/hiskens/templates/claude/agents/dispatch.md`
- `overlays/hiskens/templates/claude/agents/implement.md`
- `overlays/hiskens/templates/claude/agents/plan.md`
- `overlays/hiskens/templates/claude/agents/research.md`

### Old-name codex agents
- `overlays/hiskens/templates/codex/agents/check.toml`
- `overlays/hiskens/templates/codex/agents/debug.toml`
- `overlays/hiskens/templates/codex/agents/implement.toml`
- `overlays/hiskens/templates/codex/agents/plan.toml`
- `overlays/hiskens/templates/codex/agents/research.toml`

### Removed-upstream hooks
- `overlays/hiskens/templates/claude/hooks/ralph-loop.py`

### Removed-upstream scripts
- `overlays/hiskens/templates/trellis/scripts/create_bootstrap.py`
- `overlays/hiskens/templates/trellis/scripts/multi_agent/__init__.py`
- `overlays/hiskens/templates/trellis/scripts/multi_agent/cleanup.py`
- `overlays/hiskens/templates/trellis/scripts/multi_agent/create_pr.py`
- `overlays/hiskens/templates/trellis/scripts/multi_agent/plan.py`
- `overlays/hiskens/templates/trellis/scripts/multi_agent/start.py`
- `overlays/hiskens/templates/trellis/scripts/multi_agent/status.py`
- `overlays/hiskens/templates/trellis/scripts/common/phase.py`
- `overlays/hiskens/templates/trellis/scripts/common/registry.py`
- `overlays/hiskens/templates/trellis/scripts/common/worktree.py`

### Stale trellis-meta skill copies (old beta.5 version)
- `overlays/hiskens/templates/claude/skills/trellis-meta/` (entire directory — overlay version is 0.3.0-beta.5)
- `overlays/hiskens/templates/agents/skills/trellis-meta/` (entire directory — same old version, missing customize-local/, local-architecture/, platform-files/ subdirs)

### Compiled bytecode (should never be in templates)
- All `__pycache__/*.pyc` files across all directories

---

## Section B: Files to UPDATE in Overlay

These remain in the overlay but need content updates to align with beta.18.

### `settings.overlay.json` — Missing hook registrations
The overlay has `inject-subagent-context.py` (with CCR routing) and `session-start.py` (with Chinese first-reply notice), but neither is registered in `settings.overlay.json`. Upstream `settings.json` wires both under `PreToolUse (Task/Agent)` and `SessionStart`. The overlay should add these registrations or rely on the upstream `settings.json` wiring.

### `agents/skills/parallel/SKILL.md` and `claude/commands/trellis/parallel.md`
Need content review. If they reference `dispatch`, `plan`, or `multi_agent` scripts, content is stale.

### `agents/skills/finish-work/SKILL.md`
Check whether this duplicates upstream `trellis-finish-work` skill; may need a hiskens-specific prefix or differentiated description to avoid conflicts.

### `trellis/scripts/common/` — Missing new upstream modules
The overlay does not include `active_task.py` and `workflow_phase.py` which were added in upstream between beta.14 and beta.18. These may be required by the upstream-overridden `task.py` or `get_context.py`. If the overlay's custom `task.py` imports either of these, they must be added.

---

## Section C: Exclude.yaml Cross-Reference

Current `exclude.yaml` entries:
- `claude/agents/review.md` — file exists in overlay, correctly excluded
- `trellis/worktree.yaml` — file exists in overlay, correctly excluded

No excluded files are missing from the overlay (both exist). No stale entries in `exclude.yaml`.

**Recommendation**: `exclude.yaml` should be expanded to exclude the old-name agents that are being kept as reference material (e.g., `codex-implement.md`, `codex/agents/review.toml`) if they are not meant to be auto-installed.

---

## Caveats / Not Found

1. `parallel.md` and `parallel/SKILL.md` content was not fully read — whether they reference the deleted dispatch/multi_agent pipeline requires manual inspection.
2. `add_session.py`, `get_developer.py`, `init_developer.py` were not diff-checked against upstream — they may also have Hiskens-specific additions that should be catalogued.
3. `codex/agents/review.toml` is a Hiskens addition (for adversarial code review) — not removed from upstream, just never was in upstream. Whether it should be in `exclude.yaml` depends on whether all Hiskens projects want it installed automatically.
4. `parse_sub2api_usage.py` is not referenced in `settings.overlay.json` — it may be manually invoked or vestigial.
5. The `trellis/scripts/search/__pycache__` and other pycache directories confirm that compiled bytecode has been accidentally committed to the overlay template directory and needs to be removed from git tracking.
