---
name: trellis-overlay
description: >
  Sync the hiskens Trellis fork with upstream mindfold-ai/Trellis and apply overlay customizations.
  This skill is the single source of truth for what makes the fork different and how to keep it current.
  Use when: the user says "sync upstream", "同步上游", "overlay sync", "trellis overlay", "跟上游同步",
  "upgrade trellis", "更新上游", or when upstream has new commits on feat/v0.6.0-beta that need merging.
  Also use when verifying or modifying fork customization points (MCP tools, statusline, version scheme).
---

# Trellis Overlay — Fork Sync & Customization

This skill covers keeping `Trellis_Hiskens` aligned with upstream `mindfold-ai/Trellis` while preserving hiskens-specific customizations. The fork uses a **merge** model: upstream changes are merged into main, overlay commits stay intact.

---

## Hiskens Customization Points

Customizations live in `packages/cli/src/templates/` (distributed via `npm publish`) and `packages/cli/src/configurators/` (build-time logic). After merge, verify each point is intact.

### 1. Package Identity

**File:** `packages/cli/package.json`

| Field | Upstream | Hiskens |
|-------|----------|---------|
| name | `@mindfoldhq/trellis` | `@hiskens/trellis` |
| version | `0.6.0-beta.3` | `0.6.0-beta.3-hiskens` |

Version format: `{upstream-version}-hiskens` — no trailing `.1` or build number.

### 2. Agent MCP Tool Wildcards

**Files — 6 platforms × 3 agents = 18 template files:**

| Platform | Path pattern |
|----------|-------------|
| claude | `templates/claude/agents/trellis-{check,implement,research}.md` |
| opencode | `templates/opencode/agents/trellis-{check,implement,research}.md` |
| cursor | `templates/cursor/agents/trellis-{check,implement,research}.md` |
| codebuddy | `templates/codebuddy/agents/trellis-{check,implement,research}.md` |
| droid | `templates/droid/droids/trellis-{check,implement,research}.md` |
| qoder | `templates/qoder/agents/trellis-{check,implement,research}.md` |

All paths relative to `packages/cli/src/`.

**What to add/verify:**

| Agent | Tools (beyond platform defaults) |
|-------|----------------------------------|
| trellis-check | `mcp__augment-context-engine__*` |
| trellis-implement | `mcp__augment-context-engine__*` |
| trellis-research | `mcp__augment-context-engine__*`, `mcp__context7__*` |

Web search uses `smart-search` CLI via Bash (not MCP). The `smart-search-cli` skill is installed at user level (`~/.claude/skills/smart-search-cli/`) and handles routing (search/exa-search/zhipu-search/fetch/deep). Agents already have Bash permission.

**Research agent Step 3** must use augment-first retrieval:

```
Before exact searches, use mcp__augment-context-engine__codebase-retrieval for ANY question
involving codebase, files, structure, dependencies, search, or context,
then run independent searches in parallel (Glob + Grep + smart-search CLI via Bash) for efficiency.
```

**Platform-specific frontmatter format:**
- **opencode**: `permission:` block with `mcp__*: allow`
- **claude/cursor/codebuddy/qoder**: `tools:` frontmatter field
- **droid**: `tools:` frontmatter field (directory is `droids/` not `agents/`)

### 2b. Hook Script Tool References

**Files:**
- `packages/cli/src/templates/shared-hooks/inject-subagent-context.py` — `get_research_context()` search tips + `build_research_prompt()` tool table
- `packages/cli/src/templates/opencode/plugins/inject-subagent-context.js` — search tips text

The hook injects a tool availability table into research subagent prompts at runtime. Verify it lists augment/context7/smart-search CLI, not grok-search MCP or exa MCP.

### 2c. Copilot Tool Mapper

**File:** `packages/cli/src/configurators/shared.ts` — `mapLegacyToolToCopilot()`

Maps MCP tool wildcards to Copilot-native capability labels:

| MCP tool | Copilot mapping |
|----------|----------------|
| `mcp__augment-context-engine__*` | `["search"]` |
| `mcp__context7__*` | `["web"]` |

Note: `mcp__grok-search__*` mapping removed — web search now uses smart-search CLI via Bash, which doesn't need Copilot tool mapping.

### 3. StatusLine Hook

**Files:**
- `packages/cli/src/templates/shared-hooks/statusline.py` — the hook script (additive, not in upstream)
- `packages/cli/src/templates/shared-hooks/index.ts` — register `"statusline.py"` in `SharedHookName` type and add to `claude` platform list
- `packages/cli/src/templates/claude/settings.json` — add statusLine config block

**statusLine config:**
```json
"statusLine": {
  "type": "command",
  "command": "{{PYTHON_CMD}} .claude/hooks/statusline.py",
  "refreshInterval": 5
}
```

**index.ts comment:** Replace the upstream "intentionally not installed" comment with a note that hiskens overlay installs it by default.

### 4. CCR Model Routing

**File:** `packages/cli/src/templates/shared-hooks/inject-subagent-context.py`

Three functions provide Claude Code Router model tag injection for subagents:
- `_load_features()` — parses `.trellis/config.yaml` feature flags
- `_ccr_model_keys()` — maps subagent type to model lookup aliases
- `get_ccr_model_tag()` — 3-guard check (feature flag + localhost base URL + agent-models.json), returns `<CCR-SUBAGENT-MODEL>` XML tag

Two call sites in `main()`:
- `ccr_tag = get_ccr_model_tag(repo_root, subagent_type)` after `find_repo_root()`
- `new_prompt = ccr_tag + new_prompt` before output assembly

