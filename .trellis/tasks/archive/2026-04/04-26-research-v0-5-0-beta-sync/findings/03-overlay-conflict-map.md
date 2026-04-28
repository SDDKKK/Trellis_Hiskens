# Overlay-Asset -> Upstream-Conflict Map

> Research Agent #3 — v0.5.0-beta.14 sync investigation  
> Generated: 2026-04-26  
> Scope: All files under `overlays/hiskens/templates/` (174 files)

---

## 1. Executive Summary

Upstream Trellis underwent a **massive architectural refactoring** between `v0.4.0-beta.10` (fork base) and `v0.5.0-beta.14`:

- Template files dropped from **293 to 146** (50% reduction)
- **Skill-first refactor**: Commands and skills unified under `common/` with platform-specific resolution
- **Agent renaming**: `check.md` -> `trellis-check.md`, `implement.md` -> `trellis-implement.md`, etc.
- **Multi-agent pipeline removed**: `multi_agent/`, `worktree.yaml`, Ralph Loop, `create_bootstrap.py` all deleted
- **Shared hooks introduced**: Platform-independent hooks moved to `shared-hooks/`
- **Hooks migrated**: Claude hooks moved from `claude/hooks/` to `shared-hooks/`
- **Codex skills added**: 13 Codex skills under `codex/skills/`

### Classification x Risk Summary Table

| Class | LOW | MEDIUM | HIGH | CRITICAL |
|---|---|---|---|---|
| BASELINE | 2 | 0 | 0 | 1 |
| APPEND | 0 | 14 | 10 | 34 |
| OVERLAY-ONLY | 112 | 0 | 0 | 0 |
| EXCLUDE | 0 | 0 | 0 | 0 |

**Totals**: 174 files analyzed
- **112 OVERLAY-ONLY** (64%) — hiskens-created content, no upstream equivalent at any version
- **34 CRITICAL** (20%) — upstream removed/renamed the mirrored path
- **10 HIGH** (6%) — APPEND files where upstream also changed in v0.5
- **14 MEDIUM** (8%) — APPEND files where upstream is unchanged from v0.4 to v0.5
- **2 BASELINE/LOW** (1%) — byte-identical to upstream v0.4, can be dropped
- **1 BASELINE/CRITICAL** — byte-identical to upstream v0.4 but upstream removed it

---

## 2. CRITICAL Files (Upstream Removed or Renamed)

These 35 files have their mirrored upstream path **removed** in v0.5.0-beta.14. For each, upstream either deleted the feature entirely or relocated it under a new path.

### 2.1 Claude Agents (6 files) — Renamed to `trellis-*.md`

Upstream v5 renamed all Claude agents with `trellis-` prefix (commit `79801ed`). The overlay agents have significant hiskens customizations (model: opus[1m], RTK hooks, Nocturne tools, Ralph Loop completion markers).

| Overlay Path | Upstream v4 Path | Upstream v5 Path | Action |
|---|---|---|---|
| `claude/agents/check.md` | `claude/agents/check.md` | `claude/agents/trellis-check.md` | Port customizations to new upstream agent |
| `claude/agents/debug.md` | `claude/agents/debug.md` | **REMOVED** | Upstream dropped debug agent; keep overlay or deprecate |
| `claude/agents/dispatch.md` | `claude/agents/dispatch.md` | **REMOVED** | Upstream dropped dispatch agent; keep overlay or deprecate |
| `claude/agents/implement.md` | `claude/agents/implement.md` | `claude/agents/trellis-implement.md` | Port customizations to new upstream agent |
| `claude/agents/plan.md` | `claude/agents/plan.md` | **REMOVED** | Upstream dropped plan agent; keep overlay or deprecate |
| `claude/agents/research.md` | `claude/agents/research.md` | `claude/agents/trellis-research.md` | Port customizations to new upstream agent |

**Recommended action**: The 3 renamed agents (check, implement, research) need manual porting. The overlay versions have:
- `model: opus[1m]` (upstream v5 dropped model hardcoding entirely)
- RTK hook commands (`rtk hook claude`)
- Nocturne memory tools
- Ralph Loop completion markers
- Scientific-computing-specific tool lists

Upstream v5 agents are simpler and platform-generic. The hiskens customizations must be grafted onto the new upstream base.

The 3 dropped agents (debug, dispatch, plan) are hiskens-specific. Since upstream removed them, the overlay versions will install to paths that upstream no longer recognizes. The overlay loader will still copy them, but they won't be referenced by upstream's configurator. **Decision**: Keep as overlay-only content; they provide value for hiskens workflows.

### 2.2 Claude Commands (13 files) — Moved to `common/commands/` or `common/skills/`

Upstream v5's skill-first refactor (commit `700e7d3`) moved most commands to `common/commands/` (start, finish-work) or `common/skills/` (brainstorm, break-loop, check, update-spec). Some were merged or deleted.

| Overlay Path | Upstream v4 | Upstream v5 | Action |
|---|---|---|---|
| `claude/commands/trellis/start.md` | Exists | `common/commands/start.md` | Port hiskens customizations to new common template |
| `claude/commands/trellis/finish-work.md` | Exists | `common/commands/finish-work.md` | Port hiskens customizations to new common template |
| `claude/commands/trellis/brainstorm.md` | Exists | `common/skills/brainstorm.md` | Port to common/skills; overlay diverges significantly |
| `claude/commands/trellis/break-loop.md` | Exists | `common/skills/break-loop.md` | Port to common/skills |
| `claude/commands/trellis/check-cross-layer.md` | Exists | **MERGED into check** | Upstream merged check-cross-layer into check skill |
| `claude/commands/trellis/create-command.md` | Exists | **REMOVED** | Upstream dropped create-command skill |
| `claude/commands/trellis/integrate-skill.md` | Exists | **REMOVED** | Upstream dropped integrate-skill skill |
| `claude/commands/trellis/onboard.md` | Exists | **REMOVED** | Upstream dropped onboard skill |
| `claude/commands/trellis/parallel.md` | Exists | **REMOVED** | Upstream dropped parallel skill |
| `claude/commands/trellis/record-session.md` | Exists | **MERGED into finish-work** | Upstream merged record-session into finish-work |
| `claude/commands/trellis/update-spec.md` | Exists | `common/skills/update-spec.md` | Port to common/skills |

