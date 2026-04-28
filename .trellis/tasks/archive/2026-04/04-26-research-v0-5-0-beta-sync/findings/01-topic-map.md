# Trellis v0.4.0-beta.10 → v0.5.0-beta.14: Behavior-Level Changelog for Overlay Maintainers

> Research agent #1 output. 179 commits, 625 files changed. Focus: contract changes between upstream base templates and overlay layering.

---

## 1. Executive Summary

Upstream Trellis underwent a **skill-first architectural refactor** (v0.5.0) that restructured the entire template system around a single `common/` source of truth with per-platform resolution. The biggest overlay-relevant changes are:

1. **Template system rewrite**: All 14 platforms now consume from `packages/cli/src/templates/common/` (commands + skills) instead of per-platform copies. Per-platform `index.ts` files were gutted and replaced with `createTemplateReader()` from `template-utils.ts`.
2. **Claude hooks migrated to shared**: `packages/cli/src/templates/claude/hooks/` was deleted; all hooks now live in `shared-hooks/` and are written to every agent-capable platform (Claude, Cursor, CodeBuddy, Droid, Gemini, Qoder, Copilot, Kiro).
3. **Sub-agent rename + model change**: `implement`/`check`/`research` agents renamed to `trellis-implement`/`trellis-check`/`trellis-research` across all 10 platforms. Hardcoded `model: opus` dropped from all agent frontmatters.
4. **Task lifecycle changes**: `task.py init-context` removed; JSONL files seeded at `task.py create` time. `task.py start` now transitions `planning → in_progress`. Phase 1.3 is now agent-curated.
5. **iFlow removed, Droid added**: iFlow platform deleted entirely. Factory Droid added as new commands-only platform.
6. **Multi-Agent Pipeline removed**: `multi_agent/` scripts, `worktree.yaml`, `shell-archive/`, `phase.py`, `registry.py`, `create_bootstrap.py` all deleted.
7. **Workflow enforcement v2**: New `inject-workflow-state.py` hook replaces Ralph Loop. Per-turn breadcrumb via `UserPromptSubmit` (was `SubagentStop`).
8. **Migration system hardened**: Breaking-change gate in `update.ts`, 15 beta manifests, `reason` field on MigrationItem, mandatory `migrationGuide` enforcement.

**Overlay impact**: Hiskens overlay ships custom hooks (`session-start.py`, `inject-subagent-context.py`, `ralph-loop.py`, `statusline.py`, `statusline-bridge.py`, `todo-enforcer.py`, `intent-gate.py`, `context-monitor.py`, `parse_sub2api_usage.py`), custom agents, custom commands, and custom scripts under `overlays/hiskens/templates/`. The upstream shared-hooks migration and template restructuring are the highest-risk areas.

---

## 2. Theme-by-Theme Breakdown

### 2.1 Task Lifecycle Changes

**What changed:**
- `task.py init-context` command removed (commits `8b75d9c`, `9b92941`). `task.py create` now seeds `implement.jsonl` and `check.jsonl` with a single `{"_example": "..."}` line.
- `task.py start` now flips task status from `planning` to `in_progress` (`50149f4`).
- Phase 1.3 rewritten: AI curates jsonl directly with spec + research paths. Code paths explicitly forbidden in jsonl.
- `task_store.py` `cmd_create` drops `current_phase` and `next_action` legacy fields (`c5387df`, `b323e93`).
- `task_context.py` gutted: `cmd_init_context`, `get_implement_backend`, `get_implement_frontend`, `get_check_context` all deleted.

**Representative commits:**
- `50149f4` fix(task): transition planning → in_progress on `task.py start`
- `8b75d9c` refactor(task): drop init-context, seed implement/check jsonl on create
- `9b92941` feat(workflow): remove task.py init-context, make Phase 1.3 agent-curated
- `b323e93` chore(cleanup): remove phase.py + create_bootstrap.py + TaskData dead fields
- `c5387df` feat: workflow-enforcement-v2 + slim workflow.md + trim SessionStart payload

**Files most affected:**
- `packages/cli/src/templates/trellis/scripts/task.py`
- `packages/cli/src/templates/trellis/scripts/common/task_context.py`
- `packages/cli/src/templates/trellis/scripts/common/task_store.py`
- `packages/cli/src/templates/trellis/workflow.md`

**Overlay impact:**
- **HIGH**: Overlay ships `overlays/hiskens/templates/trellis/scripts/task.py` and `common/task_context.py`/`task_store.py`. These need surgical port.
- Overlay's `task.py` likely has `init-context` handling that must be removed.
- Overlay's `task_store.py` may still write `current_phase`/`next_action` — must drop.
- Overlay's `get_context.py` may reference `--mode record` (dropped in v0.5) — verify.

---

### 2.2 Hook System

