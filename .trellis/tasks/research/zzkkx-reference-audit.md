# Research: ZZ_KKX Reference Audit (Desired End-State for `trellis init --overlay hiskens`)

- **Query**: How is `/mnt/e/Github/repo/ZZ_KKX/` customized vs. upstream Trellis + Hiskens overlay defaults?
- **Scope**: internal (filesystem audit, byte-level diff)
- **Date**: 2026-05-02

## TL;DR

ZZ_KKX is a **hybrid**: it has the Hiskens overlay's three claude agents byte-identical, but its hooks (`inject-subagent-context.py`, `session-start.py`) and `config.yaml` are NOT byte-identical to the current overlay — they are the upstream rc.1 base **with** the Hiskens CCR additions hand-applied/cherry-picked. The fork's overlay still ships at beta.18 base, while ZZ_KKX session-start/inject-subagent-context already include rc.1 features.

The MINIMAL Hiskens-overlay surface visible in ZZ_KKX (vs upstream defaults) is:

1. `.trellis/config.yaml` — adds `features.ccr_routing: true`
2. `.trellis/config/agent-models.json` — agent → CCR provider/model mapping
3. `.claude/agents/{trellis-research,trellis-implement,trellis-check}.md` — MCP tool list rewritten (`mcp__exa__*` → `mcp__augment-context-engine__*` + `mcp__grok-search__*`; research adds `mcp__context7__*` and an "augment first" instruction)
4. `.claude/hooks/inject-subagent-context.py` — adds 3 CCR functions (`_load_features`, `_ccr_model_keys`, `get_ccr_model_tag`) and prepends a `<CCR-SUBAGENT-MODEL>` tag to the agent prompt when guardrails pass
5. `.claude/hooks/session-start.py` — adds `FIRST_REPLY_NOTICE` (Chinese acknowledgement banner)
6. `.codex/agents/{trellis-implement,trellis-check}.toml` — pre-pend a "Required: Load Trellis Context First" block
   (Codex `trellis-research.toml` is upstream-identical)

ZZ_KKX does **not** have the rest of the Hiskens overlay surface (statusline, intent-gate, todo-enforcer, ralph-loop, context-monitor, codex post-tool-use, RTK hook, the python/matlab spec packs, the Nocturne scripts). So either the user pre-selected a subset, or the install used an earlier overlay snapshot that hadn't grown those yet.

---

## Findings

### Files Found (full ZZ_KKX inventory)

#### `.trellis/`

| File | Source / Verdict |
|---|---|
| `.trellis/.developer` | runtime (gitignored: `name=Hiskens`, init 2026-05-01) |
| `.trellis/.gitignore` | upstream default (matches `templates/trellis/gitignore.txt`-style content) |
| `.trellis/.template-hashes.json` | runtime hash manifest from `trellis init`/`trellis update` |
| `.trellis/.version` | `0.5.0-rc.1` — **upstream is newer than the fork (`0.5.0-beta.18`)** |
| `.trellis/config.yaml` | **HISKENS OVERLAY** — adds `features.ccr_routing: true` block (rest of file matches upstream defaults) |
| `.trellis/config/agent-models.json` | **HISKENS OVERLAY** — CCR routing map (`trellis-implement/check/research → CC-MAX,claude-opus-4-7`) |
| `.trellis/workflow.md` | rc.1 upstream — fork still on beta.18 baseline |
| `.trellis/scripts/*.py` (top-level) | all 5 match upstream beta.18 byte-identically |
| `.trellis/scripts/common/*.py` (19 files) | 17 match upstream; **`task_store.py` and `workflow_phase.py` differ (rc.1 features)** |
| `.trellis/scripts/hooks/linear_sync.py` | upstream default |
| `.trellis/spec/backend/*.md` (6 files) | seeded from upstream `markdown/spec/backend/*` template, then **filled with project-specific content** by user (correctly project-specific) |
| `.trellis/spec/guides/*.md` (3 files) | byte-identical to upstream `markdown/spec/guides/*` template (unmodified) |
| `.trellis/workspace/index.md` | upstream default (`workspace-index.md` template) |
| `.trellis/workspace/Hiskens/{index.md,journal-1.md}` | user runtime data |
| `.trellis/workspace/research/repo-business-logic-and-data-flow.md` | user research output (398 lines, project-specific business logic notes) |
| `.trellis/tasks/archive/2026-05/00-bootstrap-guidelines/{prd.md,task.json}` | first-task auto-created by `trellis init` for backend project type, then archived |

