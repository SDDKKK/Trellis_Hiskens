# Research: Overlay Mapping

- **Query**: How the Hiskens overlay maps template files to root-level platform directories, and what controls which files get installed.
- **Scope**: internal
- **Date**: 2026-04-29

---

## 1. Overlay Directory Structure

`overlays/hiskens/templates/` contains four top-level subdirectories. Each
subdirectory name is the **overlay directory key** (`overlayDir`). The runtime
maps it to a root-level directory (`outputDir`) in the consumer project.

| Overlay subdir | Installed root dir | Description |
|---|---|---|
| `claude/` | `.claude/` | Claude Code agents, commands, hooks, skills, settings |
| `codex/` | `.codex/` | Codex agents, hooks, scripts |
| `agents/` | `.agents/` | Shared skills surfaced via `.agents/skills/` |
| `trellis/` | `.trellis/` | Workflow scripts, config, spec guides |

### Detailed tree (source → install target, excluding `__pycache__`)

```
agents/skills/<name>/SKILL.md          → .agents/skills/<name>/SKILL.md
  before-matlab-dev, before-python-dev, brainstorm,
  check-matlab, check-python, finish-work, improve-ut,
  parallel, record-session, retro, trellis-meta (+ references/)

claude/agents/<name>.md                → .claude/agents/<name>.md
  check, codex-implement, debug, dispatch, implement, plan, research
  review  ← EXCLUDED (see exclude.yaml)

claude/commands/trellis/<name>.md      → .claude/commands/trellis/<name>.md
  before-matlab-dev, before-python-dev, brainstorm-base, brainstorm,
  break-loop-base, break-loop, check-cross-layer-base, check-cross-layer,
  check-matlab, check-python, create-command, finish-work, improve-ut,
  integrate-skill, onboard, parallel, record-session, retro, start, update-spec

claude/hooks/<name>.py                 → .claude/hooks/<name>.py
  context-monitor, inject-subagent-context, intent-gate,
  parse_sub2api_usage, ralph-loop, session-start,
  statusline-bridge, statusline, todo-enforcer

claude/settings.overlay.json           → MERGED into .claude/settings.json (not copied as-is)

claude/skills/<name>/SKILL.md          → .claude/skills/<name>/SKILL.md
  github-explorer, grok-search, with-codex

codex/agents/<name>.toml               → .codex/agents/<name>.toml
  check, debug, implement, plan, research, review

codex/hooks.json                       → .codex/hooks.json
codex/hooks/<name>.py                  → .codex/hooks/<name>.py
  post-tool-use, session-start

codex/scripts/load-trellis-context.py  → .codex/scripts/load-trellis-context.py

trellis/config.yaml                    → .trellis/config.yaml
trellis/config/agent-models.example.json → .trellis/config/agent-models.example.json
trellis/scripts/**                     → .trellis/scripts/**
  (add_session, create_bootstrap, get_context, get_developer,
   init_developer, init-nocturne-namespace, nocturne_client,
   promote-to-nocturne, sync-trellis-to-nocturne, task,
   common/*.py, multi_agent/*.py, search/*.py)
trellis/spec/**                        → .trellis/spec/**
  guides/*.md (25 guide files)
  matlab/*.md + examples/
  python/*.md + examples/
trellis/templates/prd-template.md      → .trellis/templates/prd-template.md
trellis/worktree.yaml                  ← EXCLUDED (see exclude.yaml)
```

File counts (excluding `__pycache__` and `settings.overlay.json`):
- `agents/`: 34 files
- `claude/`: 40 files (includes the settings.overlay.json that is merged, not copied)
- `codex/`: 10 files
- `trellis/`: 90 files
- **Total**: ~174 source files

---

## 2. `exclude.yaml`

**File**: `overlays/hiskens/exclude.yaml`

```yaml
exclude:
  - claude/agents/review.md
  - trellis/worktree.yaml
```

**What it does**: Lists overlay-relative paths that should NOT be installed.

**Mechanism** (`configurators/index.ts` → `applyOverlayToProject` /
`applyOverlayToTemplateMap`):

1. `loadExcludeList(overlayPath)` reads `exclude.yaml` and returns the string list.
2. Each path is translated from overlay-relative → project-relative via
   `mapOverlayPathToProjectPath(excludePath, targets)`.
   - `claude/agents/review.md` → `.claude/agents/review.md`
   - `trellis/worktree.yaml` → `.trellis/worktree.yaml`
3. In `applyOverlayToProject` (runtime install): the translated paths are
   deleted from disk with `fs.rmSync(..., { recursive: true, force: true })`.
4. In `applyOverlayToTemplateMap` (update tracking): the translated paths are
   deleted from the template `Map<string,string>` via `files.delete(...)`.
5. Both functions also maintain `excludedPaths: Set<string>` so that even if
   the overlay template directory contains those files, they are never
   re-written.

**Rationale** (from comments in the file):
- `claude/agents/review.md` is kept as a reference definition only; the
  Hiskens workflow routes reviews through `/codex:adversarial-review`.