**What changed:**
- **Claude hooks migrated to shared** (`4476844`): `packages/cli/src/templates/claude/hooks/` (4 files, 1807 lines) deleted. All hooks now in `packages/cli/src/templates/shared-hooks/` (`session-start.py`, `inject-subagent-context.py`, `inject-workflow-state.py`, `statusline.py`).
- **Ralph Loop deleted**: `ralph-loop.py` removed from all platforms. Replaced by `inject-workflow-state.py` via `UserPromptSubmit` hook.
- **SessionStart context announcement** (`b0ea242`): All 4 session-start implementations now emit a one-shot Chinese notice on first reply.
- **Curated jsonl gate** (`279b542`, `b34cabe`): Session-start hooks now check for at least one `file` field in jsonl before reporting `READY`. Seed-only jsonl surfaces `PLANNING (Phase 1.3)`.
- **Windows fixes** (`192dabb`, `7e58432`, `8aead3b`): `sys.platform == "win32"` → `.startswith("win")`; GBK encoding fix synced; `CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR=1` pinned in settings.
- **Workflow enforcement v2** (`c5387df`): New `inject-workflow-state.py` reads `[workflow-state:STATUS]` tags from `workflow.md`. Supports `no_task` pseudo-status.
- **Codex hooks require opt-in** (`c5387df`): `features.codex_hooks = true` needed in `~/.codex/config.toml`.

**Representative commits:**
- `4476844` feat: claude hooks migrate to shared + 0.5.0 migration manifest
- `c5387df` feat: workflow-enforcement-v2 + slim workflow.md + trim SessionStart payload
- `b0ea242` feat(hooks): announce SessionStart context in first reply
- `279b542` fix(session-start): require curated jsonl entry for READY status
- `192dabb` fix(statusline): avoid typed detach on Windows streams
- `857b243` fix(cli): harden session-start workflow guidance

**Files most affected:**
- `packages/cli/src/templates/shared-hooks/*.py` (all new)
- `packages/cli/src/templates/claude/hooks/` (deleted)
- `packages/cli/src/templates/codex/hooks/session-start.py`
- `packages/cli/src/templates/copilot/hooks/session-start.py`
- `packages/cli/src/templates/opencode/plugins/session-start.js`
- `packages/cli/src/templates/opencode/plugins/inject-workflow-state.js`
- `packages/cli/src/templates/claude/settings.json`

**Overlay impact:**
- **CRITICAL**: Overlay ships 9 custom hook files under `overlays/hiskens/templates/claude/hooks/`. The upstream migration to `shared-hooks/` means:
  - Overlay's `session-start.py` must be reconciled with upstream's shared version (now 577 lines, includes `_has_curated_jsonl_entry`, `FIRST_REPLY_NOTICE`, Phase 1.3 gate).
  - Overlay's `inject-subagent-context.py` must be reconciled with upstream shared version (now 641 lines, includes `read_jsonl_entries` seed-row skip, `buildPullBasedPrelude` for Class-2 platforms).
  - Overlay's `ralph-loop.py` is **deleted upstream** — must decide whether to keep or drop.
  - Overlay's `statusline.py` must be reconciled with upstream shared version (Windows fix).
  - Overlay-only hooks (`todo-enforcer.py`, `intent-gate.py`, `context-monitor.py`, `parse_sub2api_usage.py`, `statusline-bridge.py`) are unaffected by upstream changes but must still be installed correctly.
- **CRITICAL**: `claude/settings.json` changed: `SubagentStop` → `UserPromptSubmit`, `ralph-loop.py` → `inject-workflow-state.py`. Overlay's `settings.overlay.json` (referenced in `overlay.yaml`) must be updated.

---

### 2.3 CLI Commands (init, update)

**What changed:**
- **init.ts** (`bbe6834`, `3d1c25c`, `e988c79`, `60fb429`, `19374ff`):
  - Joiner onboarding: new path for developers joining an existing Trellis project (creates `00-join-<slug>` task).
  - Polyrepo detection via sibling `.git` scan (up to 2 levels deep).
  - Re-init fast path for adding platforms/developers.
  - Python floor relaxed from 3.10 to 3.9.
  - Extracted Python version check helpers.
- **update.ts** (`2374433`, `d0e04ab`, `765a1f3`, `25a3337`, `1a25dd7`):
  - Breaking-change gate: hard-stop when manifest is breaking + `recommendMigrate` and user didn't pass `--migrate`.
  - `workflow.md` included in template set (was excluded, causing upgrade bug).
  - Stack overflow fix in backup phase (iterative traversal, skip `.backup-*` and `node_modules`).
  - Backup excludes `/worktrees/` paths.
  - `update.skip` bypassed for breaking releases.
  - Confirm prompt redesign: default changed from Skip to Backup-rename.
  - Build adds `clean` step before `tsc`.

**Representative commits:**
- `2374433` feat(update): breaking-change gate + full command→skill migration for 0.5.0-beta.0
- `d0e04ab` fix(update): prevent stack overflow during backup phase
- `bbe6834` feat(cli): joiner onboarding + AI-facing bootstrap PRDs
- `3d1c25c` feat(cli): detect polyrepo layouts via sibling .git scan
- `765a1f3` fix(update): include workflow.md in template set

**Files most affected:**
- `packages/cli/src/commands/init.ts`
- `packages/cli/src/commands/update.ts`
- `packages/cli/src/utils/project-detector.ts`
- `packages/cli/src/utils/task-json.ts` (new)

