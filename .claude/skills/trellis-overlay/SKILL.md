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

All customizations live in `packages/cli/src/templates/` — the source templates distributed via `npm publish`. After rebase, verify each point is intact.

### 1. Package Identity

**File:** `packages/cli/package.json`

| Field | Upstream | Hiskens |
|-------|----------|---------|
| name | `@mindfoldhq/trellis` | `@hiskens/trellis` |
| version | `0.5.0-rc.3` | `0.5.0-rc.3-hiskens` |

Version format: `{upstream-version}-hiskens` — no trailing `.1` or build number.

### 2. Agent MCP Tool Wildcards

**Files (claude):**
- `packages/cli/src/templates/claude/agents/trellis-check.md`
- `packages/cli/src/templates/claude/agents/trellis-implement.md`
- `packages/cli/src/templates/claude/agents/trellis-research.md`

**Files (opencode):**
- `packages/cli/src/templates/opencode/agents/trellis-check.md`
- `packages/cli/src/templates/opencode/agents/trellis-implement.md`
- `packages/cli/src/templates/opencode/agents/trellis-research.md`

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

For **opencode**, these go in the `permission:` frontmatter block. For **claude**, they go in the `tools:` frontmatter field.

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

Focus on overlay-relevant paths: `configurators/`, `commands/update.ts`, `templates/shared-hooks/`, `templates/claude/agents/`, `templates/opencode/agents/`.

### Step 2: Rebase Overlay Commits

```bash
git checkout -b sync/upstream-<tag>
git rebase --onto upstream/feat/v0.5.0-rc $CURRENT main
```

**Typical conflict:** `packages/cli/package.json` line 2-3 (name + version). Resolution: keep `@hiskens/trellis` name, set version to `{new-upstream-version}-hiskens`.

### Step 3: Verify Customizations

After rebase resolves, check each customization point:

```bash
# Check agent tools are intact
grep "mcp__augment-context-engine" packages/cli/src/templates/claude/agents/trellis-check.md
grep "mcp__augment-context-engine" packages/cli/src/templates/opencode/agents/trellis-check.md

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

### Step 5: Build & Test

```bash
pnpm install && pnpm build && pnpm test
```

Known upstream test flakes (ignore if overlay-unrelated):
- `template-fetcher.test.ts` — git registry env dependency
- `uninstall.integration.test.ts` — platform-specific path issues

### Step 6: Commit & Force-Push Main

```bash
git commit -m "feat: @hiskens/trellis v{version} — sync upstream {tag} + overlay"

# Move main to the rebased branch
git checkout main && git reset --hard sync/upstream-<tag>
git push --force origin main
git branch -d sync/upstream-<tag>
```

### Step 7: Publish to npm

```bash
pnpm build && cd packages/cli && npm publish --access public --ignore-scripts
```

`--ignore-scripts` skips `prepublishOnly` which re-runs tests. The build is already validated.

### Step 8: Dogfood — Self-Update This Repo

```bash
node packages/cli/dist/cli/index.js update --dry-run   # preview changes
node packages/cli/dist/cli/index.js update --force      # apply all
```

**Verify in dry-run output:**
- `+ .claude/hooks/statusline.py` appears as new file (or auto-update)
- Agent files show as updated
- `settings.json` shows as updated with statusLine config

### Step 9: Commit Dogfood & Push

```bash
git add .agents/ .claude/ .codex/ .cursor/ .opencode/ .pi/ \
       .trellis/.template-hashes.json .trellis/.version .trellis/config.yaml \
       .trellis/scripts/ .trellis/config/
git commit -m "chore: trellis self-update {old} → {new}"
git push origin main
```

---

## Pitfalls

| Issue | Why it happens | Fix |
|-------|---------------|-----|
| `package.json` conflict on rebase | Both sides touch version/name | Accept upstream, then edit to hiskens values |
| MCP tools missing after rebase | Upstream rewrote agent template | Re-add tool wildcards to frontmatter |
| statusline.py not distributed | Forgot to register in `index.ts` | Add to `SharedHookName` type + `claude` array |
| npm publish fails with test errors | `prepublishOnly` runs tests | Use `--ignore-scripts` |
| Self-update shows no changes | Forgot to `pnpm build` after edit | Always build before dogfood |
| Force-push needed for main | Rebase rewrites history | This is expected; the fork has one consumer (us) |

---

## Key Facts

- **Upstream remote:** `https://github.com/mindfold-ai/Trellis.git`
- **Upstream branch:** `feat/v0.5.0-rc`
- **npm package:** `@hiskens/trellis`
- **Only `packages/cli/src/templates/` matters** — root-level `.claude/`, `.opencode/` etc. are this repo's own dogfood config, not the distributed templates