- `trellis/worktree.yaml` must be manually activated (copied to `.trellis/`)
  because auto-installing it would break projects without the Hiskens worktree
  layout.

---

## 3. Overlay Application Flow

### Key data structures

```typescript
// configurators/index.ts

const WORKFLOW_OVERLAY_TARGETS: OverlayTarget[] = [
  { overlayDir: "trellis", outputDir: ".trellis" },
];

const PLATFORM_OVERLAY_TARGETS: Record<AITool, OverlayTarget[]> = {
  "claude-code": [
    {
      overlayDir: "claude",
      outputDir: ".claude",
      settingsTargetPath: ".claude/settings.json",
    },
  ],
  codex: [
    { overlayDir: "codex", outputDir: ".codex" },
    { overlayDir: "agents", outputDir: ".agents" },
  ],
  // ...other platforms omitted (no hiskens templates for them)
};
```

### `applyPlatformOverlay(cwd, platformId, overlayName?)`

```
applyPlatformOverlay(cwd, "claude-code", "hiskens")
  → applyOverlayToProject(cwd, "hiskens", PLATFORM_OVERLAY_TARGETS["claude-code"])
```

`applyOverlayToProject` logic (simplified):
1. `resolveOverlayPath("hiskens")` → finds `overlays/hiskens/` on the search path.
2. `loadExcludeList(overlayPath)` → get excluded paths, map to project paths, delete from disk.
3. For each `OverlayTarget` (e.g., `{ overlayDir: "claude", outputDir: ".claude", settingsTargetPath: ".claude/settings.json" }`):
   - `getOverlayTemplatePath(overlayPath, "claude")` → `overlays/hiskens/templates/claude/`
   - `readOverlayFiles(...)` walks that directory (skipping `__pycache__`) → returns `Map<relative, content>`.
   - For each file:
     - If `relativePath == "settings.overlay.json"` **and** `target.settingsTargetPath` is set:
       - Read existing `.claude/settings.json` (or `{}`), call `mergeSettings(base, overlaySettingsPath)`, write back.
     - Else: write file to `.claude/<relativePath>` (with user-modified detection via hash file, producing `.new` files if modified).

### `applyWorkflowOverlay(cwd, overlayName?)`

```
applyWorkflowOverlay(cwd, "hiskens")
  → applyOverlayToProject(cwd, "hiskens", WORKFLOW_OVERLAY_TARGETS)
```

Same `applyOverlayToProject` function, but with only one target:
`{ overlayDir: "trellis", outputDir: ".trellis" }`.
No `settingsTargetPath` is set here, so no settings merge is triggered for
this target.

### `collectWorkflowOverlayTemplates(overlayName?)`

```
collectWorkflowOverlayTemplates("hiskens")
  → applyOverlayToTemplateMap(new Map(), "hiskens", WORKFLOW_OVERLAY_TARGETS)
```

`applyOverlayToTemplateMap` is the in-memory counterpart of
`applyOverlayToProject`:
- Starts from a given `Map<string, string>` (empty for workflow, or the
  upstream template map for platform).
- Applies excludes (deletes entries from the map).
- Reads overlay files and inserts/overwrites entries in the map.
- For `settings.overlay.json`: merges into the existing settings string in the
  map (not the filesystem).
- Returns the merged `Map<string, string>`.

This is used by `collectPlatformTemplates(platformId, overlayName?)`, which
starts from `PLATFORM_FUNCTIONS[platformId].collectTemplates()` (upstream
templates) and then patches in overlay files. The result feeds the update
tracker (`.trellis/.template-hashes.json`).

### Merge precedence

1. Upstream templates are installed first (by `configurePlatform` calling `PLATFORM_FUNCTIONS[id].configure(cwd)`).
2. Overlay is applied **after** with `applyPlatformOverlay` — overlay files **overwrite** upstream files of the same path.
3. Excluded paths are removed (from the map / from disk).
4. If an existing file was **user-modified** (hash mismatch), the overlay version is written as `<file>.new` instead of overwriting.

---

## 4. `settings_merge` in `overlay.yaml` / `settings.overlay.json`

**`overlay.yaml`** declares:
```yaml
settings_merge:
  claude: templates/claude/settings.overlay.json
```

This `settings_merge` key is parsed by `loadOverlayConfig()` into
`OverlayConfig.settings_merge`. However, the actual merge at install time is
**not** driven by this YAML field directly. Instead it is triggered by the
filename convention: any file named exactly `settings.overlay.json` inside a
target directory is intercepted by `isSettingsOverlayFile(relativePath)` and
routed to `mergeSettings()` rather than being copied verbatim.

**`mergeSettings(baseContent, overlaySettingsPath)`** (`utils/overlay.ts`):

The function performs a **deep, hook-aware merge**:

| Field | Merge strategy |
|---|---|
| `env` | Shallow merge — overlay keys overwrite base keys |
| `permissions` | Shallow merge for non-`deny` keys; `deny` array is unioned (deduped) |
| `hooks.<event>[]` | Matcher-keyed merge: if an overlay entry's `matcher` already exists in base, the entry is replaced; otherwise appended |
| All other top-level keys | Overlay value overwrites base value outright |