**Overlay impact:**
- **MEDIUM**: Overlay doesn't override `init.ts` or `update.ts` directly, but the overlay loader (`overlay.ts`) consumes the output. No direct collision.
- **LOW**: The `task-json.ts` canonical shape (24 fields) should match overlay's `task_store.py` output. Verify overlay's `task_store.py` cmd_create emits the same 24 fields.

---

### 2.4 Configurators

**What changed:**
- **All 14 configurators** rewritten to use `common/` templates + `resolvePlaceholders()` + `writeSkills()`/`writeAgents()`/`writeSharedHooks()` helpers.
- **Claude configurator** (`4476844`): Now calls `writeSharedHooks()` instead of copying `claude/hooks/`. Excludes `commands/` and `hooks/` dirs from `copyDirFiltered`.
- **New platforms upgraded to agent-capable** (`efccf6f`): Qoder, CodeBuddy, Droid, Cursor, Gemini, Kiro, Copilot all now get hooks + agents + settings.
- **Qoder split** (`d949c37`): Session-boundary commands (`finish-work`, `continue`) written as flat `.qoder/commands/trellis-{name}.md` files; auto-trigger skills go to `.qoder/skills/trellis-{name}/SKILL.md`.
- **iFlow configurator deleted** (`efccf6f`).
- **Droid configurator added** (`0015246`).
- **TemplateContext** added to `AI_TOOLS` registry (`700e7d3`): each platform now has `cmdRefPrefix`, `executorAI`, `userActionLabel`, `agentCapable`, `hasHooks`, `cliFlag`.
- **shared.ts** (`700e7d3`, `d949c37`, `d2c6682`, `9b92941`, `a5e3285`, `79801ed`): Grew by 405 lines. New helpers: `resolveAllAsSkills`, `resolveCommands`, `resolveSkills`, `writeSkills`, `writeAgents`, `writeSharedHooks`, `applyPullBasedPreludeMarkdown`, `applyPullBasedPreludeToml`, `wrapWithSkillFrontmatter`, `wrapWithCommandFrontmatter`, `COMMAND_DESCRIPTIONS`, `SKILL_DESCRIPTIONS`.

**Representative commits:**
- `700e7d3` feat: skill-first template refactor — common source + 14 platform unified output
- `efccf6f` feat: add hooks + agents for 7 platforms, remove iFlow/multi-agent/Ralph Loop
- `4476844` feat: claude hooks migrate to shared + 0.5.0 migration manifest
- `d949c37` feat(qoder): split session-boundary commands from auto-trigger skills
- `0015246` feat(platform): add Factory Droid support

**Files most affected:**
- `packages/cli/src/configurators/*.ts` (all 17 files)
- `packages/cli/src/configurators/shared.ts`
- `packages/cli/src/configurators/index.ts`
- `packages/cli/src/types/ai-tools.ts`

**Overlay impact:**
- **MEDIUM**: Overlay doesn't override configurators, but the overlay loader (`overlay.ts`) must understand the new `TemplateContext` and `common/` template resolution. If overlay adds new platforms or modifies template resolution, it must align with `shared.ts` helpers.
- **LOW**: `ai-tools.ts` dropped `iflow` from `AITool`/`TemplateDir`/`CliFlag` unions and added `droid`. Overlay's `overlay.yaml` `compatible_upstream` field should be updated to `>=0.5.0`.

---

### 2.5 Migration System

**What changed:**
- **15 new manifests** for 0.5.0-beta.0 through beta.14.
- **0.5.0-beta.0 manifest** (`403657d`, `2374433`): 126 safe-file-delete entries + 68 rename entries. Covers skill-first refactor cleanup, multi-agent removal, iFlow drop.
- **0.5.0-beta.5 manifest** (`79801ed`): 30 rename entries for `trellis-` prefix sub-agents across 10 platforms.
- **MigrationItem gains `reason` field** (`2374433`): per-entry context in confirm prompt.
- **Mandatory migrationGuide enforcement** (`8667520`): `create-manifest.js` rejects breaking manifests without `migrationGuide`.
- **Manifest continuity guard** (`44233e1`): Restores accidentally deleted `0.5.0-beta.10.json`.

**Representative commits:**
- `403657d` feat(release): v0.5.0-beta.0 migration manifest + docs changelog
- `2374433` feat(update): breaking-change gate + full command→skill migration for 0.5.0-beta.0
- `79801ed` feat(agents)!: trellis- prefix sub-agents + drop model: opus hardcoding
- `8667520` fix(migrations): back-fill missing migrationGuides + enforce on future breaking
- `44233e1` feat(release): manifest continuity guard + create-manifest hardening

**Files most affected:**
- `packages/cli/src/migrations/manifests/0.5.0-beta.*.json` (15 files)
- `packages/cli/src/types/migration.ts`
- `packages/cli/scripts/create-manifest.js`
- `packages/cli/src/commands/update.ts`

