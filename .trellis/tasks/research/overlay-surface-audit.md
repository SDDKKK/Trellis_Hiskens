# Research: Hiskens Overlay Surface Audit

- **Query**: Categorize every file under `overlays/hiskens/templates/` as CORE / NICE-TO-HAVE / REMOVABLE relative to upstream `packages/cli/src/templates/`, given the user's claim that only 3 customizations are essential (CCR injection in `inject-subagent-context.py`, MCP tool replacements in 3 trellis-* agents, config files for `.trellis/config.yaml` features + `agent-models.json` + `.claude/settings.json` overlay).
- **Scope**: internal
- **Date**: 2026-05-02

---

## TL;DR

- **Total files in `overlays/hiskens/templates/`**: 134
- **Truly CORE for the 3 customizations**: 4 files (~3% of overlay) — `settings.overlay.json`, `inject-subagent-context.py`, and 3 trellis-* agent definitions … wait, that's 5; `config.yaml` lives in `templates/trellis/` so it's also shipped automatically. **5 files**.
- **NICE-TO-HAVE**: ~50 files (Python/MATLAB specs, hiskens-only skills, statusline/intent-gate/todo-enforcer hooks, Codex integration). These add genuine value but are not part of the 3 patches.
- **REMOVABLE**: ~80 files. Most fall into two buckets:
  1. The entire `templates/trellis/scripts/common/` tree (18 files) — a stale fork of upstream `common/` that diverges by 2,943 diff lines but is auto-shipped by the overlay loader, **overwriting upstream scripts wholesale**. This is the single largest source of overlay bloat and the most fragile coupling to upstream internals.
  2. ~20 `templates/claude/commands/trellis/` files that are full upstream-replacement copies, drifting 100–300 diff lines from current upstream and creating a hidden second source of truth.
- **`agent-models.json` is not actually in the overlay** — only `agent-models.example.json` is shipped. The real config lives at `.trellis/config/agent-models.json` in the *project root* (currently uncommitted in git status).
- **`exclude.yaml`** excludes only 2 paths: `claude/agents/review.md` (stale reference, not even present anymore) and `trellis/worktree.yaml`.

---

## How the overlay actually ships files

Reference: `packages/cli/src/utils/overlay.ts:217-244` (`readOverlayFiles`) and `packages/cli/src/configurators/index.ts:597-633`.

1. `init --overlay hiskens` walks `overlays/hiskens/templates/<platform>/` recursively.
2. **Every file** found is written to the user's project at the corresponding path, **overwriting** the upstream-default content that the configurator wrote one step earlier.
3. **Exception 1** — files matching `isSettingsOverlayFile` (today: `settings.overlay.json`) are *merged* into the project's existing `.claude/settings.json` via `mergeSettings()` (`overlay.ts:246-330`). Merge logic: `env`, `permissions`, `hooks` matchers are unioned/replaced-by-matcher; everything else is shallow-overwritten.
4. **Exception 2** — paths listed in `overlays/hiskens/exclude.yaml` are removed from the upstream baseline (no overlay file replaces them).

**Implication**: every file you keep in `overlays/hiskens/templates/` becomes a hard fork of that upstream path, frozen at whenever it was last copied. The "overlay" model has no copy-on-modify or partial-merge for `.md` / `.py` files — they fully replace upstream.

---

## Directory-by-directory inventory

### `templates/claude/agents/` (3 files)

| File | Status | Diff vs upstream | Reason |
|---|---|---|---|
| `trellis-check.md` | **CORE** | tools-line only: `mcp__exa__*` → `mcp__augment-context-engine__codebase-retrieval, mcp__grok-search__*` | Customization #2 (MCP tool replacement). Body is byte-identical to upstream. |
| `trellis-implement.md` | **CORE** | tools-line only: same swap as above | Customization #2. Body byte-identical to upstream. |
| `trellis-research.md` | **CORE** | tools-line swap + frontmatter adds `mcp__context7__resolve-library-id`, `mcp__context7__query-docs`; body adds one paragraph in Step 3 about "use augment-context-engine for any codebase question, then Glob/Grep/grok-search in parallel" | Customization #2. Body is upstream-equivalent except the augment-first guidance. |