So for the Hiskens overlay the result is that `.claude/settings.json` ends up
with:
- `env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS = "1"`, `env.ENABLE_TOOL_SEARCH = "true"` added.
- `enabledPlugins`, `model`, `alwaysThinkingEnabled`, `effortLevel` set to overlay values.
- `hooks.UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `Stop` merged in.
  Matcher-keyed entries replace existing base matchers; new matchers are appended.

---

## 5. Cross-reference: overlay template files vs. installed project files

The task directory context refers to "31 overlay extra root files." Based on
the full tree above, the mapping is not purely 1:1 files — the overlay
installs **directories of files**, not individual root files. The precise
correspondence:

| Overlay source path | Installed project path | Notes |
|---|---|---|
| `overlays/hiskens/templates/claude/agents/check.md` | `.claude/agents/check.md` | Replaces upstream |
| `overlays/hiskens/templates/claude/agents/codex-implement.md` | `.claude/agents/codex-implement.md` | Hiskens-only |
| `overlays/hiskens/templates/claude/agents/debug.md` | `.claude/agents/debug.md` | Replaces upstream |
| `overlays/hiskens/templates/claude/agents/dispatch.md` | `.claude/agents/dispatch.md` | Hiskens-only |
| `overlays/hiskens/templates/claude/agents/implement.md` | `.claude/agents/implement.md` | Replaces upstream |
| `overlays/hiskens/templates/claude/agents/plan.md` | `.claude/agents/plan.md` | Replaces upstream |
| `overlays/hiskens/templates/claude/agents/research.md` | `.claude/agents/research.md` | Replaces upstream |
| `overlays/hiskens/templates/claude/agents/review.md` | **NOT INSTALLED** (excluded) | Reference only |
| `overlays/hiskens/templates/claude/commands/trellis/*.md` (19 files) | `.claude/commands/trellis/*.md` | Adds/replaces upstream commands |
| `overlays/hiskens/templates/claude/hooks/*.py` (9 files) | `.claude/hooks/*.py` | Adds/replaces upstream hooks |
| `overlays/hiskens/templates/claude/settings.overlay.json` | **MERGED into** `.claude/settings.json` | Not copied |
| `overlays/hiskens/templates/claude/skills/**` (3 dirs) | `.claude/skills/**` | Hiskens-only skills |
| `overlays/hiskens/templates/codex/agents/*.toml` (6 files) | `.codex/agents/*.toml` | Replaces upstream Codex agents |
| `overlays/hiskens/templates/codex/hooks.json` | `.codex/hooks.json` | Replaces upstream |
| `overlays/hiskens/templates/codex/hooks/*.py` (2 files) | `.codex/hooks/*.py` | Replaces upstream |
| `overlays/hiskens/templates/codex/scripts/load-trellis-context.py` | `.codex/scripts/load-trellis-context.py` | Hiskens-only |
| `overlays/hiskens/templates/agents/skills/**` (10 skill dirs) | `.agents/skills/**` | Hiskens-only shared skills |
| `overlays/hiskens/templates/trellis/config.yaml` | `.trellis/config.yaml` | Replaces upstream |
| `overlays/hiskens/templates/trellis/config/agent-models.example.json` | `.trellis/config/agent-models.example.json` | Hiskens-only |
| `overlays/hiskens/templates/trellis/scripts/**` (~40 files) | `.trellis/scripts/**` | Replaces/augments upstream scripts |
| `overlays/hiskens/templates/trellis/spec/**` (~35 files) | `.trellis/spec/**` | Adds Hiskens spec guides/matlab/python |
| `overlays/hiskens/templates/trellis/templates/prd-template.md` | `.trellis/templates/prd-template.md` | Hiskens-only |
| `overlays/hiskens/templates/trellis/worktree.yaml` | **NOT INSTALLED** (excluded) | Manual activation required |

The mapping is 1:1 for every non-excluded, non-settings-overlay file: each
file in `overlays/hiskens/templates/<overlayDir>/...` installs to
`<outputDir>/...` with the same sub-path. The only two files that break this
strict copy semantics are `settings.overlay.json` (merged) and the two
excluded files.

---

## Caveats / Not Found

- The "31 overlay extra root files" figure from the task prompt could not be
  verified from a direct list in the codebase. The overlay installs files
  across multiple directories (`.claude/`, `.codex/`, `.agents/`, `.trellis/`),
  not a root-level flat set of 31 files. The figure may refer to a prior
  analysis artifact.
- `overlay.yaml`'s `settings_merge` key (`{ claude: "templates/claude/settings.overlay.json" }`)
  is parsed and stored in `OverlayConfig` but is NOT used at runtime to drive
  the merge. The merge is triggered purely by the `settings.overlay.json`
  filename convention in `applyOverlayToProject` / `applyOverlayToTemplateMap`.
  The YAML field appears to be documentary/metadata only.
- `readOverlayFiles` skips `__pycache__` directories, so compiled `.pyc` files
  (present in the overlay source tree) are never installed.