Notable absences:
- **No `python/`, `matlab/` spec dirs** — the rich python/matlab spec packs that ship in `overlays/hiskens/templates/trellis/spec/{python,matlab}/` are NOT present in ZZ_KKX.
- **No `cli/`, `docs-site/` spec dirs** — only `backend/` and `guides/` exist.

#### `.claude/`

| File | Source / Verdict |
|---|---|
| `.claude/settings.json` | minimal — only the 4 standard hook entries (SessionStart, PreToolUse Task/Agent, UserPromptSubmit), `model: opus[1m]`, `alwaysThinkingEnabled: true`, `CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR=1`, `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`. **Does NOT include the Hiskens `settings.overlay.json` content** (no `intent-gate`, `todo-enforcer`, `context-monitor`, `rtk hook`, `enabledPlugins`). |
| `.claude/agents/trellis-research.md` | **byte-identical to `overlays/hiskens/templates/claude/agents/trellis-research.md`** |
| `.claude/agents/trellis-implement.md` | **byte-identical to overlay** |
| `.claude/agents/trellis-check.md` | **byte-identical to overlay** |
| `.claude/hooks/inject-subagent-context.py` | **HISKENS OVERLAY (rc.1-rebased variant)** — 825 lines, contains all 3 CCR functions; differs from current overlay (which is 841 lines, beta.18-based) |
| `.claude/hooks/session-start.py` | **HISKENS OVERLAY (rc.1-rebased variant)** — 717 lines, contains `FIRST_REPLY_NOTICE` and `_has_curated_jsonl_entry`; differs from current overlay (677 lines, beta.18) |
| `.claude/hooks/inject-workflow-state.py` | upstream rc.1 (matches `shared-hooks/inject-workflow-state.py` fairly closely with rc.1 docstring updates) |
| `.claude/skills/trellis-{before-dev,brainstorm,break-loop,check,meta,update-spec}/SKILL.md` | upstream defaults |
| `.claude/skills/trellis-meta/references/{customize-local,local-architecture,platform-files}/*.md` (~22 files) | upstream defaults |
| `.claude/commands/trellis/{continue,finish-work}.md` | upstream defaults |

#### `.codex/`

| File | Source / Verdict |
|---|---|
| `.codex/config.toml` | byte-identical to upstream `templates/codex/config.toml` |
| `.codex/hooks.json` | upstream `templates/codex/hooks.json` with `{{PYTHON_CMD}}` resolved to `python3` (standard `trellis init` rendering, NOT overlay) |
| `.codex/agents/trellis-research.toml` | byte-identical to upstream |
| `.codex/agents/trellis-implement.toml` | **HISKENS-STYLE** — adds 16-line "Required: Load Trellis Context First" block at the top of `developer_instructions` (rest matches upstream) |
| `.codex/agents/trellis-check.toml` | **HISKENS-STYLE** — same pre-pended context-load block |
| `.codex/hooks/session-start.py` | rc.1 upstream (adds `_strip_breadcrumb_tag_blocks` + heading change to "Customizing Trellis (for forks)"). **NOT** in overlay templates — fork's `overlays/hiskens/templates/codex/` only has `hooks.json`. |
| `.codex/hooks/inject-workflow-state.py` | rc.1 upstream (shared between platforms) |

#### `.agents/skills/`

This is the Codex-style portable skills dir. Contents:
- `before-{matlab,python}-dev`, `brainstorm`, `check-{matlab,python}`, `finish-work`, `improve-ut`, `parallel`, `record-session`, `retro` — upstream defaults (would ship as part of skills package)
- `trellis-{before-dev,brainstorm,break-loop,check,continue,finish-work,meta,update-spec}/SKILL.md` — upstream defaults
- The `trellis-meta/references/` tree mirrors `.claude/skills/trellis-meta/references/`

The `.template-hashes.json` registers all 19 of these `.agents/skills/...` paths, indicating they were all installed by `trellis init`.

#### Repo root