**Overlay impact:**
- **LOW**: Overlay doesn't ship migration manifests. However, downstream consumers upgrading from v0.4.x will need `--migrate` to pass the breaking-change gate.
- **MEDIUM**: Overlay's `exclude.yaml` excludes `claude/commands/trellis/before-dev.md` and `claude/commands/trellis/check.md`. Upstream renamed/removed many command paths. Verify overlay exclusions still match upstream paths.

---

### 2.6 Templates — Claude/Codex/CodeBuddy/etc

**What changed:**
- **Skill-first refactor** (`700e7d3`): All per-platform command/skill templates deleted. New `common/` directory has 2 commands (`start.md`, `finish-work.md`) + 6 skills (`brainstorm.md`, `before-dev.md`, `break-loop.md`, `check.md`, `update-spec.md`, `parallel.md`).
- **Commands vs Skills split**: "Both" platforms (Claude, Cursor, CodeBuddy, Droid, Gemini, Qoder, Copilot, Kiro) get `start` + `finish-work` as commands, rest as `trellis-*` skills. "Skill-only" platforms (Codex) get everything as skills.
- **Agent rename** (`79801ed`): `check.md` → `trellis-check.md`, `implement.md` → `trellis-implement.md`, `research.md` → `trellis-research.md`. `debug.md`, `dispatch.md`, `plan.md` deleted.
- **Pull-based prelude** (`d2c6682`): Class-2 platforms (Codex, Copilot, Gemini, Qoder) get "Load Trellis Context First" prelude prepended to agent definitions.
- **Research agent gets write capability** (`d2c6682`): Added Write + Bash tools across 7 platforms. Codex `sandbox_mode` changed from `read-only` to `workspace-write`.
- **continue.md** added (`d2c6682`): New command for phase index + next-step selector.
- **Codex config.toml** (`c5387df`): Added feature-flag warning for `codex_hooks`.
- **Codex hooks.json** (`c5387df`): Added `UserPromptSubmit` hook.

**Representative commits:**
- `700e7d3` feat: skill-first template refactor — common source + 14 platform unified output
- `79801ed` feat(agents)!: trellis- prefix sub-agents + drop model: opus hardcoding
- `d2c6682` feat: workflow rewrite + pull-based sub-agent context for class-2 platforms
- `fe1d1ff` fix(codex): trellis-check workspace-write + self-fix behavior

**Files most affected:**
- `packages/cli/src/templates/common/` (new, 8 files)
- `packages/cli/src/templates/claude/agents/` (3 agents renamed, 3 deleted)
- `packages/cli/src/templates/claude/commands/` (all 13 deleted)
- `packages/cli/src/templates/codex/agents/` (3 renamed, 3 deleted)
- `packages/cli/src/templates/codex/codex-skills/parallel/SKILL.md` (deleted)
- `packages/cli/src/templates/codex/skills/start/SKILL.md` (updated)
- `packages/cli/src/templates/codex/config.toml` (new content)
- `packages/cli/src/templates/codex/hooks.json` (new)
- All other platform `agents/`, `commands/`, `skills/` directories

**Overlay impact:**
- **CRITICAL**: Overlay ships its own `claude/agents/` (8 files), `claude/commands/` (20 files), `claude/skills/` (3 files), `codex/agents/` (6 files), `codex/hooks.json`, and `agents/skills/` (12 files). These all use old naming (`check.md`, `implement.md`, not `trellis-check.md`).
- Overlay's agents must be renamed to `trellis-*.md` to match upstream convention.
- Overlay's commands must be evaluated against the new `common/` templates — many upstream commands were deleted or merged.
- Overlay's `codex/hooks.json` must add `UserPromptSubmit` hook.
- Overlay's `codex/agents/*.toml` must add pull-based prelude and drop `model: opus`.

---

### 2.7 Trellis Scripts

**What changed:**
- **Multi-Agent Pipeline removed** (`efccf6f`): `multi_agent/` directory (8 files, ~3000 lines) deleted. `worktree.yaml` deleted. `shell-archive/` deleted.
- **Dead code cleanup** (`b323e93`): `common/phase.py` (254 lines), `common/registry.py` (335 lines), `create_bootstrap.py` (298 lines), `common/worktree.py` (305 lines) all deleted.
- **New module** (`d2c6682`): `common/workflow_phase.py` (176 lines) — extracts step-level content from `workflow.md`, supports platform filtering.
- **config.py** (`efccf6f`): Inlined `parse_simple_yaml` from deleted `worktree.py` (+132 lines).
- **cli_adapter.py** (`0015246`, `a5e3285`, `efccf6f`): Added `droid` platform. Fixed `trellis-` prefix for Codex/Kiro skill paths. Added `--platform` arg plumbing. Removed `.agents` from `_ALL_PLATFORM_CONFIG_DIRS`.
- **task.py** (`efccf6f`, `9b92941`, `50149f4`, `6877f92`): Removed `init-context` and `create-pr` subcommands. Added `planning → in_progress` transition in `cmd_start`.
- **task_context.py** (`9b92941`): Gutted — `cmd_init_context` and all default content generators removed.
- **task_store.py** (`9b92941`, `c5387df`, `efccf6f`): Added `_has_subagent_platform`, `_write_seed_jsonl`, `_SEED_EXAMPLE`. Dropped `current_phase`/`next_action` from `cmd_create`.
- **git_context.py** (`d2c6682`): Added `--mode phase` with `--step` and `--platform` args.
- **types.py** (`b323e93`): Dropped `current_phase` and `next_action` from `TaskData`.
- **Unchanged scripts**: `get_context.py`, `add_session.py`, `init_developer.py`, `get_developer.py`, `search/*.py`, `nocturne_client.py`, `promote-to-nocturne.py`, `sync-trellis-to-nocturne.py`, `init-nocturne-namespace.py`, `common/git.py`, `common/developer.py`, `common/packages_context.py`, `common/context_assembly.py`, `common/session_context.py`, `common/io.py`, `common/log.py`, `common/paths.py`, `common/task_queue.py`, `common/tasks.py`, `common/task_utils.py`, `common/__init__.py`, `scripts/__init__.py`, `gitignore.txt`.