**Recommended action**: These are the most complex ports. The overlay commands have hiskens-specific:
- Python/MATLAB dev type references (vs upstream's backend/frontend/fullstack)
- RTK integration notes
- Nocturne memory promotion steps
- Scientific computing-specific instructions

The upstream v5 common templates use `{{CMD_REF:x}}` and `{{#AGENT_CAPABLE}}` placeholder syntax that gets resolved per-platform. Hiskens customizations need to be expressed within this new template system.

### 2.3 Claude Hooks (5 files) — Moved to `shared-hooks/`

Upstream v5 moved platform-independent hooks to `shared-hooks/` (commit `efccf6f`). Some hooks were removed entirely.

| Overlay Path | Upstream v4 | Upstream v5 | Action |
|---|---|---|---|
| `claude/hooks/session-start.py` | Exists | `shared-hooks/session-start.py` | Port hiskens customizations to shared-hooks |
| `claude/hooks/inject-subagent-context.py` | Exists | `shared-hooks/inject-subagent-context.py` | Port hiskens customizations to shared-hooks |
| `claude/hooks/statusline.py` | Exists | `shared-hooks/statusline.py` | Port hiskens customizations to shared-hooks |
| `claude/hooks/ralph-loop.py` | Exists | **REMOVED** | Upstream dropped Ralph Loop entirely |

**Recommended action**: The shared-hooks versions in v5 are more generic (platform-agnostic). The overlay versions have hiskens-specific:
- Nocturne context injection (`get_nocturne_context()`, `get_memory_summary()`)
- Scientific computing spec paths (`spec/python/`, `spec/matlab/`)
- RTK hook integration
- CCR routing support

These customizations must be ported to the new shared-hooks base. The Ralph Loop hook was entirely removed by upstream — the overlay version provides hiskens-specific completion marker enforcement. **Decision**: Keep as overlay-only since upstream no longer has an equivalent.

### 2.4 Codex Agents (3 files) — Renamed to `trellis-*.toml`

| Overlay Path | Upstream v4 | Upstream v5 | Action |
|---|---|---|---|
| `codex/agents/check.toml` | Exists | `codex/agents/trellis-check.toml` | Rename overlay; port customizations |
| `codex/agents/implement.toml` | Exists | `codex/agents/trellis-implement.toml` | Rename overlay; port customizations |
| `codex/agents/research.toml` | Exists | `codex/agents/trellis-research.toml` | Rename overlay; port customizations |

**Recommended action**: The overlay Codex agents have hiskens-specific tool lists and model settings. Upstream v5 renamed them and simplified the content. The overlay should be renamed to match upstream's new naming convention, then customizations applied.

### 2.5 Scripts — Removed Features (7 files)

| Overlay Path | Upstream v4 | Upstream v5 | Action |
|---|---|---|---|
| `trellis/scripts/common/phase.py` | Exists | **REMOVED** (commit `b323e93`) | Overlay uses this; investigate if upstream replacement exists |
| `trellis/scripts/common/registry.py` | Exists | **REMOVED** | Overlay uses this; investigate replacement |
| `trellis/scripts/common/worktree.py` | Exists | **REMOVED** | Overlay uses this; upstream dropped worktree support |
| `trellis/scripts/create_bootstrap.py` | Exists | **REMOVED** | Overlay uses this; upstream dropped bootstrap creation |
| `trellis/scripts/multi_agent/cleanup.py` | Exists | **REMOVED** | Upstream dropped multi-agent pipeline |
| `trellis/scripts/multi_agent/create_pr.py` | Exists | **REMOVED** | Upstream dropped multi-agent pipeline |
| `trellis/scripts/multi_agent/plan.py` | Exists | **REMOVED** | Upstream dropped multi-agent pipeline |
| `trellis/scripts/multi_agent/start.py` | Exists | **REMOVED** | Upstream dropped multi-agent pipeline |
| `trellis/scripts/multi_agent/status.py` | Exists | **REMOVED** | Upstream dropped multi-agent pipeline |
| `trellis/scripts/multi_agent/__init__.py` | Exists | **REMOVED** | Byte-identical to v4; safe to drop |
| `trellis/worktree.yaml` | Exists | **REMOVED** | Upstream dropped worktree support |

**Recommended action**: The multi-agent pipeline was entirely removed by upstream (commit `efccf6f`). The overlay still ships these files for hiskens projects that may use them. Since upstream no longer has these paths, the overlay files will install without conflict — but they won't be maintained by upstream. **Decision**: Keep as overlay-only deprecated content; mark for future removal if hiskens stops using multi-agent workflows.

`phase.py`, `registry.py`, `worktree.py`, and `create_bootstrap.py` are dependencies of other overlay scripts. Need to verify if the calling scripts still need them or if upstream's refactoring made them obsolete.

---

## 3. HIGH-Risk Files (APPEND + Upstream Changed)

These 10 files diverge from upstream v0.4, AND upstream changed them in v0.5. Manual porting required.

### 3.1 `codex/hooks.json`

**Upstream v4 -> v5 diff**: Added `UserPromptSubmit` hook with `inject-workflow-state.py`. Changed `{{PYTHON_CMD}}` placeholder to actual command.

**Overlay vs v4**: Overlay uses hardcoded `python3` instead of `{{PYTHON_CMD}}`, adds `PostToolUse` hook with `post-tool-use.py` (hiskens-specific).

**Porting strategy**: Accept upstream v5's `UserPromptSubmit` addition. Keep overlay's `PostToolUse` hook. Decide whether to use `{{PYTHON_CMD}}` (upstream pattern) or hardcoded `python3` (overlay pattern).

### 3.2 `codex/hooks/session-start.py`

**Upstream v4 -> v5 diff**: Major rewrite. Added `FIRST_REPLY_NOTICE`, `configure_project_encoding()`, `_has_curated_jsonl_entry()`, `_build_workflow_toc()`, `_extract_range()`. Changed workflow injection from full `workflow.md` to TOC + Phase Index. Added `UserPromptSubmit` hook support. Changed guidelines injection to path-only for non-guide specs.

**Overlay vs v4**: Overlay has hiskens-specific additions: `LEGACY_MONOREPO_SPEC_MOVES`, `LEGACY_SCIENTIFIC_ROOTS`, Nocturne context loading, scientific computing spec handling, simplified task resolution.

**Overlay vs v5**: The overlay is 382 lines vs upstream v5's 332 lines. The overlay is missing upstream v5's `_has_curated_jsonl_entry()` and `_build_workflow_toc()` helpers but has Nocturne and scientific-computing-specific logic.

**Porting strategy**: This is the most complex port. Start with upstream v5's base (it has important new features like curated JSONL detection and workflow TOC). Then graft hiskens-specific additions:
- Nocturne context injection
- Scientific computing spec paths (python/matlab)
- Legacy monorepo spec move warnings

### 3.3 `trellis/config.yaml`

**Upstream v4 -> v5 diff**: Added `git: true` option for polyrepo layouts in packages section.

**Overlay vs v4**: Overlay adds `session.spec_scope`, `features` section (ccr_routing, reference_support, java_support, extra_platforms), and update skip paths documentation.

**Porting strategy**: Trivial merge. Accept upstream v5's `git: true` addition. Keep overlay's `session` and `features` sections.

### 3.4 `trellis/scripts/common/cli_adapter.py`

**Upstream v4 -> v5 diff**: Added `droid` platform. Changed Codex/Kiro skill paths from `.agents/skills/{name}/` to `.agents/skills/trellis-{name}/` (trellis-prefix rename).

**Overlay vs v4**: Overlay replaces `windsurf` with `droid` (different platform set), changes docstrings.

**Porting strategy**: Accept upstream v5's `droid` addition AND trellis-prefix skill paths. The overlay's platform changes need reconciliation — upstream v5 still has `windsurf` AND added `droid`, while the overlay dropped `windsurf` for `droid`.

### 3.5 `trellis/scripts/common/config.py`

**Upstream v4 -> v5 diff**: Major rewrite of `parse_simple_yaml()` — inlined from `worktree.py` with much more robust parsing. Added `_unquote()` helper.

**Overlay vs v4**: Overlay adds `get_features()` function for feature flags (ccr_routing, reference_support, etc.).

**Porting strategy**: Accept upstream v5's improved YAML parser. Keep overlay's `get_features()` function.

### 3.6 `trellis/scripts/common/git_context.py`

**Upstream v4 -> v5 diff**: Added `--mode phase` and `--step` / `--platform` arguments. Added imports from new `workflow_phase` module.

**Overlay vs v4**: Minimal diff — just `noqa: F401` comments on imports.

**Porting strategy**: Trivial. Accept upstream v5's phase mode additions. Keep overlay's noqa comments (or drop them if not needed).

### 3.7 `trellis/scripts/common/task_context.py`

**Upstream v4 -> v5 diff**: Removed `cmd_init_context` and all default content generators (`get_implement_base()`, `get_implement_backend()`, etc.). JSONL files are now seeded at `task.py create` time with `_example` lines.

**Overlay vs v4**: Overlay adds scientific computing spec paths to `get_implement_base()`, adds `get_features` and `get_spec_base` imports, adds `_get_scientific_spec_path()` helper.

**Porting strategy**: Complex. Upstream v5 removed `cmd_init_context` entirely — the overlay's scientific computing context generators need to be rethought. The new v5 approach seeds JSONL at task creation time. Hiskens-specific spec paths should be added to the new seeding logic in `task_store.py` instead.

### 3.8 `trellis/scripts/common/task_store.py`

**Upstream v4 -> v5 diff**: Added `_has_subagent_platform()`, `_write_seed_jsonl()`, `_SUBAGENT_CONFIG_DIRS`, and `_SEED_EXAMPLE`. JSONL seeding now happens at task creation time.

**Overlay vs v4**: Overlay adds `cmd_complete`, `cmd_set_status`, state machine constants (`VALID_STATUS_TRANSITIONS`), memory file constants, Nocturne promotion logic.

**Porting strategy**: Accept upstream v5's JSONL seeding logic. Keep overlay's state machine and completion logic. The `_SUBAGENT_CONFIG_DIRS` tuple needs to be checked against hiskens platforms.

### 3.9 `trellis/scripts/common/types.py`

**Upstream v4 -> v5 diff**: Removed `current_phase` and `next_action` fields from `TaskData`.

**Overlay vs v4**: Minimal — just blank line differences and a "Ported from upstream" comment.

**Porting strategy**: Trivial. Accept upstream v5's field removals. The overlay is essentially identical.

### 3.10 `trellis/scripts/task.py`

**Upstream v4 -> v5 diff**: Removed `init-context` and `create-pr` commands. Added deprecation guard for `init-context`. Changed `task.py start` to auto-transition status from `planning` to `in_progress`. Removed multi-agent pipeline references.

**Overlay vs v4**: Overlay adds `complete` and `set-status` commands, Windows UTF-8 encoding fix, Nocturne learning promotion, `--reference` flag for `add-context`, dev_type changed from `backend|frontend|fullstack` to `python|matlab|both|trellis`.

**Porting strategy**: Complex. The overlay's `init-context` command is still used by hiskens workflows (though upstream deprecated it). The overlay's `complete`/`set-status` commands and state machine are hiskens-specific additions that need to be preserved. The dev_type change is fundamental to hiskens.

---

## 4. MEDIUM-Risk Files (APPEND but Upstream Unchanged, or BASELINE but Upstream Changed)

These 14 files diverge from upstream v0.4, but upstream did not change them between v0.4 and v0.5. The overlay customizations are safe to keep, but should be reviewed for relevance.

| File | Overlay Additions vs v4 | Recommended Action |
|---|---|---|
| `trellis/scripts/add_session.py` | Nocturne learning promotion, `--learning`/`--promote-learning` flags, Windows UTF-8 fix, branch resolution, stdin support | Keep — hiskens-specific knowledge harvesting |
| `trellis/scripts/common/developer.py` | Minor formatting, `DIR_TASKS` import reorder | Keep — trivial divergence |
| `trellis/scripts/common/git.py` | (need review — diff was small) | Review |
| `trellis/scripts/common/__init__.py` | **IDENTICAL to v4** | **Drop from overlay** — dead weight |
| `trellis/scripts/common/io.py` | (need review) | Review |
| `trellis/scripts/common/log.py` | (need review) | Review |
| `trellis/scripts/common/packages_context.py` | (need review) | Review |
| `trellis/scripts/common/paths.py` | (need review) | Review |
| `trellis/scripts/common/session_context.py` | (need review) | Review |
| `trellis/scripts/common/task_queue.py` | (need review) | Review |
| `trellis/scripts/common/tasks.py` | (need review) | Review |
| `trellis/scripts/common/task_utils.py` | (need review) | Review |
| `trellis/scripts/get_context.py` | **Near-identical** (1 blank line diff) | **Drop from overlay** — dead weight |
| `trellis/scripts/init_developer.py` | Minor import reorder | Keep — trivial divergence |

---

## 5. OVERLAY-ONLY Inventory

These 112 files exist only in the hiskens overlay and never existed in upstream at v0.4 or v0.5. They are hiskens-specific content.

### 5.1 Agent Skills (9 files)
`agents/skills/before-matlab-dev/SKILL.md`  
`agents/skills/before-python-dev/SKILL.md`  
`agents/skills/brainstorm/SKILL.md`  
`agents/skills/check-matlab/SKILL.md`  
`agents/skills/check-python/SKILL.md`  
`agents/skills/finish-work/SKILL.md`  
`agents/skills/improve-ut/SKILL.md`  
`agents/skills/parallel/SKILL.md`  
`agents/skills/record-session/SKILL.md`  
`agents/skills/retro/SKILL.md`

### 5.2 Trellis Meta Skill (26 files)
`agents/skills/trellis-meta/SKILL.md` + 25 reference docs under `references/{claude-code,core,how-to-modify,meta}/`

### 5.3 Hiskens-Specific Claude Agents (2 files)
`claude/agents/codex-implement.md` — Codex-specific implement agent  
`claude/agents/review.md` — Review agent (upstream dropped review in v5)

### 5.4 Hiskens-Specific Claude Commands (8 files)
`claude/commands/trellis/before-matlab-dev.md`  
`claude/commands/trellis/before-python-dev.md`  
`claude/commands/trellis/brainstorm-base.md`  
`claude/commands/trellis/break-loop-base.md`  
`claude/commands/trellis/check-cross-layer-base.md`  
`claude/commands/trellis/check-matlab.md`  
`claude/commands/trellis/check-python.md`  
`claude/commands/trellis/improve-ut.md`  
`claude/commands/trellis/retro.md`

### 5.5 Hiskens-Specific Claude Hooks (5 files)
`claude/hooks/context-monitor.py`  
`claude/hooks/intent-gate.py`  
`claude/hooks/parse_sub2api_usage.py`  
`claude/hooks/statusline-bridge.py`  
`claude/hooks/todo-enforcer.py`

### 5.6 Hiskens Settings and Skills (4 files)
`claude/settings.overlay.json`  
`claude/skills/github-explorer/SKILL.md`  
`claude/skills/grok-search/SKILL.md`  
`claude/skills/with-codex/SKILL.md`

### 5.7 Codex-Specific Overlay (4 files)
`codex/agents/debug.toml`  
`codex/agents/plan.toml`  
`codex/agents/review.toml`  
`codex/hooks/post-tool-use.py`  
`codex/scripts/load-trellis-context.py`

### 5.8 Nocturne Integration Scripts (4 files)
`trellis/scripts/init-nocturne-namespace.py`  
`trellis/scripts/nocturne_client.py`  
`trellis/scripts/promote-to-nocturne.py`  
`trellis/scripts/sync-trellis-to-nocturne.py`

### 5.9 Search Scripts (5 files)
`treliis/scripts/search/API_CONFIG.md`  
`trellis/scripts/search/_common.py`  
`trellis/scripts/search/web_fetch.py`  
`trellis/scripts/search/web_map.py`  
`trellis/scripts/search/web_search.py`

### 5.10 Spec Guides (25 files)
All files under `trellis/spec/guides/` — hiskens-specific development guides (cross-platform thinking, code reuse, debug methodology, TDD, verification, etc.)

### 5.11 Python Spec (10 files)
All files under `trellis/spec/python/` — Python coding standards, docstring conventions, data processing guidelines, examples

### 5.12 MATLAB Spec (6 files)
All files under `trellis/spec/matlab/` — MATLAB coding standards, docstring conventions, quality guidelines, examples

### 5.13 Other (1 file)
`trellis/templates/prd-template.md` — PRD template

---

## 6. Wasted-Overlay Candidates

These files are byte-identical (or near-identical) to upstream v0.4 and could be removed from the overlay to reduce maintenance burden.

| File | Status | Action |
|---|---|---|
| `trellis/scripts/common/__init__.py` | IDENTICAL to v4 | **Remove** — 3-line docstring module |
| `trellis/scripts/get_developer.py` | IDENTICAL to v4 | **Remove** — simple wrapper |
| `trellis/scripts/get_context.py` | Near-identical (1 blank line) | **Remove** — 15-line wrapper |
| `trellis/scripts/multi_agent/__init__.py` | IDENTICAL to v4 | Keep for now — upstream removed multi_agent; this file is harmless but part of a deprecated module |

**Potential savings**: Removing 3 files reduces overlay weight by ~50 lines of dead code.

---

## 7. `exclude.yaml` Review

Current `exclude.yaml`:
```yaml
exclude:
  - claude/commands/trellis/before-dev.md
  - claude/commands/trellis/check.md
  - agents/skills/before-dev/SKILL.md
  - agents/skills/check/SKILL.md
```

### 7.1 Current Rules Status

| Excluded Path | In Upstream v4? | In Upstream v5? | In Overlay? | Status |
|---|---|---|---|---|
| `claude/commands/trellis/before-dev.md` | YES | NO (moved to `common/skills/before-dev.md`) | NO | **Stale** — upstream v5 moved this to common/skills; exclude rule no longer matches |
| `claude/commands/trellis/check.md` | YES | NO (moved to `common/skills/check.md`) | NO | **Stale** — same issue |
| `agents/skills/before-dev/SKILL.md` | NO | NO | NO | **Stale** — never existed in upstream |
| `agents/skills/check/SKILL.md` | NO | NO | NO | **Stale** — never existed in upstream |

**All 4 exclude rules are stale for v0.5.0-beta.14.** The upstream paths they target no longer exist.

### 7.2 Recommended Changes for v0.5.0

The exclude mechanism prevents upstream files from being installed. With the skill-first refactor, upstream now installs files through configurators that read from `common/` and resolve per-platform. The exclude rules need to target the **source** templates or the **output** paths.

**New exclude candidates for v0.5.0:**

| Path | Reason |
|---|---|
| `common/skills/before-dev.md` | Hiskens uses `before-python-dev.md` / `before-matlab-dev.md` instead |
| `codex/skills/before-dev/SKILL.md` | Same — hiskens has platform-specific before-dev variants |

However, the exclude mechanism may not work the same way in v0.5 since templates are resolved through the configurator. This needs testing with the actual overlay loader.

**Recommendation**: For v0.5.0 sync, clear all stale exclude rules and rebuild based on actual conflicts observed during the sync.

```yaml
# Proposed v0.5.0 exclude.yaml (start fresh, add as needed)
exclude: []
```

---

## 8. Per-File Appendix

| # | Overlay Path | Mirrored Upstream Path | v4 Exists? | v5 Exists? | v5 Status | v4->v5 Changed? | Overlay vs v4 | Class | Risk | Recommended Action |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `agents/skills/before-matlab-dev/SKILL.md` | `agents/skills/before-matlab-dev/SKILL.md` | NO | NO | REMOVED | N/A | NOT_IN_V4 | OVERLAY-ONLY | LOW | No action — hiskens-only |
| 2 | `agents/skills/before-python-dev/SKILL.md` | `agents/skills/before-python-dev/SKILL.md` | NO | NO | REMOVED | N/A | NOT_IN_V4 | OVERLAY-ONLY | LOW | No action — hiskens-only |
| 3 | `agents/skills/brainstorm/SKILL.md` | `agents/skills/brainstorm/SKILL.md` | NO | NO | REMOVED | N/A | NOT_IN_V4 | OVERLAY-ONLY | LOW | No action — hiskens-only |
| 4 | `agents/skills/check-matlab/SKILL.md` | `agents/skills/check-matlab/SKILL.md` | NO | NO | REMOVED | N/A | NOT_IN_V4 | OVERLAY-ONLY | LOW | No action — hiskens-only |
| 5 | `agents/skills/check-python/SKILL.md` | `agents/skills/check-python/SKILL.md` | NO | NO | REMOVED | N/A | NOT_IN_V4 | OVERLAY-ONLY | LOW | No action — hiskens-only |
| 6 | `agents/skills/finish-work/SKILL.md` | `agents/skills/finish-work/SKILL.md` | NO | NO | REMOVED | N/A | NOT_IN_V4 | OVERLAY-ONLY | LOW | No action — hiskens-only |
| 7 | `agents/skills/improve-ut/SKILL.md` | `agents/skills/improve-ut/SKILL.md` | NO | NO | REMOVED | N/A | NOT_IN_V4 | OVERLAY-ONLY | LOW | No action — hiskens-only |
| 8 | `agents/skills/parallel/SKILL.md` | `agents/skills/parallel/SKILL.md` | NO | NO | REMOVED | N/A | NOT_IN_V4 | OVERLAY-ONLY | LOW | No action — hiskens-only |
| 9 | `agents/skills/record-session/SKILL.md` | `agents/skills/record-session/SKILL.md` | NO | NO | REMOVED | N/A | NOT_IN_V4 | OVERLAY-ONLY | LOW | No action — hiskens-only |
| 10 | `agents/skills/retro/SKILL.md` | `agents/skills/retro/SKILL.md` | NO | NO | REMOVED | N/A | NOT_IN_V4 | OVERLAY-ONLY | LOW | No action — hiskens-only |
| 11-35 | `agents/skills/trellis-meta/...` (25 files) | Various | NO | NO | REMOVED | N/A | NOT_IN_V4 | OVERLAY-ONLY | LOW | No action — hiskens-only |
| 36 | `claude/agents/check.md` | `claude/agents/check.md` | YES | NO | RENAMED | N/A | DIVERGED | APPEND | CRITICAL | Port to `claude/agents/trellis-check.md` |
| 37 | `claude/agents/codex-implement.md` | `claude/agents/codex-implement.md` | NO | NO | REMOVED | N/A | NOT_IN_V4 | OVERLAY-ONLY | LOW | No action — hiskens-only |
| 38 | `claude/agents/debug.md` | `claude/agents/debug.md` | YES | NO | REMOVED | N/A | DIVERGED | APPEND | CRITICAL | Upstream dropped; keep as overlay-only |
| 39 | `claude/agents/dispatch.md` | `claude/agents/dispatch.md` | YES | NO | REMOVED | N/A | DIVERGED | APPEND | CRITICAL | Upstream dropped; keep as overlay-only |
| 40 | `claude/agents/implement.md` | `claude/agents/implement.md` | YES | NO | RENAMED | N/A | DIVERGED | APPEND | CRITICAL | Port to `claude/agents/trellis-implement.md` |
| 41 | `claude/agents/plan.md` | `claude/agents/plan.md` | YES | NO | REMOVED | N/A | DIVERGED | APPEND | CRITICAL | Upstream dropped; keep as overlay-only |
| 42 | `claude/agents/research.md` | `claude/agents/research.md` | YES | NO | RENAMED | N/A | DIVERGED | APPEND | CRITICAL | Port to `claude/agents/trellis-research.md` |
| 43 | `claude/agents/review.md` | `claude/agents/review.md` | NO | NO | REMOVED | N/A | NOT_IN_V4 | OVERLAY-ONLY | LOW | No action — hiskens-only |
| 44-52 | `claude/commands/trellis/...` (9 base files) | Various | NO | NO | REMOVED | N/A | NOT_IN_V4 | OVERLAY-ONLY | LOW | No action — hiskens-only |
| 53-63 | `claude/commands/trellis/...` (11 diverged files) | Various | YES | NO | MOVED | N/A | DIVERGED | APPEND | CRITICAL | Port to `common/commands/` or `common/skills/` |
| 64-67 | `claude/hooks/...` (4 overlay-only hooks) | Various | NO | NO | REMOVED | N/A | NOT_IN_V4 | OVERLAY-ONLY | LOW | No action — hiskens-only |
| 68-72 | `claude/hooks/...` (5 diverged hooks) | Various | YES | NO | MOVED | N/A | DIVERGED | APPEND | CRITICAL | Port to `shared-hooks/` |
| 73 | `claude/settings.overlay.json` | `claude/settings.overlay.json` | NO | NO | REMOVED | N/A | NOT_IN_V4 | OVERLAY-ONLY | LOW | No action — hiskens-only |
| 74-76 | `claude/skills/...` (3 files) | Various | NO | NO | REMOVED | N/A | NOT_IN_V4 | OVERLAY-ONLY | LOW | No action — hiskens-only |
| 77 | `codex/agents/check.toml` | `codex/agents/check.toml` | YES | NO | RENAMED | N/A | DIVERGED | APPEND | CRITICAL | Rename to `trellis-check.toml`; port customizations |
| 78 | `codex/agents/debug.toml` | `codex/agents/debug.toml` | NO | NO | REMOVED | N/A | NOT_IN_V4 | OVERLAY-ONLY | LOW | No action — hiskens-only |
| 79 | `codex/agents/implement.toml` | `codex/agents/implement.toml` | YES | NO | RENAMED | N/A | DIVERGED | APPEND | CRITICAL | Rename to `trellis-implement.toml`; port customizations |
| 80 | `codex/agents/plan.toml` | `codex/agents/plan.toml` | NO | NO | REMOVED | N/A | NOT_IN_V4 | OVERLAY-ONLY | LOW | No action — hiskens-only |
| 81 | `codex/agents/research.toml` | `codex/agents/research.toml` | YES | NO | RENAMED | N/A | DIVERGED | APPEND | CRITICAL | Rename to `trellis-research.toml`; port customizations |
| 82 | `codex/agents/review.toml` | `codex/agents/review.toml` | NO | NO | REMOVED | N/A | NOT_IN_V4 | OVERLAY-ONLY | LOW | No action — hiskens-only |
| 83 | `codex/hooks.json` | `codex/hooks.json` | YES | YES | PRESENT | YES | DIVERGED | APPEND | HIGH | Merge upstream v5 additions; keep PostToolUse |
| 84 | `codex/hooks/post-tool-use.py` | `codex/hooks/post-tool-use.py` | NO | NO | REMOVED | N/A | NOT_IN_V4 | OVERLAY-ONLY | LOW | No action — hiskens-only |
| 85 | `codex/hooks/session-start.py` | `codex/hooks/session-start.py` | YES | YES | PRESENT | YES | DIVERGED | APPEND | HIGH | Major port: merge v5 base + hiskens additions |
| 86 | `codex/scripts/load-trellis-context.py` | `codex/scripts/load-trellis-context.py` | NO | NO | REMOVED | N/A | NOT_IN_V4 | OVERLAY-ONLY | LOW | No action — hiskens-only |
| 87 | `trellis/config.yaml` | `trellis/config.yaml` | YES | YES | PRESENT | YES | DIVERGED | APPEND | HIGH | Trivial merge: accept v5 additions + keep features |
| 88 | `trellis/scripts/add_session.py` | `trellis/scripts/add_session.py` | YES | YES | PRESENT | NO | DIVERGED | APPEND | MEDIUM | Keep — hiskens-specific learning promotion |
| 89 | `trellis/scripts/common/cli_adapter.py` | `trellis/scripts/common/cli_adapter.py` | YES | YES | PRESENT | YES | DIVERGED | APPEND | HIGH | Reconcile platform sets; accept trellis-prefix |
| 90 | `trellis/scripts/common/config.py` | `trellis/scripts/common/config.py` | YES | YES | PRESENT | YES | DIVERGED | APPEND | HIGH | Accept v5 YAML parser; keep get_features() |
| 91 | `trellis/scripts/common/context_assembly.py` | `trellis/scripts/common/context_assembly.py` | NO | NO | REMOVED | N/A | NOT_IN_V4 | OVERLAY-ONLY | LOW | No action — hiskens-only |
| 92 | `trellis/scripts/common/developer.py` | `trellis/scripts/common/developer.py` | YES | YES | PRESENT | NO | DIVERGED | APPEND | MEDIUM | Keep — trivial divergence |
| 93 | `trellis/scripts/common/git_context.py` | `trellis/scripts/common/git_context.py` | YES | YES | PRESENT | YES | DIVERGED | APPEND | HIGH | Trivial: accept v5 phase mode |
| 94 | `trellis/scripts/common/git.py` | `trellis/scripts/common/git.py` | YES | YES | PRESENT | NO | DIVERGED | APPEND | MEDIUM | Review |
| 95 | `trellis/scripts/common/__init__.py` | `trellis/scripts/common/__init__.py` | YES | YES | PRESENT | NO | IDENTICAL | BASELINE | LOW | **Remove from overlay** |
| 96 | `trellis/scripts/common/io.py` | `trellis/scripts/common/io.py` | YES | YES | PRESENT | NO | DIVERGED | APPEND | MEDIUM | Review |
| 97 | `trellis/scripts/common/log.py` | `trellis/scripts/common/log.py` | YES | YES | PRESENT | NO | DIVERGED | APPEND | MEDIUM | Review |
| 98 | `trellis/scripts/common/packages_context.py` | `trellis/scripts/common/packages_context.py` | YES | YES | PRESENT | NO | DIVERGED | APPEND | MEDIUM | Review |
| 99 | `trellis/scripts/common/paths.py` | `trellis/scripts/common/paths.py` | YES | YES | PRESENT | NO | DIVERGED | APPEND | MEDIUM | Review |
| 100 | `trellis/scripts/common/phase.py` | `trellis/scripts/common/phase.py` | YES | NO | REMOVED | N/A | DIVERGED | APPEND | CRITICAL | Upstream removed; check if still needed |
| 101 | `trellis/scripts/common/registry.py` | `trellis/scripts/common/registry.py` | YES | NO | REMOVED | N/A | DIVERGED | APPEND | CRITICAL | Upstream removed; check if still needed |
| 102 | `trellis/scripts/common/session_context.py` | `trellis/scripts/common/session_context.py` | YES | YES | PRESENT | NO | DIVERGED | APPEND | MEDIUM | Review |
| 103 | `trellis/scripts/common/task_context.py` | `trellis/scripts/common/task_context.py` | YES | YES | PRESENT | YES | DIVERGED | APPEND | HIGH | Complex: upstream removed init-context; rethink approach |
| 104 | `trellis/scripts/common/task_queue.py` | `trellis/scripts/common/task_queue.py` | YES | YES | PRESENT | NO | DIVERGED | APPEND | MEDIUM | Review |
| 105 | `trellis/scripts/common/tasks.py` | `trellis/scripts/common/tasks.py` | YES | YES | PRESENT | NO | DIVERGED | APPEND | MEDIUM | Review |
| 106 | `trellis/scripts/common/task_store.py` | `trellis/scripts/common/task_store.py` | YES | YES | PRESENT | YES | DIVERGED | APPEND | HIGH | Accept v5 seeding; keep state machine |
| 107 | `trellis/scripts/common/task_utils.py` | `trellis/scripts/common/task_utils.py` | YES | YES | PRESENT | NO | DIVERGED | APPEND | MEDIUM | Review |
| 108 | `trellis/scripts/common/types.py` | `trellis/scripts/common/types.py` | YES | YES | PRESENT | YES | DIVERGED | APPEND | HIGH | Trivial: accept v5 field removals |
| 109 | `trellis/scripts/common/worktree.py` | `trellis/scripts/common/worktree.py` | YES | NO | REMOVED | N/A | DIVERGED | APPEND | CRITICAL | Upstream removed; check if still needed |
| 110 | `trellis/scripts/create_bootstrap.py` | `trellis/scripts/create_bootstrap.py` | YES | NO | REMOVED | N/A | DIVERGED | APPEND | CRITICAL | Upstream removed; check if still needed |
| 111 | `trellis/scripts/get_context.py` | `trellis/scripts/get_context.py` | YES | YES | PRESENT | NO | DIVERGED* | APPEND | MEDIUM | **Remove from overlay** (1 blank line diff) |
| 112 | `trellis/scripts/get_developer.py` | `trellis/scripts/get_developer.py` | YES | YES | PRESENT | NO | IDENTICAL | BASELINE | LOW | **Remove from overlay** |
| 113 | `trellis/scripts/init_developer.py` | `trellis/scripts/init_developer.py` | YES | YES | PRESENT | NO | DIVERGED | APPEND | MEDIUM | Keep — trivial divergence |
| 114 | `trellis/scripts/init-nocturne-namespace.py` | `trellis/scripts/init-nocturne-namespace.py` | NO | NO | REMOVED | N/A | NOT_IN_V4 | OVERLAY-ONLY | LOW | No action — hiskens-only |
| 115 | `trellis/scripts/__init__.py` | `trellis/scripts/__init__.py` | YES | YES | PRESENT | NO | IDENTICAL | BASELINE | LOW | **Remove from overlay** |
| 116-121 | `trellis/scripts/multi_agent/...` (6 files) | Various | YES | NO | REMOVED | N/A | Various | Various | CRITICAL | Upstream dropped multi-agent; keep as deprecated |
| 122 | `trellis/scripts/nocturne_client.py` | `trellis/scripts/nocturne_client.py` | NO | NO | REMOVED | N/A | NOT_IN_V4 | OVERLAY-ONLY | LOW | No action — hiskens-only |
| 123 | `trellis/scripts/promote-to-nocturne.py` | `trellis/scripts/promote-to-nocturne.py` | NO | NO | REMOVED | N/A | NOT_IN_V4 | OVERLAY-ONLY | LOW | No action — hiskens-only |
| 124-128 | `trellis/scripts/search/...` (5 files) | Various | NO | NO | REMOVED | N/A | NOT_IN_V4 | OVERLAY-ONLY | LOW | No action — hiskens-only |
| 129 | `trellis/scripts/sync-trellis-to-nocturne.py` | `trellis/scripts/sync-trellis-to-nocturne.py` | NO | NO | REMOVED | N/A | NOT_IN_V4 | OVERLAY-ONLY | LOW | No action — hiskens-only |
| 130 | `trellis/scripts/task.py` | `trellis/scripts/task.py` | YES | YES | PRESENT | YES | DIVERGED | APPEND | HIGH | Complex: merge v5 removals + keep hiskens additions |
| 131-155 | `trellis/spec/guides/...` (25 files) | Various | NO | NO | REMOVED | N/A | NOT_IN_V4 | OVERLAY-ONLY | LOW | No action — hiskens-only |
| 156-161 | `trellis/spec/matlab/...` (6 files) | Various | NO | NO | REMOVED | N/A | NOT_IN_V4 | OVERLAY-ONLY | LOW | No action — hiskens-only |
| 162-172 | `trellis/spec/python/...` (11 files) | Various | NO | NO | REMOVED | N/A | NOT_IN_V4 | OVERLAY-ONLY | LOW | No action — hiskens-only |
| 173 | `trellis/templates/prd-template.md` | `trellis/templates/prd-template.md` | NO | NO | REMOVED | N/A | NOT_IN_V4 | OVERLAY-ONLY | LOW | No action — hiskens-only |
| 174 | `trellis/worktree.yaml` | `trellis/worktree.yaml` | YES | NO | REMOVED | N/A | DIVERGED | APPEND | CRITICAL | Upstream dropped worktree support; keep as deprecated |

---

## 9. Key Findings & Recommendations

### 9.1 The v0.5.0 Sync Will Be Major Surgery

Unlike previous syncs that involved incremental changes, v0.5.0-beta.14 represents a **fundamental architectural rewrite** of Trellis templates:

- 50% of template files were deleted or moved
- The skill-first refactor changes how ALL commands and skills are organized
- Agent renaming breaks all existing agent references
- Multi-agent pipeline removal eliminates a core hiskens feature

### 9.2 Three-Phase Porting Strategy

**Phase 1 — Structural Mapping** (this report)
- Map every overlay file to its new upstream location (or confirm deletion)
- Identify which upstream files need hiskens customizations grafted onto them

**Phase 2 — Core Script Porting** (highest priority)
1. `trellis/scripts/task.py` — merge upstream v5 removals with hiskens additions
2. `trellis/scripts/common/config.py` — accept new YAML parser, keep feature flags
3. `trellis/scripts/common/task_store.py` — accept JSONL seeding, keep state machine
4. `trellis/scripts/common/task_context.py` — rethink init-context approach
5. `trellis/scripts/common/cli_adapter.py` — reconcile platform sets

**Phase 3 — Agent/Hook Porting**
1. Claude agents: Port customizations to `trellis-*.md` naming
2. Claude hooks: Port customizations to `shared-hooks/`
3. Codex agents: Rename to `trellis-*.toml`
4. Codex hooks: Merge upstream additions

### 9.3 Overlay-Only Content is Safe

112 files (64%) are hiskens-only and require no upstream coordination. These include:
- All spec guides (Python, MATLAB, general)
- All Nocturne integration scripts
- All search scripts
- All trellis-meta skill references
- Most agent skills

### 9.4 Deprecated Content Should Be Marked

The multi-agent pipeline files and worktree.yaml are still shipped by the overlay but upstream no longer supports them. Consider:
- Adding deprecation notices to these files
- Planning their removal in a future overlay version
- Updating downstream projects that may depend on them

### 9.5 Wasted Overlay Weight

3 files are byte-identical to upstream v0.4 and can be removed:
- `trellis/scripts/common/__init__.py`
- `trellis/scripts/get_developer.py`
- `trellis/scripts/__init__.py`

Additionally, `trellis/scripts/get_context.py` differs by only 1 blank line.

---

*End of report. Generated by Research Agent #3 for the v0.5.0-beta.14 sync investigation.*