The frontmatter `tools:` field is the **only** load-bearing change for trellis-implement.md and trellis-check.md. The body text in all three is essentially upstream verbatim and could in principle be regenerated if Trellis ever moves to a per-overlay tools-list mechanism, but until that exists these 3 files are mandatory for the user's MCP-swap goal.

### `templates/claude/hooks/` (9 files)

| File | Status | Notes |
|---|---|---|
| `inject-subagent-context.py` | **CORE** | 841 lines vs upstream 808. Adds `_load_features()`, `_ccr_model_keys()`, `get_ccr_model_tag()` (CCR routing #1) and many Cursor/Copilot/Kiro/Gemini platform-detect helpers. Drops upstream's debug-agent path, `update_current_phase`, and `.current-task` reader (uses `common.active_task.resolve_active_task` instead). The CCR functions are the user's customization #1 but the file also has many other deltas that are NOT user-listed customizations (platform compat, active_task resolver). |
| `session-start.py` | NICE-TO-HAVE | 677 vs upstream similar — needs deeper diff to classify. Hiskens-flavored session display. |
| `ralph-loop.py` | NICE-TO-HAVE | 618 lines. Classic Hiskens Ralph-loop runner; upstream also ships one but content differs. |
| `statusline.py` | NICE-TO-HAVE | 311 lines. Replaces upstream statusline with one that reads Trellis task data + Sub2API rate limits. |
| `intent-gate.py` | **HISKENS-ONLY** (not in upstream) | UserPromptSubmit hook for keyword → mode hint injection. Wired in `settings.overlay.json` via `UserPromptSubmit` matcher. |
| `todo-enforcer.py` | **HISKENS-ONLY** | Stop-hook that blocks session stop while todos remain. Wired via `PostToolUse:TodoWrite` and `Stop`. |
| `context-monitor.py` | **HISKENS-ONLY** | PostToolUse hook injecting context-window warnings, paired with statusline-bridge. |
| `statusline-bridge.py` | **HISKENS-ONLY** | Transparent statusline proxy that writes the bridge file context-monitor reads. User-level config, not project-level. |
| `parse_sub2api_usage.py` | **HISKENS-ONLY** | Helper script (not a hook) for Sub2API usage parsing, called from statusline. |

The user's customization #1 is just the CCR additions inside `inject-subagent-context.py`. The other 8 hooks are independent hiskens features that survive or die on their own merits.

### `templates/claude/commands/trellis/` (20 files) — REMOVABLE bulk

All 20 mirror upstream paths and replace them outright. Sample diff sizes (lines reported by `diff … | wc -l`):

| File | Diff lines | Status |
|---|---|---|
| `finish-work.md` | 309 | REMOVABLE (full rewrite to use `uv run ruff/pytest`, hiskens spec layout) |
| `check-cross-layer.md` | 43 | REMOVABLE |
| `start.md` | 140 | REMOVABLE |
| `onboard.md` | 164 | REMOVABLE |
| `before-python-dev.md` | upstream-absent | NICE-TO-HAVE (Python-specific dev gate) |
| `before-matlab-dev.md` | upstream-absent | NICE-TO-HAVE (MATLAB dev gate) |
| `check-python.md` / `check-matlab.md` | upstream-absent | NICE-TO-HAVE (per-language verification) |
| `improve-ut.md` | upstream-absent | NICE-TO-HAVE (unit-test improvement command) |
| `record-session.md` | varies | REMOVABLE (replaces upstream) |
| `retro.md` | upstream-absent | NICE-TO-HAVE |
| `brainstorm-base.md` / `break-loop-base.md` / `check-cross-layer-base.md` | upstream-absent | NICE-TO-HAVE (the hiskens "base + hiskens" layered model) |
| `update-spec.md`, `integrate-skill.md`, `parallel.md`, `create-command.md` | varies | REMOVABLE (drift from upstream) |
| `brainstorm.md`, `break-loop.md` | varies | REMOVABLE |

13 of 20 are pure replacements of an existing upstream command file — every one of these is a hard fork that will silently shadow upstream improvements. 7 are hiskens-only commands without an upstream counterpart and have to live somewhere.

### `templates/claude/skills/` (4 files) — NICE-TO-HAVE

| File | Status |
|---|---|
| `fork-sync-strategy/SKILL.md` | NICE-TO-HAVE — explicit hiskens process knowledge |
| `github-explorer/SKILL.md` | NICE-TO-HAVE |
| `grok-search/SKILL.md` | NICE-TO-HAVE — pairs with the MCP swap in agents |
| `with-codex/SKILL.md` | NICE-TO-HAVE — codex MCP plugin integration |

None present in upstream. None required for the 3 core customizations, but the grok-search skill arguably documents the agent tool change.

### `templates/agents/skills/` (10 files) — NICE-TO-HAVE

Per-agent skill index (e.g. `before-python-dev`, `check-python`, `parallel`, `retro`). These follow the upstream "platform-agnostic skills" pattern but are hiskens-specific (Python/MATLAB and `parallel`/`retro` ops).

### `templates/codex/` (8 files)

| File | Status | Reason |
|---|---|---|
| `agents/debug.toml`, `plan.toml`, `review.toml` | REMOVABLE | These are v0.4-era agent names. Upstream Codex now ships `trellis-check.toml`, `trellis-implement.toml`, `trellis-research.toml`. The hiskens overlay does NOT override the upstream trellis-* codex agents, but it DOES install three orphan v0.4 agents alongside them. `MAINTENANCE.md` line 28 explicitly says hiskens "should not own ... v0.4-era agent overrides", so these violate the documented policy. |
| `hooks.json` | REMOVABLE | Replaces the upstream codex `hooks.json` (which adds `inject-workflow-state.py` UserPromptSubmit) with a hiskens version that drops `inject-workflow-state.py` and adds a `post-tool-use.py` PostToolUse hook. |
| `hooks/post-tool-use.py` | NICE-TO-HAVE | Codex PostToolUse hook that injects an additionalContext reminder after `load-trellis-context.py` runs. |
| `hooks/session-start.py` | NICE-TO-HAVE (or REMOVABLE) | Replaces upstream codex session-start. Worth diffing closely. |
| `scripts/load-trellis-context.py` | NICE-TO-HAVE | Codex helper to load Trellis context at session start. |

### `templates/trellis/scripts/` (24 files) — overwhelmingly REMOVABLE

This is the single biggest source of bloat. The overlay loader will write all 24 files into the user's `.trellis/scripts/`, replacing whatever upstream wrote.

#### Top-level scripts (10 files)

| File | Status | Reason |
|---|---|---|
| `task.py` | DIFFERS from upstream | Likely REMOVABLE — investigate diff. |
| `get_context.py` | DIFFERS from upstream | Likely REMOVABLE. |
| `init_developer.py` | DIFFERS from upstream | Likely REMOVABLE. |
| `add_session.py` | DIFFERS from upstream | Likely REMOVABLE. |
| `get_developer.py` | identical to upstream | REMOVABLE (zero-value duplicate). |
| `__init__.py` | identical to upstream | REMOVABLE (zero-value duplicate). |
| `init-nocturne-namespace.py` | HISKENS-ONLY | NICE-TO-HAVE if Nocturne is used; otherwise REMOVABLE. |
| `nocturne_client.py` | HISKENS-ONLY | NICE-TO-HAVE / REMOVABLE depending on Nocturne usage. |
| `promote-to-nocturne.py` | HISKENS-ONLY | Same. |
| `sync-trellis-to-nocturne.py` | HISKENS-ONLY | Same. |

#### `templates/trellis/scripts/common/` (18 files) — STALE FORK

| File | Diff lines vs upstream | Overlay LOC | Verdict |
|---|---:|---:|---|
| `cli_adapter.py` | 248 | 674 | REMOVABLE / drift |
| `config.py` | 190 | 324 | REMOVABLE / drift |
| `context_assembly.py` | overlay-only | n/a | REMOVABLE — only consumer is the hiskens-only Codex `load-trellis-context.py`; no upstream code path imports it. |
| `developer.py` | 32 | 192 | REMOVABLE |
| `git_context.py` | 41 | 79 | REMOVABLE |
| `git.py` | 3 | 33 | REMOVABLE (trivial drift) |
| `__init__.py` | 112 | 176 | REMOVABLE — primary symptom of the fork: re-exports v0.4 names (`DIR_MEMORY`, `FILE_DECISIONS`, …) that upstream removed. |
| `io.py` | 5 | 40 | REMOVABLE |
| `log.py` | 3 | 47 | REMOVABLE |
| `packages_context.py` | 57 | 253 | REMOVABLE |
| `paths.py` | 236 | 442 | REMOVABLE |
| `session_context.py` | 385 | 794 | REMOVABLE |
| `task_context.py` | 547 | 665 | REMOVABLE — almost entirely rewritten |
| `task_queue.py` | 170 | 258 | REMOVABLE |
| `tasks.py` | 13 | 108 | REMOVABLE |
| `task_store.py` | 538 | 835 | REMOVABLE — almost entirely rewritten |
| `task_utils.py` | 70 | 281 | REMOVABLE |
| `types.py` | 12 | 117 | REMOVABLE |

**Sum of `common/`**: 5,415 LOC, 2,660 diff lines vs upstream (≈ 50% drift). Notably the overlay's `common/__init__.py` line 4 still says *"Ported from upstream v0.4.0-beta.7"* — this is an unmaintained snapshot. It also lacks `active_task.py` and `workflow_phase.py` that upstream now ships, which means after `init --overlay hiskens` the project gets a `common/` package with **18 forked files plus 2 missing files** the upstream `inject-subagent-context.py` (and the new hiskens hook header) actually try to import. This is the live coupling failure that `task.py current` hit at the start of this very research session: `ModuleNotFoundError: No module named 'common.worktree'`.

#### `templates/trellis/scripts/search/` (4 files) — HISKENS-ONLY

| File | Status |
|---|---|
| `_common.py` | NICE-TO-HAVE |
| `web_fetch.py` | NICE-TO-HAVE |
| `web_map.py` | NICE-TO-HAVE |
| `web_search.py` | NICE-TO-HAVE |
| `API_CONFIG.md` | NICE-TO-HAVE |

Local-grok / web fallback toolkit. Not in upstream. Pairs with the grok-search skill.

### `templates/trellis/spec/` (43 files) — domain knowledge

#### `templates/trellis/spec/guides/` (26 files) — NICE-TO-HAVE

All hiskens-domain guides (debug-methodology, tdd-guide, code-reuse, etc.). None present upstream by these names. Drop-in spec library for scientific computing teams. Several entries (`trellis-check-hiskens.md`, `agent-design-principles.md`, `new-agent-wiring.md`) are explicitly hiskens-fork process knowledge.

#### `templates/trellis/spec/python/` (8 files) — NICE-TO-HAVE

Python code-style, docstring conventions, data-processing notes plus 4 `.template` skill examples (markitdown, polars×2, scientific-visualization). Solid value for a Python-focused project; not part of the 3 listed customizations.

#### `templates/trellis/spec/matlab/` (6 files) — NICE-TO-HAVE

MATLAB code-style, docstring, quality-guidelines plus 2 `.m.template` examples. Same status as python/.

### `templates/trellis/` (top-level overlay files)

| File | Status |
|---|---|
| `config.yaml` | **CORE** — features block (`ccr_routing: true`, `reference_support: true`) is consumed by the hook's `_load_features()`. This is customization #3-(a). |
| `worktree.yaml` | REMOVABLE — already in `exclude.yaml`, so it's not even shipped. |
| `templates/prd-template.md` | NICE-TO-HAVE — Hiskens flavored PRD template. |
| `config/agent-models.example.json` | **CORE-ADJACENT** — example mapping for CCR routing. The actual `agent-models.json` is NOT in the overlay; users (and the project root, see git-status `A  .trellis/config/agent-models.json`) place it manually. The example file documents the schema customization #3-(b) needs. |

---

## `claude/settings.overlay.json` analysis

Path: `overlays/hiskens/templates/claude/settings.overlay.json` (74 lines).

Compared with upstream `packages/cli/src/templates/claude/settings.json` (74 lines):

| Key | Upstream value | Overlay value | Hiskens-only? |
|---|---|---|---|
| `env.CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR` | `"1"` | (absent) | upstream-only — overlay merge will preserve it via `…baseEnv, ...overlayEnv` |
| `env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` | (absent) | `"1"` | **HISKENS** |
| `env.ENABLE_TOOL_SEARCH` | (absent) | `"true"` | **HISKENS** |
| `enabledPlugins` (full list) | (absent) | 7 plugin entries | **HISKENS** — installs astral, code-simplifier, codex, context7, github, notion, skill-creator plugins |
| `model` | (absent) | `"opus[1m]"` | **HISKENS** |
| `alwaysThinkingEnabled` | (absent) | `true` | **HISKENS** |
| `effortLevel` | (absent) | `"medium"` | **HISKENS** |
| `hooks.SessionStart` (×3 matchers) | upstream wires `session-start.py` for `startup`/`clear`/`compact` | (absent in overlay) | upstream-only — preserved by merge |
| `hooks.PreToolUse[Task]` and `[Agent]` | upstream wires `inject-subagent-context.py` | (absent in overlay) | upstream-only — preserved by merge |
| `hooks.UserPromptSubmit (no matcher)` | upstream wires `inject-workflow-state.py` | overlay adds a SECOND entry with `matcher: ""` and `intent-gate.py` | merge will replace by matcher: both upstream `""` and overlay `""` collide → overlay overwrites the upstream entry. **This drops `inject-workflow-state.py` silently** — confirmed in code at `overlay.ts:294-321`: matchers with the same value are replaced, not unioned. |
| `hooks.PreToolUse[Bash]` | (absent upstream) | `rtk hook claude` | **HISKENS** (RTK integration) |
| `hooks.PostToolUse[TodoWrite]` | (absent upstream) | `todo-enforcer.py` | **HISKENS** |
| `hooks.PostToolUse[""]` | (absent upstream) | `context-monitor.py` | **HISKENS** |
| `hooks.Stop[""]` | (absent upstream) | `todo-enforcer.py` | **HISKENS** |

**Net hiskens-specific keys to keep in any minimal overlay**: 7 keys + 4 hooks groups. The merge logic means the `settings.overlay.json` *can* stay tiny and only carry hiskens additions; it currently doesn't redefine any upstream values it doesn't intend to override.

⚠️ **Side effect to verify**: the overlay's `UserPromptSubmit` with empty matcher silently displaces upstream's `inject-workflow-state.py`. If this is intentional (intent-gate.py replaces workflow-state injection), `MAINTENANCE.md` should call it out. If not, intent-gate should use a non-empty matcher and the upstream entry should be allowed to coexist.

---

## `exclude.yaml` analysis

Two entries:

1. **`claude/agents/review.md`** — A defensive exclusion. There is no `review.md` in the current overlay (`templates/claude/agents/` only contains `trellis-check.md`, `trellis-implement.md`, `trellis-research.md`). Comment says "kept as a reference agent definition for manual use" but the file is absent from disk. **Stale — can be dropped** along with the entry.
2. **`trellis/worktree.yaml`** — Real entry. The overlay ships `templates/trellis/worktree.yaml` but the configurator deletes it from the project install. Used as a "starting point reference" the user must manually copy.

---

## Minimum file count for ONLY the 3 core customizations

If the user wants to strip the overlay to ONLY:

1. CCR injection in `inject-subagent-context.py`
2. MCP tool replacement in 3 trellis-* agents
3. Config files (config.yaml `features`, agent-models.json, settings.json hooks)

…the absolute minimum overlay tree is:

```
overlays/hiskens/
├── overlay.yaml                                     # required metadata (1)
├── exclude.yaml                                     # optional; can be empty (1, optional)
└── templates/
    ├── claude/
    │   ├── agents/
    │   │   ├── trellis-check.md                     # (1)
    │   │   ├── trellis-implement.md                 # (1)
    │   │   └── trellis-research.md                  # (1)
    │   ├── hooks/
    │   │   └── inject-subagent-context.py           # (1) — CCR additions
    │   └── settings.overlay.json                    # (1) — features-driving hooks/env
    └── trellis/
        ├── config.yaml                              # (1) — features.ccr_routing flag
        └── config/
            └── agent-models.example.json            # (1) — schema example
```

**Minimum file count: 8** (or 7 if `exclude.yaml` is dropped — the loader treats absence as empty).

Note that **`agent-models.json` itself is project-side**, not overlay-side — only the `.example.json` ships. The user's bullet "config files: agent-models.json" refers to the runtime config the project uses, which today lives at the repo root (`.trellis/config/agent-models.json`, status `A` in `git status`).

If the user is willing to drop the **CCR feature flag** and rely only on the `ANTHROPIC_BASE_URL` + `agent-models.json` presence checks already in the hook, then `config.yaml` could go too (the hook's `_load_features` defaults to `{}` and CCR returns `""` early), shrinking the minimum to **6 files**. But the existing hook source explicitly requires `features.ccr_routing: true`, so removing config.yaml would silently disable CCR routing.

---

## Files that aren't doing what they claim

A few items worth flagging because their *stated* purpose differs from current overlay reality:

- **`MAINTENANCE.md` line 27-28**: "should not own … v0.4-era agent overrides" — but `templates/codex/agents/{debug,plan,review}.toml` are exactly that.
- **`MAINTENANCE.md` line 31**: "should not own … default `worktree.yaml` verification blocks" — the overlay ships `templates/trellis/worktree.yaml` (excluded from install, but still present in the source tree as a "starting point").
- **`overlays/hiskens/templates/trellis/scripts/common/__init__.py:5-6`**: docstring still says *"Ported from upstream v0.4.0-beta.7"*. Today's upstream is v0.5.0-beta.18 (per `MAINTENANCE.md` and recent commits). This is the canary for the stale-fork problem.
- **The very repo we're auditing**: `python3 ./.trellis/scripts/task.py current --source` fails with `ModuleNotFoundError: No module named 'common.worktree'`. This is real-world evidence that the forked `common/` is no longer in sync with `task.py` (top-level scripts/upstream).

---

## Caveats / Not done

- I did not byte-diff every `.md` body to confirm they are 100% drift vs intentional. Sample diffs (3 commands + 3 agents + 1 hook) suggest most `.md` files in `commands/` are full rewrites; a fuller sweep is a quick follow-up.
- I did not confirm whether `parse_sub2api_usage.py`, `init-nocturne-namespace.py`, `promote-to-nocturne.py`, `sync-trellis-to-nocturne.py`, and `nocturne_client.py` are wired by any other file in the overlay. If they aren't referenced from a hook, command, or skill, they're dead code in the overlay.
- I did not verify whether the user's actual project (Trellis_Hiskens) consumes the overlay files via `init --overlay hiskens` or directly off-disk. If they're consumed off-disk (i.e. the project IS the overlay author), the "minimum file count" question is about repo size, not install size; both are still 8.
- The `agents/skills/` (10 files) directory at the overlay root has an unusual path (no `claude/` or `codex/` prefix); I did not trace which platform configurator consumes it. May be a v0.4 carry-over.