**Representative commits:**
- `efccf6f` feat: add hooks + agents for 7 platforms, remove iFlow/multi-agent/Ralph Loop
- `b323e93` chore(cleanup): remove phase.py + create_bootstrap.py + TaskData dead fields
- `d2c6682` feat: workflow rewrite + pull-based sub-agent context for class-2 platforms
- `9b92941` feat(workflow): remove task.py init-context, make Phase 1.3 agent-curated
- `0015246` feat(platform): add Factory Droid support

**Files most affected:**
- `packages/cli/src/templates/trellis/scripts/common/workflow_phase.py` (new)
- `packages/cli/src/templates/trellis/scripts/common/config.py`
- `packages/cli/src/templates/trellis/scripts/common/cli_adapter.py`
- `packages/cli/src/templates/trellis/scripts/task.py`
- `packages/cli/src/templates/trellis/scripts/common/task_context.py`
- `packages/cli/src/templates/trellis/scripts/common/task_store.py`
- `packages/cli/src/templates/trellis/scripts/common/git_context.py`
- `packages/cli/src/templates/trellis/scripts/common/types.py`
- `packages/cli/src/templates/trellis/index.ts`
- Deleted: `multi_agent/*`, `create_bootstrap.py`, `common/phase.py`, `common/registry.py`, `common/worktree.py`, `worktree.yaml`

**Overlay impact:**
- **HIGH**: Overlay ships custom versions of `task.py`, `task_context.py`, `task_store.py`, `cli_adapter.py`, `config.py`, `git_context.py`, `common/types.py`, and `index.ts` under `overlays/hiskens/templates/trellis/scripts/`.
- Each of these must be diffed against upstream and ported.
- Overlay's `multi_agent/` scripts, `create_bootstrap.py`, `phase.py`, `registry.py`, `worktree.py` should be deleted if they exist.
- Overlay's `workflow_phase.py` must be added.
- Overlay's `get_context.py` must be checked for `--mode record` usage (dropped upstream).

---

### 2.8 Skills (Marketplace)

**What changed:**
- **4 marketplace skills imported** (`192cad0`): `contribute`, `first-principles-thinking`, `python-design`, `trellis-meta`. Installed into `.agents/skills/`.
- These are consumed by Codex/Qoder/CodeBuddy/OpenCode via the shared `.agents/skills/` layer.

**Representative commits:**
- `192cad0` chore(skill): import 4 marketplace skills

**Files most affected:**
- `.agents/skills/contribute/SKILL.md`
- `.agents/skills/first-principles-thinking/SKILL.md` + references/
- `.agents/skills/python-design/SKILL.md`
- `.agents/skills/trellis-meta/SKILL.md` + references/

**Overlay impact:**
- **LOW**: These are project-local skills in the publisher repo, not overlay templates. Downstream consumers don't get them unless overlay explicitly ships them.
- Overlay already ships `trellis-meta` skill under `overlays/hiskens/templates/agents/skills/trellis-meta/`. Verify it's not stale compared to upstream's imported version.

---

### 2.9 Docs / Spec

**What changed:**
- **Spec files updated** for platform-integration, directory-structure, script-conventions, migrations, quality-guidelines.
- **Docs-site submodule** bumped 20+ times for changelog updates.
- **Changelog voice convention** documented (`ef5e384`).
- **Release-track lessons** captured (`5cce25c`, `c5c5928`).
- **PEP 604 + `__future__` rule** for distributed Python templates (`f6a2ebb`, `7e58432`).
- **Agent-Curated JSONL Contract** documented (`ffeec47`).

**Representative commits:**
- `ef5e384` docs(spec): capture changelog voice convention
- `6c34762` docs(spec): document polyrepo detection + CLI ↔ runtime schema parity
- `16f8a71` docs(spec): Task → Package Binding Contract in script-conventions
- `ffeec47` docs(spec): Agent-Curated JSONL Contract + docs-site sync matrix

**Overlay impact:**
- **LOW**: Overlay ships its own spec files under `overlays/hiskens/templates/trellis/spec/`. These are independent of upstream spec changes unless overlay references upstream spec paths.

---

### 2.10 Build / Release Plumbing