| File | Source / Verdict |
|---|---|
| `AGENTS.md` | byte-identical to upstream `templates/markdown/agents.md` (TRELLIS:START/END block content unmodified) |
| **No `CLAUDE.md`** | none at repo root (the one I see is the user's global at `/home/hcx/.claude/CLAUDE.md`, not in the project) |
| `.gitignore`, `pyproject.toml`, `README.md`, `schema.yml`, `uv.lock`, `.python-version`, `FMEA_README.md`, `ZZ_KKX.zip`, `src/`, `scripts/`, `docs/`, `output/`, etc. | project-specific (NOT Trellis territory) |

### Code Patterns

#### CCR plumbing in `inject-subagent-context.py` (Hiskens overlay surface)

Three functions added to the upstream hook:

- `_load_features(repo_root)` (line 133) — minimal YAML parser scanning the `features:` block in `.trellis/config.yaml`
- `_ccr_model_keys(subagent_type)` (line 169) — alias map so legacy short names (`implement`/`check`/`research`) resolve to the canonical `trellis-*` keys and vice-versa
- `get_ccr_model_tag(repo_root, subagent_type)` (line 181) — returns either `<CCR-SUBAGENT-MODEL>provider,model</CCR-SUBAGENT-MODEL>\n` or empty string. Triple guardrail:
  1. `features.ccr_routing == true` in `config.yaml`
  2. `ANTHROPIC_BASE_URL` contains `127.0.0.1` or `localhost`
  3. `.trellis/config/agent-models.json` exists and parses to a dict with the agent key

The result is prepended to the new prompt at line 799-800:

```python
if ccr_tag:
    new_prompt = ccr_tag + new_prompt
```

This matches the contract documented in `/home/hcx/github/Trellis_Hiskens/overlays/hiskens/templates/claude/hooks/inject-subagent-context.py` exactly (functions are byte-equivalent in body; only docstring wording differs because ZZ_KKX trims a few lines of comment).

#### `FIRST_REPLY_NOTICE` in `session-start.py` (Hiskens overlay surface)

Lines 21-25 of `/mnt/e/Github/repo/ZZ_KKX/.claude/hooks/session-start.py`:

```python
FIRST_REPLY_NOTICE = """<first-reply-notice>
On the first visible assistant reply in this session, begin with exactly one short Chinese sentence:
Trellis SessionStart 已注入：workflow、当前任务状态、开发者身份、git 状态、active tasks、spec 索引已加载。
Then continue directly with the user's request. This notice is one-shot: do not repeat it after the first assistant reply in the same session.
</first-reply-notice>"""
```

Written into output at line 615: `output.write(FIRST_REPLY_NOTICE)`. This is the only Chinese-language injection from the Hiskens overlay; the upstream session-start.py has neither the constant nor the write call.

#### Agent MCP tool delta (Hiskens overlay surface)

| Agent | Upstream tools list | ZZ_KKX (= overlay) tools list |
|---|---|---|
| `trellis-research` | `Read, Write, Glob, Grep, Bash, mcp__exa__web_search_exa, mcp__exa__get_code_context_exa, Skill, mcp__chrome-devtools__*` | `Read, Write, Glob, Grep, Bash, Skill, mcp__augment-context-engine__codebase-retrieval, mcp__context7__resolve-library-id, mcp__context7__query-docs, mcp__grok-search__*` |
| `trellis-implement` | `..., mcp__exa__web_search_exa, mcp__exa__get_code_context_exa` | `..., mcp__augment-context-engine__codebase-retrieval, mcp__grok-search__*` |
| `trellis-check` | `..., mcp__exa__web_search_exa, mcp__exa__get_code_context_exa` | `..., mcp__augment-context-engine__codebase-retrieval, mcp__grok-search__*` |

`trellis-research.md` also adds two instruction lines (46-47):

> Befor exact searches use mcp__augment-context-engine__codebase-retrieval for ANY question involving codebase, files, structure, dependencies, search, or context,
> then run independent searches in parallel (Glob + Grep + mcp__grok-search__*) for efficiency.

#### Codex `trellis-implement`/`trellis-check` context-load preamble

Both `.codex/agents/trellis-{implement,check}.toml` insert a 16-line block before `You are the Trellis ... agent.`:

```
## Required: Load Trellis Context First

This platform does NOT auto-inject task context via hook. Before doing anything else, you MUST load context yourself:

1. Run `python3 ./.trellis/scripts/task.py current --source` ...
2. Read the task's `prd.md` (requirements) and `info.md` if it exists ...
3. Read `<task-path>/{implement,check}.jsonl` — JSONL list of dev spec files ...
4. For each entry in the JSONL, Read its `file` path ...
   **Skip rows without a `"file"` field** ...

If `{implement,check}.jsonl` has no curated entries (only a seed row, or the file is missing), fall back to: ...
```

`trellis-research.toml` does NOT have this addition (it stays upstream-identical because the research agent's `task.py current --source` step is already in the upstream body).

NOTE: This preamble is NOT in the current `overlays/hiskens/templates/` tree (the overlay does not ship customized codex agents). Either (a) the user installed it manually, (b) an earlier overlay version had it, or (c) it was emitted by a separate `trellis init --overlay hiskens` migration step. **Provenance is uncertain — surface this when scoping the upgrade.**

### Diff Summary: ZZ_KKX vs upstream Trellis_Hiskens fork (`templates/`)

Files that **differ from upstream defaults**:

| File | Type of difference |
|---|---|
| `.trellis/.version` | rc.1 vs beta.18 |
| `.trellis/workflow.md` | rc.1 content (`workflow-state` tag blocks, "Customizing Trellis (for forks)" footer) |
| `.trellis/scripts/common/task_store.py` | rc.1 auto-active-task on `task.py create` |
| `.trellis/scripts/common/workflow_phase.py` | rc.1 strip `[workflow-state:*]` blocks |
| `.trellis/config.yaml` | + `features:` block (overlay) |
| `.trellis/config/agent-models.json` | NEW (overlay) |
| `.trellis/spec/backend/*.md` | filled in by user (project-specific, NOT overlay) |
| `.claude/agents/*.md` | overlay |
| `.claude/hooks/inject-subagent-context.py` | overlay (CCR funcs) on rc.1 base |
| `.claude/hooks/session-start.py` | overlay (FIRST_REPLY_NOTICE) on rc.1 base + `_has_curated_jsonl_entry` |
| `.claude/hooks/inject-workflow-state.py` | rc.1 (matches `shared-hooks/`) |
| `.codex/hooks.json` | upstream with `{{PYTHON_CMD}}` rendered |
| `.codex/hooks/session-start.py` | rc.1 |
| `.codex/agents/trellis-{implement,check}.toml` | overlay-style preamble (provenance unclear — not in current `overlays/hiskens/`) |
| `AGENTS.md` | matches upstream template (no project additions) |

Files that **match upstream byte-for-byte**:

- `.trellis/scripts/*.py` (5 top-level)
- `.trellis/scripts/common/*.py` (17 of 19)
- `.trellis/scripts/hooks/linear_sync.py`
- `.trellis/spec/guides/*.md` (3 files)
- `.trellis/workspace/index.md`
- `.claude/skills/**` (all 7 skills + 22 reference files)
- `.claude/commands/trellis/{continue,finish-work}.md`
- `.codex/config.toml`
- `.codex/agents/trellis-research.toml`
- `.agents/skills/**` (the 19 portable skill dirs)

### Categorization (the answer to "key question")

**Overlay-deliverable** (should come from `--overlay hiskens`):

1. `.trellis/config.yaml` `features.ccr_routing: true` block insertion
2. `.trellis/config/agent-models.json` (with example mapping; user customizes after install)
3. `.claude/agents/trellis-research.md` — replaces upstream
4. `.claude/agents/trellis-implement.md` — replaces upstream
5. `.claude/agents/trellis-check.md` — replaces upstream
6. `.claude/hooks/inject-subagent-context.py` — replaces upstream (with CCR funcs)
7. `.claude/hooks/session-start.py` — replaces upstream (with `FIRST_REPLY_NOTICE`)
8. `.codex/agents/trellis-implement.toml` — pre-pend "Required: Load Trellis Context First" block
9. `.codex/agents/trellis-check.toml` — same preamble (research stays upstream)

**Project-specific** (do NOT include in overlay):

- `.trellis/.developer`, `.trellis/.template-hashes.json`, `.trellis/.version` (all runtime / `trellis init` outputs)
- `.trellis/spec/backend/*.md` content (user's own project guidelines)
- `.trellis/workspace/{Hiskens/, research/}` (user data)
- `.trellis/tasks/archive/...` (user history)
- The repo's source code (`src/`, `scripts/`, `docs/`, etc.)

**Upstream default** (no change needed by overlay):

- `.trellis/scripts/**` (all 24 files — overlay does not need to touch them; rc.1 already has them)
- `.trellis/spec/guides/*.md` (3 unchanged-from-template files)
- `.trellis/workspace/index.md`
- `.trellis/workflow.md` (overlay should rely on whatever upstream `trellis init` renders for the rc.1+ baseline)
- `.claude/skills/**` (7 skills + ~22 references, all unchanged)
- `.claude/commands/trellis/*.md`
- `.claude/hooks/inject-workflow-state.py` (this is `shared-hooks/`, owned by upstream)
- `.codex/{config.toml, hooks.json, hooks/session-start.py, hooks/inject-workflow-state.py, agents/trellis-research.toml}`
- `.agents/skills/**` (19 portable skill dirs)
- `AGENTS.md` (the TRELLIS:START/END block content from upstream template)

### CCR-specific checks (yes/no)

- `features.ccr_routing: true` in `.trellis/config.yaml`? → **YES** (line 71-72)
- `.trellis/config/agent-models.json` exists? → **YES** (3 entries: implement/check/research → `CC-MAX,claude-opus-4-7`)
- Hook has `_load_features`, `_ccr_model_keys`, `get_ccr_model_tag`? → **YES** at lines 133, 169, 181 of `.claude/hooks/inject-subagent-context.py`
- Hook integrates the tag into the prompt? → **YES** at lines 757 and 799-800

### Related Specs

(None — the spec files were ALL filled with project-specific content by the user, and the relevant references for overlay design live under `/home/hcx/github/Trellis_Hiskens/.trellis/spec/cli/` which currently has no entries.)

### External References

None — this is purely an internal filesystem audit.

## Caveats / Not Found

1. **Provenance of `.codex/agents/trellis-{implement,check}.toml` preamble is uncertain.** The 16-line "Required: Load Trellis Context First" block appears in ZZ_KKX but is **not** in the current `overlays/hiskens/templates/codex/` tree. Possible explanations:
   - The overlay shipped this in an earlier version but has since dropped it (worth checking git log on `overlays/hiskens/templates/codex/agents/`).
   - It was migrated through a different mechanism (e.g., a one-shot script, or an older `trellis update` step).
   - The user manually edited it.
   The user should clarify whether this preamble is desired in the new `--overlay hiskens` install. If yes, the overlay needs to grow `templates/codex/agents/trellis-{implement,check}.toml` files.

2. **Version drift between fork and ZZ_KKX.** Trellis_Hiskens fork is at `0.5.0-beta.18`; ZZ_KKX is at `0.5.0-rc.1`. Several files in ZZ_KKX (workflow.md, task_store.py, workflow_phase.py, the two claude hooks' upstream base, codex session-start.py) reflect rc.1 content. The fork must complete the rc.1 sync before its `--overlay hiskens` can produce ZZ_KKX-equivalent output.

3. **ZZ_KKX is missing most of the overlay's claude-side enrichment.** The current overlay ships `intent-gate.py`, `todo-enforcer.py`, `context-monitor.py`, `statusline*.py`, `ralph-loop.py`, `parse_sub2api_usage.py`, plus the entire `settings.overlay.json` (RTK hook, plugin enables, hook chain). **None** of these are present in ZZ_KKX. Either (a) the user pre-selected a minimal subset, or (b) ZZ_KKX was installed before these were added to the overlay. Whichever the answer, the user should explicitly decide whether the new `--overlay hiskens` should ship these.

4. **ZZ_KKX is missing the python/matlab spec packs.** The current overlay ships rich `templates/trellis/spec/{python,matlab}/` directories (~7 files each, plus example templates). ZZ_KKX has only the upstream `backend/` and `guides/` skeletons; the user filled `backend/` themselves. If `--overlay hiskens` is supposed to seed python/matlab specs, the user must explicitly opt in (and the install needs to reconcile with the user's pre-existing, hand-filled `backend/`).

5. **No project-level `CLAUDE.md`.** The only CLAUDE-style instruction file in the project is `AGENTS.md`, which is just the upstream template (no project-specific additions). Worth confirming whether the user wants the overlay to also drop a project-level `CLAUDE.md` template or leave that to the consumer.

6. **The `.trellis/scripts/common/*.pyc` files are present in ZZ_KKX** (Python bytecode cache). These should NOT be replicated — they are build artifacts. Trellis already ignores these via the `**/__pycache__/` rule in `.trellis/.gitignore`.
