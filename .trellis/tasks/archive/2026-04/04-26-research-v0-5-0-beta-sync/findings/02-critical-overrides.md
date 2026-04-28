# Critical Overrides Analysis: v0.4.0-beta.10 -> v0.5.0-beta.14

## 1. Executive Verdict

| Category | Count | Files |
|----------|-------|-------|
| GREEN (no upstream change) | 1 | `overlay.ts` (file does not exist in upstream) |
| YELLOW (changed, manageable) | 15 | All configurators + commands + migration types |
| RED (deleted/renamed, high risk) | 4 | `claude/hooks/*.py` (all 4 deleted from claude-specific dir) |

**Biggest risks:**
1. **overlay.ts**: Does not exist upstream -- our overlay owns it entirely. No merge conflict.
2. **claude/hooks/*.py**: All 4 files deleted from `templates/claude/hooks/` and moved to `templates/shared-hooks/` (unified cross-platform). Our overlay injects into these paths -- the migration engine will delete old `.claude/hooks/*.py` files during `trellis update --migrate`.
3. **Configurators**: Massive refactor (skill-first architecture, `TemplateContext` placeholder system, `collectTemplates` for every platform). Every configurator rewritten.
4. **Migration manifests**: 18 new manifests (0.5.0-beta.*), beta.0 alone has 206 migration items (138 safe-file-delete + 68 rename). Breaking release gate requires `--migrate`.
5. **init.ts**: +680/-201 lines. New reinit flow, bootstrap/joiner task creation, Python 3.9 minimum (was 3.10).

---

## 2. `packages/cli/src/utils/overlay.ts`

**Verdict: GREEN -- file does not exist upstream.**

Upstream has no `overlay.ts` at either v0.4.0-beta.10 or v0.5.0-beta.14. The only changes in `packages/cli/src/utils/` between versions are:

- `project-detector.ts`: +146/-12 (monorepo detection, package discovery)
- `task-json.ts`: +76/-0 (new `emptyTaskJson` factory, `TaskJson` type)

**Overlay impact: NONE.** Our `overlay.ts` is a pure overlay addition. No upstream contract changes affect it.

---

## 3. `commands/init.ts` and `commands/update.ts`

### init.ts (+680 / -201 lines, 1118 total diff)

**Key changes:**

| Change | Risk | Detail |
|--------|------|--------|
| Python min version 3.9 (was 3.10) | LOW | `MIN_PYTHON_MAJOR=3, MIN_PYTHON_MINOR=9`. Exported `isSupportedPythonVersion()` and `requireSupportedPython()`. |
| `getPythonCommandForPlatform()` moved to `configurators/shared.ts` | MED | init.ts now imports from shared.ts. Our overlay may have its own Python detection. |
| New `slugifyDeveloperName()` | LOW | Unicode-safe slugification for task dir names. Used by bootstrap/joiner flows. |
| New `writeTaskSkeleton()` | MED | Idempotent task.json + prd.md + .current-task writer. Creates canonical task structure. |
| New `getBootstrapChecklistItems()` | LOW | Returns markdown checklist items (was structured `subtasks` in task.json). Task schema unified. |
| New `handleReinit()` | HIGH | Re-init fast path when `.trellis/` exists. Shows menu: "Add AI platform(s)", "Set up developer identity", "Full re-initialize". Our overlay may need to hook into reinit flow. |
| New `createBootstrapTask()` / `createJoinerOnboardingTask()` | MED | Auto-creates `00-bootstrap` or `00-join-{slug}` task dirs with task.json + prd.md. |
| Monorepo detection enhanced | MED | `detectMonorepo()` now returns `DetectedPackage[]`. Template strategy per package. |
| `createWorkflowStructure()` still called | LOW | Same import from `configurators/workflow.js`. |

**Overlay concern:** If our overlay modifies init behavior (e.g., custom platform selection, custom task creation), the new `handleReinit()` flow may bypass or conflict with overlay logic.

### update.ts (+266 / -75 lines, 528 total diff)

**Key changes:**

| Change | Risk | Detail |
|--------|------|--------|
| `workflowMdTemplate` replaces `worktreeYamlTemplate` | HIGH | `collectTemplateFiles()` now includes `.trellis/workflow.md` (was excluded). workflow.md is now script-parsed (Phase Index, workflow-state tags). Our overlay may have customized workflow.md. |
| `bypassUpdateSkip` parameter | MED | Breaking releases can bypass `update.skip` config. Enabled when `breaking && recommendMigrate && --migrate`. |
| `PROTECTED_PATHS` expanded | LOW | Now includes `.trellis/workspace/`, `.trellis/tasks/`, `.trellis/spec/`, `.trellis/.developer`, `.trellis/.current-task`. |
| `safe-file-delete` auto-executes | HIGH | No `--migrate` needed. Hash-verified deletion of deprecated files. 138 items in beta.0 alone. Our overlay files at old paths may be deleted if hash matches. |
| `breakingBypass` logic | MED | When breaking + recommendMigrate + --migrate, skips `update.skip` for both safe-file-delete AND template collection. |
| `shouldExcludeFromBackup` now exported | LOW | Added `/worktrees/` and `/worktree/` exclusions. Windows path normalization fix. |
| `collectAllFiles` stack-based rewrite | LOW | Fixes symlink/junction loop on Windows. No functional change for overlay. |
| Migration task auto-creation | MED | On breaking update, creates `.trellis/tasks/MM-DD-migrate-to-{version}/` with task.json + prd.md. Uses `emptyTaskJson()` factory. |
| `promptMigrationAction()` improved | LOW | Default is now `backup-rename` (safest). Shows per-migration `reason` field. |

**Overlay concern:** The `safe-file-delete` auto-execution is the biggest risk. If our overlay has files at paths listed in migration manifests (e.g., old `.claude/hooks/ralph-loop.py`, retired commands), and those files happen to match `allowed_hashes`, they will be silently deleted during `trellis update`.

---

## 4. Configurators

| Configurator | Changed? | + lines | - lines | Summary | Overlay Impact |
|--------------|----------|---------|---------|---------|----------------|
| `index.ts` | YES | +340/-186 | Massive refactor. `PLATFORM_FUNCTIONS` registry now uses `collectBothTemplates()`, `collectSharedHooks()`, `applyPullBasedPrelude*()`. Every platform gets `collectTemplates`. | **HIGH** -- overlay must align with new registry pattern |
| `shared.ts` | YES | +405/-5 | New `TemplateContext` placeholder resolution (`{{CMD_REF}}`, `{{EXECUTOR_AI}}`, `{{CLI_FLAG}}`, conditional `{{#FLAG}}`). New `resolveCommands()`, `resolveSkills()`, `resolveAllAsSkills()`, `writeSharedHooks()`, pull-based prelude injection. | **HIGH** -- core of skill-first architecture |
| `claude.ts` | YES | +49/-44 | Now uses `resolveCommands()`, `resolveSkills()`, `writeSharedHooks()`. Skips `commands/` and `hooks/` dirs from template copy (sourced from common templates). | **MED** -- our overlay claude hooks must use shared-hooks |
| `cursor.ts` | YES | +85/-43 | Complete rewrite. No longer copies template dir. Uses `resolveCommands()`, `resolveSkills()`, `writeAgents()`, `writeSharedHooks()`. | **MED** |
| `codex.ts` | YES | +49/-28 | Now `applyPullBasedPreludeToml()` for agents (class-2 pull-based). Excludes `session-start.py` and `inject-subagent-context.py` from shared hooks. | **HIGH** -- Codex hook exclusion affects overlay |
| `copilot.ts` | YES | +72/-31 | Now uses `resolveCommands()`, `resolveSkills()`, `applyPullBasedPreludeMarkdown()`. Agents use Cursor content + pull-based prelude. | **MED** |
| `gemini.ts` | YES | +100/-50 | Complete rewrite. Uses `resolveCommands()`, `resolveSkills()`, `writeAgents()`, `writeSharedHooks()`. TOML commands. | **MED** |
| `qoder.ts` | YES | +101/-50 | Complete rewrite. Uses `resolveCommands()`, `resolveSkills()`, `wrapWithCommandFrontmatter()`, `writeSharedHooks()`. | **MED** |
| `opencode.ts` | YES | +113/-55 | New `walkOpenCodeTemplateDir()` + `collectOpenCodeTemplates()` for update tracking. | **MED** |
| `codebuddy.ts` | YES | +93/-50 | Complete rewrite. Uses shared helpers, adds agents + hooks. | **MED** |
| `kiro.ts` | YES | +43/-20 | Now uses `resolveAllAsSkills()`, `writeAgents()`, `writeSharedHooks()`. | **MED** |
| `kilo.ts` | YES | +70/-35 | Uses `collectBothTemplates()`. | **LOW** |
| `antigravity.ts` | YES | +28/-14 | Uses `collectBothTemplates()`. | **LOW** |
| `windsurf.ts` | YES | +31/-14 | Uses `collectBothTemplates()`. | **LOW** |
| `droid.ts` | NEW | +43/-0 | New platform configurator. Factory Droid. Commands + skills + droids + hooks + settings. | **LOW** -- new platform, no overlay impact yet |
| `iflow.ts` | DELETED | -- | iFlow platform removed entirely. | **NONE** -- was not in overlay |
| `workflow.ts` | DELETED | -- | Empty file removed. | **NONE** |

**Key architectural shift:**
- **v0.4**: Each configurator copied its own template directory tree. Platform-specific commands, skills, hooks, agents all lived in separate `src/templates/{platform}/` dirs.
- **v0.5**: **Skill-first architecture**. Common templates live in `src/templates/common/`. Configurators use `resolveCommands()` (2 commands: start + finish-work) and `resolveSkills()` (5 skills: before-dev, brainstorm, break-loop, check, update-spec) from common source, then wrap with platform-specific frontmatter/paths. Hooks are unified in `src/templates/shared-hooks/`.

**Overlay impact:** If our overlay adds custom commands, skills, or hooks to any platform, we must now inject them through the `PLATFORM_FUNCTIONS` registry in `index.ts` AND ensure they work with the `TemplateContext` placeholder system.

---

## 5. Migration Manifests

### Count and Date Range

- **Total v0.5.0-beta manifests:** 18 files (beta.0 through beta.14)
- **Date range:** beta.0 is the massive breaking release; beta.1-beta.14 are incremental patches
- **Largest:** `0.5.0-beta.0.json` (80,787 bytes, 206 migrations)
- **Other large:** `0.5.0-beta.5.json` (19,920 bytes, 30 renames), `0.5.0-beta.9.json` (10,412 bytes, 4 safe-file-deletes)

### Schema (top-level fields)

```json
{
  "version": "0.5.0-beta.X",
  "description": "human-readable summary",
  "breaking": true/false,
  "recommendMigrate": true/false,
  "changelog": "markdown changelog",
  "migrationGuide": "markdown guide for AI-assisted fixes",
  "aiInstructions": "instructions for AI assistants",
  "notes": "additional notes",
  "migrations": [...]
}
```

### Migration Item Schema

```json
{
  "type": "rename" | "safe-file-delete",
  "from": "relative/path",
  "to": "relative/path",        // rename only
  "description": "human readable",
  "reason": "why prompted",      // NEW in v0.5
  "allowed_hashes": ["sha256"]   // safe-file-delete only
}
```

### Migration Type Distribution

| Manifest | Rename | Safe-file-delete | Breaking | recommendMigrate |
|----------|--------|------------------|----------|------------------|
| 0.5.0-beta.0 | 68 | 138 | true | true |
| 0.5.0-beta.5 | 30 | 0 | true | true |
| 0.5.0-beta.9 | 0 | 4 | false | false |
| 0.5.0-beta.12 | 0 | 0 | false | false |
| 0.5.0-beta.14 | 0 | 0 | false | false |
| Others (beta.1-4,6-8,10-11,13) | 0 | 0 | varies | varies |

### Path Collision with Overlay-Owned Files

**CRITICAL:** The beta.0 manifest includes safe-file-delete entries for paths that our overlay may own:

- `.claude/hooks/ralph-loop.py` -- deleted if hash matches
- `.claude/agents/debug.md`, `dispatch.md`, `plan.md` -- deleted if hash matches
- `.claude/commands/trellis/*.md` (7 retired commands) -- deleted if hash matches
- `.cursor/commands/trellis-*.md` (7 retired commands) -- deleted if hash matches
- `.trellis/scripts/multi_agent/*.py` (9 files) -- deleted if hash matches
- `.trellis/scripts-shell-archive/*` (17 files) -- deleted if hash matches

**The safety mechanism:** `allowed_hashes` -- only files whose SHA256 matches known upstream template hashes are deleted. If our overlay modified these files, the hash won't match and deletion is skipped with "skip-modified" warning.

**However:** If our overlay ADDED new files at these paths (not modified existing ones), the files won't have upstream hashes and won't be affected by safe-file-delete. But if our overlay KEPT pristine upstream copies of retired files, they WILL be deleted.

### Cumulative vs Incremental Contract

- **Cumulative:** `getMigrationsForVersion(from, to)` returns ALL migrations from versions > from and <= to. The migration system is cumulative -- running `trellis update --migrate` from 0.4.0 to 0.5.0-beta.14 applies beta.0, beta.5, and beta.9 migrations (and any others with non-empty migrations arrays).
- **Incremental:** Each manifest is independent. The `migrations/index.ts` loader sorts versions and filters applicable range.

---

## 6. `claude/hooks/*.py`

### v0.4.0-beta.10 (all deleted in v0.5.0)

| File | Lines | v0.5.0 Fate | Overlay Risk |
|------|-------|-------------|--------------|
| `session-start.py` | 397 | Moved to `templates/shared-hooks/session-start.py` (577 lines, heavily rewritten) | **HIGH** -- our overlay may depend on old session-start behavior |
| `inject-subagent-context.py` | 803 | Moved to `templates/shared-hooks/inject-subagent-context.py` (641 lines, rewritten) | **HIGH** -- core hook for sub-agent context |
| `ralph-loop.py` | 396 | **DELETED entirely** (Ralph Loop feature dropped) | **HIGH** -- safe-file-delete will remove if hash matches |
| `statusline.py` | 211 | Moved to `templates/shared-hooks/statusline.py` (219 lines, slightly updated) | **MED** |

### v0.5.0-beta.14 (new shared-hooks)

| File | Lines | Platforms Using It | Notes |
|------|-------|-------------------|-------|
| `session-start.py` | 577 | All hook-capable platforms | Adds `<first-reply-notice>` block (beta.14). CWD-robust root discovery. |
| `inject-subagent-context.py` | 641 | Hook-capable platforms (excluded for class-2 pull-based) | Multi-platform sub-agent context injection. |
| `inject-workflow-state.py` | 247 | All hook-capable platforms | **NEW** -- per-turn workflow breadcrumb hook. Reads workflow.md `[workflow-state:STATUS]` tags. |
| `statusline.py` | 219 | All hook-capable platforms | Claude Code status line display. |

### Hook Exclusion Rules (class-2 pull-based platforms)

Platforms that CANNOT use certain shared hooks:

- **Codex**: Excludes `session-start.py` and `inject-subagent-context.py` (hooks require `features.codex_hooks = true` in config.toml)
- **Gemini, Qoder, Copilot**: Excludes `inject-subagent-context.py` (sub-agents pull context via prelude instead)
- **Kiro**: No per-turn hook entry point, so `inject-workflow-state.py` not wired

**Overlay impact:** If our overlay adds custom hooks to `.claude/hooks/`, they will now be written alongside the shared hooks. The old claude-specific hooks directory is gone -- all hooks come from `shared-hooks/`.

---

## 7. Per-File Action List

| File Path | Status | Action Required | Priority |
|-----------|--------|-----------------|----------|
| `packages/cli/src/utils/overlay.ts` | GREEN (no upstream) | None -- pure overlay file | P3 |
| `packages/cli/src/commands/init.ts` | YELLOW (+680/-201) | Review `handleReinit()` flow for overlay conflicts. Check bootstrap/joiner task creation doesn't conflict with overlay task structure. | P2 |
| `packages/cli/src/commands/update.ts` | YELLOW (+266/-75) | Review `safe-file-delete` paths against overlay files. Verify `workflowMdTemplate` inclusion doesn't overwrite overlay workflow.md. Check `bypassUpdateSkip` behavior. | P1 |
| `packages/cli/src/configurators/index.ts` | YELLOW (+340/-186) | Update overlay platform registrations to use new `PLATFORM_FUNCTIONS` pattern with `collectTemplates`. | P1 |
| `packages/cli/src/configurators/shared.ts` | YELLOW (+405/-5) | Understand `TemplateContext` system. If overlay adds custom placeholders, extend `resolvePlaceholders()`. | P1 |
| `packages/cli/src/configurators/claude.ts` | YELLOW (+49/-44) | Verify overlay claude config works with `skipDirs: ["commands", "hooks"]` pattern. | P2 |
| `packages/cli/src/configurators/cursor.ts` | YELLOW (+85/-43) | Verify cursor config uses new shared helpers. | P2 |
| `packages/cli/src/configurators/codex.ts` | YELLOW (+49/-28) | **CRITICAL:** Codex excludes `session-start.py` and `inject-subagent-context.py`. If overlay depends on these for Codex, must override exclusion. | P1 |
| `packages/cli/src/configurators/copilot.ts` | YELLOW (+72/-31) | Verify copilot config with new skills + agents + shared hooks. | P2 |
| `packages/cli/src/configurators/gemini.ts` | YELLOW (+100/-50) | Verify gemini config with new TOML commands + pull-based prelude. | P2 |
| `packages/cli/src/configurators/qoder.ts` | YELLOW (+101/-50) | Verify qoder config with `wrapWithCommandFrontmatter()`. | P2 |
| `packages/cli/src/configurators/opencode.ts` | YELLOW (+113/-55) | Verify opencode with new `collectOpenCodeTemplates()`. | P2 |
| `packages/cli/src/configurators/codebuddy.ts` | YELLOW (+93/-50) | Verify codebuddy with agents + shared hooks. | P2 |
| `packages/cli/src/configurators/kiro.ts` | YELLOW (+43/-20) | Verify kiro with `writeAgents()` + `writeSharedHooks()`. | P2 |
| `packages/cli/src/configurators/kilo.ts` | YELLOW (+70/-35) | Verify kilo with `collectBothTemplates()`. | P3 |
| `packages/cli/src/configurators/antigravity.ts` | YELLOW (+28/-14) | Verify antigravity with `collectBothTemplates()`. | P3 |
| `packages/cli/src/configurators/windsurf.ts` | YELLOW (+31/-14) | Verify windsurf with `collectBothTemplates()`. | P3 |
| `packages/cli/src/configurators/droid.ts` | NEW (+43/-0) | No action unless overlay wants to support Droid. | P3 |
| `packages/cli/src/configurators/iflow.ts` | DELETED | iFlow removed. No overlay impact. | -- |
| `packages/cli/src/configurators/workflow.ts` | DELETED | Empty file removed. No impact. | -- |
| `packages/cli/src/types/ai-tools.ts` | YELLOW (+164/-21) | New `TemplateContext` interface. New platform `droid`. Removed `iflow`. If overlay references `iflow`, update. | P2 |
| `packages/cli/src/types/migration.ts` | YELLOW (+8/-1) | New `reason` field on `MigrationItem`. No breaking change. | P3 |
| `packages/cli/src/migrations/index.ts` | GREEN (no diff) | Unchanged between versions. | P3 |
| `packages/cli/src/migrations/manifests/0.5.0-beta.*.json` | NEW (18 files) | **CRITICAL:** Review all 206 beta.0 safe-file-delete `from` paths against overlay-owned files. Check `allowed_hashes` for any overlay files that might match. | P1 |
| `packages/cli/src/templates/claude/hooks/*.py` | DELETED (4 files) | All moved to `templates/shared-hooks/`. Overlay must update hook injection to target shared-hooks or per-platform hooks dir. | P1 |
| `packages/cli/src/templates/shared-hooks/*.py` | NEW (4 files) | New unified hook source. `index.ts` exports `getSharedHookScripts()`. | P2 |

---

## Scratch Files

Full diffs saved for reference:

- `scratch-02b-init-ts.diff` (1118 lines) -- init.ts full diff
- `scratch-02b-update-ts.diff` (528 lines) -- update.ts full diff
- `scratch-02b-configurators.diff` (2278 lines) -- all configurators full diff