**What changed:**
- **package.json** (`2374433`): Build now runs `clean && tsc && copy-templates`. Version bumped to 0.5.0-beta.0+.
- **check-docs-changelog.js** (`57651e8`): Pre-release guard added.
- **15 beta manifests** generated.
- **Debug mode** (`d0e04ab`): `DEBUG=1` / `TRELLIS_DEBUG=1` now prints full stack traces.

**Overlay impact:**
- **LOW**: No direct overlay impact.

---

## 3. Top 10 Highest-Overlay-Risk Commits

| Rank | Commit | Risk | Rationale |
|------|--------|------|-----------|
| 1 | `4476844` feat: claude hooks migrate to shared | **CRITICAL** | Deletes `claude/hooks/` (4 files, 1807 lines). Overlay ships 9 custom hooks in same path. Must reconcile each with shared-hooks/ versions. |
| 2 | `700e7d3` feat: skill-first template refactor | **CRITICAL** | Deletes all per-platform commands/skills. Overlay ships 20+ command files and 12+ skill files under `claude/`. Must align with common/ template system. |
| 3 | `79801ed` feat(agents)!: trellis- prefix sub-agents | **CRITICAL** | Renames all agents to `trellis-*.md`. Overlay agents use old names. Must rename + drop `model: opus`. |
| 4 | `c5387df` feat: workflow-enforcement-v2 | **HIGH** | New `inject-workflow-state.py` hook, `UserPromptSubmit` replaces `SubagentStop`, settings.json changes. Overlay settings.overlay.json must update. |
| 5 | `9b92941` feat(workflow): remove task.py init-context | **HIGH** | Removes `init-context` command, seeds jsonl at create time. Overlay's task.py and task_context.py likely have custom init-context logic. |
| 6 | `efccf6f` feat: add hooks + agents for 7 platforms | **HIGH** | Deletes multi_agent/, worktree.yaml, phase.py, registry.py, create_bootstrap.py. Overlay may have references to these. |
| 7 | `d2c6682` feat: workflow rewrite + pull-based | **HIGH** | New `workflow_phase.py`, `get_context.py --mode phase`, pull-based prelude for Codex/Copilot/Gemini/Qoder agents. Overlay agents need prelude. |
| 8 | `b323e93` chore(cleanup): remove phase.py + create_bootstrap.py | **MEDIUM** | Deletes files overlay may reference. Verify overlay doesn't import deleted modules. |
| 9 | `0015246` feat(platform): add Factory Droid support | **MEDIUM** | New platform in cli_adapter.py, AI_TOOLS registry. Overlay's cli_adapter.py must add droid branches. |
| 10 | `2374433` feat(update): breaking-change gate | **MEDIUM** | Breaking releases now require `--migrate`. Downstream consumers will hit this gate. Overlay manifest compatibility should be bumped. |

---

## 4. Open Questions for Phase B Drift Investigator (Agent #3)

1. **Hook reconciliation**: For each of the 9 overlay hook files (`session-start.py`, `inject-subagent-context.py`, `ralph-loop.py`, `statusline.py`, `statusline-bridge.py`, `todo-enforcer.py`, `intent-gate.py`, `context-monitor.py`, `parse_sub2api_usage.py`), what is the exact delta between overlay version and upstream shared-hooks version? Which upstream behavioral changes must be ported, and which overlay customizations must be preserved?

2. **Agent rename completeness**: Overlay ships agents under `claude/agents/` (check.md, implement.md, research.md, debug.md, dispatch.md, plan.md, review.md, codex-implement.md). Upstream renamed only 3 agents and deleted 3. What should overlay do with `debug.md`, `dispatch.md`, `plan.md`, `review.md`, `codex-implement.md`?

3. **Command file alignment**: Overlay ships 20 command files under `claude/commands/trellis/`. Upstream deleted most commands (only `start` and `finish-work` remain as commands; rest are skills). Which overlay commands should be converted to skills? Which should stay as commands?

4. **settings.overlay.json update**: The overlay manifest references `templates/claude/settings.overlay.json`. Upstream `settings.json` changed significantly (env block, SubagentStop→UserPromptSubmit, ralph-loop→inject-workflow-state). What should the overlay settings file contain?

5. **exclude.yaml validity**: Overlay excludes `claude/commands/trellis/before-dev.md` and `claude/commands/trellis/check.md`. Upstream deleted `before-dev.md` (moved to common/skills/). Are these exclusions still meaningful?

6. **Script drift**: Overlay ships `task.py`, `task_context.py`, `task_store.py`, `cli_adapter.py`, `config.py`, `git_context.py`, `types.py`, `index.ts`. For each, what is the exact diff against upstream? Which upstream fixes (e.g., Windows encoding, curated jsonl gate, droid support) must be ported?

7. **common/workflow_phase.py**: This is a new upstream file. Does overlay need a custom version, or can it use upstream verbatim?

8. **Codex integration**: Overlay ships `codex/agents/*.toml`, `codex/hooks.json`, `codex/hooks/session-start.py`. Upstream added `UserPromptSubmit`, `config.toml` feature-flag warning, pull-based prelude, and `workspace-write` sandbox. Which of these must overlay adopt?

