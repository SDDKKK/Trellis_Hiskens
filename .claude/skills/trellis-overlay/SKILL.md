---
name: trellis-overlay
description: >
  Sync the hiskens Trellis fork with upstream mindfold-ai/Trellis and apply overlay customizations.
  This skill is the single source of truth for what makes the fork different and how to keep it current.
  Use when: the user says "sync upstream", "同步上游", "overlay sync", "trellis overlay", "跟上游同步",
  "upgrade trellis", "更新上游", or when upstream has new commits on feat/v0.5.0-rc that need merging.
  Also use when verifying or modifying fork customization points (MCP tools, statusline, version scheme).
---

# Trellis Overlay — Fork Sync & Customization

This skill covers keeping `Trellis_Hiskens` aligned with upstream `mindfold-ai/Trellis` while preserving hiskens-specific customizations. The fork uses a **rebase-on-top** model: upstream commits form the base, overlay commits sit on top.

---

## Hiskens Customization Points

Customizations live in `packages/cli/src/templates/` (distributed via `npm publish`) and `packages/cli/src/configurators/` (build-time logic). After rebase, verify each point is intact.

### 1. Package Identity

**File:** `packages/cli/package.json`

| Field | Upstream | Hiskens |
|-------|----------|---------|
| name | `@mindfoldhq/trellis` | `@hiskens/trellis` |
| version | `0.5.0-rc.3` | `0.5.0-rc.3-hiskens` |

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
| trellis-check | `mcp__augment-context-engine__*`, `mcp__grok-search__*` |
| trellis-implement | `mcp__augment-context-engine__*`, `mcp__grok-search__*` |
| trellis-research | `mcp__augment-context-engine__*`, `mcp__context7__*`, `mcp__grok-search__*` |

**Research agent Step 3** must use augment-first retrieval:

```
Before exact searches, use mcp__augment-context-engine__codebase-retrieval for ANY question
involving codebase, files, structure, dependencies, search, or context,
then run independent searches in parallel (Glob + Grep + mcp__grok-search__*) for efficiency.
```

**Platform-specific frontmatter format:**
- **opencode**: `permission:` block with `mcp__*: allow`
- **claude/cursor/codebuddy/qoder**: `tools:` frontmatter field
- **droid**: `tools:` frontmatter field (directory is `droids/` not `agents/`)

### 2b. Hook Script Tool References

**Files:**
- `packages/cli/src/templates/shared-hooks/inject-subagent-context.py` — `get_research_context()` search tips + `build_research_prompt()` tool table
- `packages/cli/src/templates/opencode/plugins/inject-subagent-context.js` — search tips text

The hook injects a tool availability table into research subagent prompts at runtime. Verify it lists augment/context7/grok, not exa.

### 2c. Copilot Tool Mapper

**File:** `packages/cli/src/configurators/shared.ts` — `mapLegacyToolToCopilot()`

Maps MCP tool wildcards to Copilot-native capability labels:

| MCP tool | Copilot mapping |
|----------|----------------|
| `mcp__augment-context-engine__*` | `["search"]` |
| `mcp__context7__*` | `["web"]` |
| `mcp__grok-search__*` | `["web"]` |

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

### 4. Upstream Version Tracker

**File:** `.upstream-version` (repo root)

Contains the upstream commit hash that the fork is currently based on. Updated after each successful rebase.

---

## Upstream Sync Workflow

### Step 1: Fetch & Assess

```bash
cd /home/hcx/github/Trellis_Hiskens
git fetch upstream feat/v0.5.0-rc --tags
CURRENT=$(cat .upstream-version)
git log --oneline $CURRENT..upstream/feat/v0.5.0-rc
git diff --stat $CURRENT..upstream/feat/v0.5.0-rc -- packages/cli/src/
```

Focus on overlay-relevant paths: `configurators/shared.ts`, `commands/update.ts`, `templates/shared-hooks/`, `templates/claude/agents/`, `templates/opencode/agents/`, `templates/cursor/agents/`, `templates/codebuddy/agents/`, `templates/droid/droids/`, `templates/qoder/agents/`, `templates/opencode/plugins/`.

### Step 2: Rebase Overlay Commits

```bash
git checkout -b sync/upstream-<tag>
git rebase --onto upstream/feat/v0.5.0-rc $CURRENT main
```

**Typical conflict:** `packages/cli/package.json` line 2-3 (name + version). Resolution: keep `@hiskens/trellis` name, set version to `{new-upstream-version}-hiskens`.

### Step 3: Verify Customizations

After rebase resolves, check each customization point:

```bash
# Check agent tools across ALL platforms (should return 0 hits for exa, 6+ for augment)
grep -rn "mcp__exa__" packages/cli/src/templates/*/agents/ packages/cli/src/templates/droid/droids/ && echo "FAIL: exa remnants" || echo "OK: no exa"
grep -rn "mcp__augment-context-engine" packages/cli/src/templates/*/agents/ packages/cli/src/templates/droid/droids/ | wc -l

# Check hook scripts tool table
grep "augment-context-engine" packages/cli/src/templates/shared-hooks/inject-subagent-context.py
grep "augment-context-engine" packages/cli/src/templates/opencode/plugins/inject-subagent-context.js

# Check Copilot tool mapper
grep "augment-context-engine" packages/cli/src/configurators/shared.ts

# Check statusline exists and is registered
grep "statusline" packages/cli/src/templates/shared-hooks/index.ts

# Check statusLine in settings
grep "statusLine" packages/cli/src/templates/claude/settings.json
```

If upstream modified any of these files, re-apply hiskens additions manually.

### Step 4: Update Metadata

```bash
# Record the new upstream base
echo "<new-upstream-commit-hash>" > .upstream-version

# Version is already set during conflict resolution in Step 2
grep '"version"' packages/cli/package.json
```

### Step 5: Commit & Force-Push Main

```bash
git commit -m "feat: @hiskens/trellis v{version} — sync upstream {tag} + overlay"

# Move main to the rebased branch
git checkout main && git reset --hard sync/upstream-<tag>
git push --force origin main
git branch -d sync/upstream-<tag>
```

### Step 6: Publish & Dogfood

Run the `trellis-publish` skill (`/trellis-publish`) which handles:
- Version bump → build → npm publish → global install → `trellis update --force` → commit dogfood

---

## Pitfalls

| Issue | Why it happens | Fix |
|-------|---------------|-----|
| `package.json` conflict on rebase | Both sides touch version/name | Accept upstream, then edit to hiskens values |
| MCP tools missing after rebase | Upstream rewrote agent template | Re-add tool wildcards to frontmatter (all 6 platforms) |
| Hook tool table reverted | Upstream rewrote inject-subagent-context | Re-apply augment/context7/grok in tool table + search tips |
| Copilot mapper missing new tools | Upstream rewrote shared.ts | Re-add cases in `mapLegacyToolToCopilot()` |
| statusline.py not distributed | Forgot to register in `index.ts` | Add to `SharedHookName` type + `claude` array |
| Force-push needed for main | Rebase rewrites history | This is expected; the fork has one consumer (us) |

For publish/dogfood pitfalls, see the `trellis-publish` skill.

---

## Key Facts

- **Upstream remote:** `https://github.com/mindfold-ai/Trellis.git`
- **Upstream branch:** `feat/v0.5.0-rc`
- **npm package:** `@hiskens/trellis`
- **Only `packages/cli/src/templates/` matters** — root-level `.claude/`, `.opencode/` etc. are this repo's own dogfood config, not the distributed templates