**Runtime config (project-side, not in template):**
- `.trellis/config.yaml` — `features.ccr_routing: true`
- `.trellis/config/agent-models.json` — agent → CCR provider/model mapping

**Verification:** `grep "get_ccr_model_tag" packages/cli/src/templates/shared-hooks/inject-subagent-context.py`

### 5. Upstream Version Tracker

**File:** `.upstream-version` (repo root)

Contains the upstream commit hash that the fork is currently synced to. Updated after each successful merge.

---

## Upstream Sync Workflow

### Step 1: Fetch & Assess

```bash
cd /home/hcx/github/Trellis_Hiskens
git fetch upstream feat/v0.6.0-beta --tags
CURRENT=$(cat .upstream-version)
git log --oneline $CURRENT..upstream/feat/v0.6.0-beta
git diff --stat $CURRENT..upstream/feat/v0.6.0-beta -- packages/cli/src/
```

Focus on overlay-relevant paths: `configurators/shared.ts`, `commands/update.ts`, `templates/shared-hooks/`, `templates/claude/agents/`, `templates/opencode/agents/`, `templates/cursor/agents/`, `templates/codebuddy/agents/`, `templates/droid/droids/`, `templates/qoder/agents/`, `templates/opencode/plugins/`.

### Step 2: Merge Upstream

```bash
git merge upstream/feat/v0.6.0-beta --no-edit
```

**Typical conflicts:** `packages/cli/package.json` (name + version), `.trellis/.version`, `.trellis/config.yaml`, `.trellis/.template-hashes.json`. Resolution:
- `package.json`: keep `@hiskens/trellis` name, set version to `{new-upstream-version}-hiskens`
- `.trellis/.version`: set to `{new-upstream-version}-hiskens`
- `.trellis/config.yaml`: take upstream's new sections, preserve hiskens-specific values
- `.trellis/.template-hashes.json`: take upstream's hashes
- workspace journals: keep ours (`git checkout --ours`)

### Step 3: Verify Customizations

After merge resolves, check each customization point:

```bash
# Check agent tools across ALL platforms (should return 0 hits for exa/grok-search, 6+ for augment)
grep -rn "mcp__exa__\|mcp__grok-search__" packages/cli/src/templates/*/agents/ packages/cli/src/templates/droid/droids/ && echo "FAIL: exa/grok remnants" || echo "OK: no exa/grok in agents"
grep -rn "mcp__augment-context-engine" packages/cli/src/templates/*/agents/ packages/cli/src/templates/droid/droids/ | wc -l

# Check hook scripts reference smart-search CLI (not grok-search MCP)
grep "smart-search" packages/cli/src/templates/shared-hooks/inject-subagent-context.py
grep "smart-search" packages/cli/src/templates/opencode/plugins/inject-subagent-context.js

# Check Copilot tool mapper (should NOT have grok-search)
grep "augment-context-engine" packages/cli/src/configurators/shared.ts
grep "grok-search" packages/cli/src/configurators/shared.ts && echo "FAIL: grok in mapper" || echo "OK: no grok in mapper"

# Check statusline exists and is registered
grep "statusline" packages/cli/src/templates/shared-hooks/index.ts

# Check statusLine in settings
grep "statusLine" packages/cli/src/templates/claude/settings.json

# Check CCR model routing in hook
grep "get_ccr_model_tag" packages/cli/src/templates/shared-hooks/inject-subagent-context.py
```

If upstream modified any of these files, re-apply hiskens additions manually.

### Step 4: Update Metadata

```bash
# Record the new upstream base
echo "<new-upstream-commit-hash>" > .upstream-version

# Version is already set during conflict resolution in Step 2
grep '"version"' packages/cli/package.json
```

### Step 5: Commit & Push

The merge commit is created during Step 2. If conflict resolution was needed, the commit message should follow this format:

```bash
git commit -m "feat: @hiskens/trellis v{version} — sync upstream {tag} + overlay"
git push origin main
```

No force-push needed — merge preserves history.

### Step 6: Publish & Dogfood

Run the `trellis-publish` skill (`/trellis-publish`) which handles:
- Version bump → build → npm publish → global install → `trellis update --force` → commit dogfood

---

## Pitfalls

| Issue | Why it happens | Fix |
|-------|---------------|-----|
| `package.json` conflict on merge | Both sides touch version/name | Keep hiskens name, set `{upstream-version}-hiskens` |
| MCP tools missing after merge | Upstream rewrote agent template | Re-add augment/context7 tool wildcards to frontmatter (all 6 platforms); web search uses smart-search CLI via Bash, no MCP entry needed |
| Hook tool table reverted | Upstream rewrote inject-subagent-context | Re-apply augment/context7/smart-search CLI in tool table + search tips |
| Copilot mapper missing new tools | Upstream rewrote shared.ts | Re-add augment/context7 cases in `mapLegacyToolToCopilot()` (grok-search removed — web search is CLI-based) |
| statusline.py not distributed | Forgot to register in `index.ts` | Add to `SharedHookName` type + `claude` array |
| CCR routing lost after update | Upstream overwrote inject-subagent-context.py | Verify `get_ccr_model_tag` exists in shared-hooks template; re-add `_load_features`, `_ccr_model_keys`, `get_ccr_model_tag` + 2 call sites in `main()` |

For publish/dogfood pitfalls, see the `trellis-publish` skill.

---

## Key Facts

- **Upstream remote:** `https://github.com/mindfold-ai/Trellis.git`
- **Upstream branch:** `feat/v0.6.0-beta`
- **npm package:** `@hiskens/trellis`
- **Only `packages/cli/src/templates/` matters** — root-level `.claude/`, `.opencode/` etc. are this repo's own dogfood config, not the distributed templates