9. **trellis-meta skill drift**: Overlay ships `agents/skills/trellis-meta/` with references/. Upstream imported a marketplace `trellis-meta` skill into `.agents/skills/`. Are these the same content? If not, which should overlay ship?

10. **compatible_upstream version bump**: Overlay manifest says `compatible_upstream: ">=0.4.0-beta.10 <0.5.0"`. After sync, this should likely become `>=0.5.0-beta.14`. What breaking changes require a major version bump vs. minor?

11. **Nocturne integration**: Overlay ships `init-nocturne-namespace.py`, `promote-to-nocturne.py`, `sync-trellis-to-nocturne.py`, `nocturne_client.py`. These were unchanged upstream. Are they still compatible with the new task.json shape (no `current_phase`/`next_action`)?

12. **Search scripts**: Overlay ships `search/web_search.py`, `search/web_fetch.py`, `search/web_map.py`, `search/_common.py`, `search/API_CONFIG.md`. These were unchanged upstream. Verify they still work with new `config.py` (inlined YAML parser).

13. **Multi-agent cleanup**: Overlay ships `multi_agent/cleanup.py`, `create_pr.py`, `plan.py`, `start.py`, `status.py` under `trellis/scripts/`. Upstream deleted the entire `multi_agent/` directory. Should overlay delete these too, or keep them as custom extensions?

14. **Test coverage**: After overlay sync, what test matrix should validate that the overlay still works? (P0: init with overlay, P1: update with overlay, P2: hook execution, P3: agent spawn + context injection)

---

## Appendix: File Change Summary

### Files with upstream changes that overlay mirrors (HIGH RISK)
- `packages/cli/src/templates/claude/hooks/*.py` → `overlays/hiskens/templates/claude/hooks/*.py`
- `packages/cli/src/templates/claude/agents/*.md` → `overlays/hiskens/templates/claude/agents/*.md`
- `packages/cli/src/templates/claude/commands/trellis/*.md` → `overlays/hiskens/templates/claude/commands/trellis/*.md`
- `packages/cli/src/templates/claude/skills/*.md` → `overlays/hiskens/templates/claude/skills/*.md`
- `packages/cli/src/templates/claude/settings.json` → `overlays/hiskens/templates/claude/settings.overlay.json`
- `packages/cli/src/templates/codex/agents/*.toml` → `overlays/hiskens/templates/codex/agents/*.toml`
- `packages/cli/src/templates/codex/hooks.json` → `overlays/hiskens/templates/codex/hooks.json`
- `packages/cli/src/templates/codex/hooks/session-start.py` → `overlays/hiskens/templates/codex/hooks/session-start.py`
- `packages/cli/src/templates/trellis/scripts/*.py` → `overlays/hiskens/templates/trellis/scripts/*.py`
- `packages/cli/src/templates/trellis/scripts/common/*.py` → `overlays/hiskens/templates/trellis/scripts/common/*.py`
- `packages/cli/src/templates/trellis/workflow.md` → `overlays/hiskens/templates/trellis/spec/guides/index.md` (indirect)

### Files with upstream changes but NO overlay mirror (MEDIUM RISK — may affect downstream)
- `packages/cli/src/commands/init.ts` — joiner onboarding, polyrepo detection
- `packages/cli/src/commands/update.ts` — breaking-change gate, backup fixes
- `packages/cli/src/configurators/*.ts` — all rewritten for common/ templates
- `packages/cli/src/types/ai-tools.ts` — iFlow removed, Droid added, TemplateContext added
- `packages/cli/src/migrations/manifests/*.json` — 15 new manifests

### Files unchanged upstream (LOW RISK)
- `packages/cli/src/templates/trellis/scripts/get_context.py`
- `packages/cli/src/templates/trellis/scripts/add_session.py`
- `packages/cli/src/templates/trellis/scripts/init_developer.py`
- `packages/cli/src/templates/trellis/scripts/get_developer.py`
- `packages/cli/src/templates/trellis/scripts/search/*.py`
- `packages/cli/src/templates/trellis/scripts/nocturne_client.py`
- `packages/cli/src/templates/trellis/scripts/promote-to-nocturne.py`
- `packages/cli/src/templates/trellis/scripts/sync-trellis-to-nocturne.py`
- `packages/cli/src/templates/trellis/scripts/init-nocturne-namespace.py`
- `packages/cli/src/templates/trellis/scripts/common/git.py`
- `packages/cli/src/templates/trellis/scripts/common/developer.py`
- `packages/cli/src/templates/trellis/scripts/common/packages_context.py`
- `packages/cli/src/templates/trellis/scripts/common/context_assembly.py`
- `packages/cli/src/templates/trellis/scripts/common/session_context.py`
- `packages/cli/src/templates/trellis/scripts/common/io.py`
- `packages/cli/src/templates/trellis/scripts/common/log.py`
- `packages/cli/src/templates/trellis/scripts/common/paths.py`
- `packages/cli/src/templates/trellis/scripts/common/task_queue.py`
- `packages/cli/src/templates/trellis/scripts/common/tasks.py`
- `packages/cli/src/templates/trellis/scripts/common/task_utils.py`
- `packages/cli/src/templates/trellis/scripts/common/__init__.py`
- `packages/cli/src/templates/trellis/scripts/__init__.py`
- `packages/cli/src/templates/trellis/gitignore.txt`

---

## Appendix B: Commit-to-Theme Mapping (Quick Reference)

### Skill-First Refactor (Template System)
- `700e7d3` — Phase 0-3: common source, placeholder engine, delete 9 old dirs
- `efccf6f` — 7 platforms upgraded, shared-hooks, template-utils.ts, delete iFlow/multi-agent
- `4476844` — Claude hooks migrate to shared, 0.5.0 migration manifest (125 deletions)
- `d2c6682` — Workflow rewrite, pull-based prelude, research agent write capability
- `c5387df` — Workflow enforcement v2, slim workflow.md, trim SessionStart payload
- `79801ed` — trellis- prefix agents, drop model:opus, 30 rename migrations
- `d949c37` — Qoder commands/skills split, COMMAND_DESCRIPTIONS registry
- `d456e97` — Tighten task-creation trigger, delegate research to sub-agents
- `a5e3285` — Plumb --platform through init-context, fix skill path bugs
- `fe1d1ff` — Codex trellis-check workspace-write + self-fix
- `6877f92` — Backport dogfood edits to packaged templates

### Task Lifecycle
- `50149f4` — planning → in_progress on task.py start
- `8b75d9c` — Seed jsonl on create, drop init-context
- `9b92941` — Remove init-context, make Phase 1.3 agent-curated
- `b323e93` — Remove phase.py, create_bootstrap.py, TaskData dead fields

### Hook System
- `b0ea242` — Announce SessionStart context in first reply
- `192dabb` — Windows statusline typed detach fix
- `279b542` — Require curated jsonl entry for READY status
- `b34cabe` — Surface Phase 1.3 gate when jsonl only has seed row
- `857b243` — Harden session-start workflow guidance
- `7e58432` — Add __future__ annotations to shared hooks
- `8aead3b` — Sync GBK encoding fix to claude template
- `78acefd` — Clean up dangling Step refs
- `1688e3a` — Remove redundant start.md injection
- `e93b227` — Replace workflow.md full injection with compact ToC

### CLI Commands
- `2374433` — Breaking-change gate, command→skill migration
- `d0e04ab` — Prevent stack overflow in backup phase
- `765a1f3` — Include workflow.md in template set
- `25a3337` — Backup-rename writes inline .backup copy
- `1a25dd7` — Bypass update.skip for breaking releases
- `bbe6834` — Joiner onboarding + AI-facing bootstrap PRDs
- `3d1c25c` — Detect polyrepo layouts via sibling .git scan
- `60fb429` — Relax Python floor from 3.10 to 3.9
- `19374ff` — Extract Python version check helpers
- `e988c79` — Re-init fast path for adding platforms/developers
- `1b767f2` — Skip bootstrap task creation on re-init
- `4eaa2b5` — Shared TaskJson factory unifying init.ts + update.ts

### Configurators
- `0015246` — Add Factory Droid support
- `abc8514` — OpenCode update tracking + Windows hook cwd fix
- `5fbf961` — OpenCode plugin factory-function shape for 1.2.x

### Migration System
- `403657d` — v0.5.0-beta.0 migration manifest + docs changelog
- `8667520` — Back-fill migrationGuides + enforce on future breaking
- `44233e1` — Manifest continuity guard + create-manifest hardening
- `50a87b1` — Consolidate 0.5.0-beta.9 manifest
- `5abf877` — Add 0.5.0-beta.11 manifest
- `c800da3` — Add 0.5.0-beta.12 manifest
- `730c9a3` — Add 0.5.0-beta.13 manifest
- `45627fd` — Add 0.5.0-beta.14 manifest

### Docs / Spec
- `ef5e384` — Changelog voice convention
- `6c34762` — Polyrepo detection + CLI↔runtime schema parity
- `16f8a71` — Task→Package Binding Contract
- `ffeec47` — Agent-Curated JSONL Contract
- `f6a2ebb` — PEP 604 + __future__ rule
- `13cf30c` — Init dispatch wiring + .developer signal
- `6625042` — Docs-site audit + artifacts
- `c5c5928` — Release/Beta dual-track lessons
- `5cce25c` — Two Release-track mistakes from 0.4.0 audit
- `1541e98` — Docs-audit lessons in style-guide
- `f03775b` — Schema deprecation audit + hook no-silent-exit
- `f2e89e7` — SessionStart size constraint + __pycache__ gotcha

### Build / Release
- `57651e8` — check-docs-changelog.js pre-release guard
- `80bf0f1` — Close 4 coverage gaps from workflow-v2
- `bff5154` — Sync vi.mock + add regressions

### Marketplace Skills
- `192cad0` — Import 4 marketplace skills (contribute, first-principles-thinking, python-design, trellis-meta)

### Dogfood / Self-Update
- `9717c63`, `0fe3c70`, `54d27d7`, `e7314a4`, `6825d5c`, `f9ab324` — trellis self update, pre-release updates, hash syncs
