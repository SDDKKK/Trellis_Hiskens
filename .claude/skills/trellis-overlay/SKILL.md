---
name: trellis-overlay
description: >
  Sync the hiskens Trellis fork with upstream mindfold-ai/Trellis and apply overlay customizations.
  This skill is the single source of truth for what makes the fork different and how to keep it current.
  Use when: the user says "sync upstream", "同步上游", "overlay sync", "trellis overlay", "跟上游同步",
  "upgrade trellis", "更新上游", or when upstream has new commits that need merging.
  Also use when verifying or modifying fork customization points (CCR routing, version scheme).
---

# Trellis Overlay — Fork Sync & Customization

This skill covers keeping `Trellis_Hiskens` aligned with upstream `mindfold-ai/Trellis` while preserving hiskens-specific customizations. The fork uses a **merge** model: upstream changes are merged into main, overlay commits stay intact.

---

## Hiskens Customization Points

The overlay surface is intentionally minimal. Only two categories of customization remain after the v0.6.2 cleanup.

### 1. Package Identity

**File:** `packages/cli/package.json`

| Field | Upstream | Hiskens |
|-------|----------|---------|
| name | `@mindfoldhq/trellis` | `@hiskens/trellis` |
| version | `0.6.2` | `0.6.2-hiskens` |

Version format: `{upstream-version}-hiskens` — no trailing `.1` or build number.

### 2. CCR Model Routing

**File:** `packages/cli/src/templates/shared-hooks/inject-subagent-context.py`

Three functions provide Claude Code Router model tag injection for subagents:
- `_load_features()` — parses `.trellis/config.yaml` feature flags
- `_ccr_model_keys()` — maps subagent type to model lookup aliases
- `get_ccr_model_tag()` — 3-guard check (feature flag + localhost base URL + agent-models.json), returns `<CCR-SUBAGENT-MODEL>` XML tag

Two call sites in `main()`:
- `ccr_tag = get_ccr_model_tag(repo_root, subagent_type)` after `find_repo_root()`
- `new_prompt = ccr_tag + new_prompt` before output assembly

**Distributed default (in template):**
- `packages/cli/src/templates/trellis/config.yaml` — `features.ccr_routing: true` (Feature Flags section). This section is distributed to new projects on `trellis init` and surfaced to existing projects via `configSectionsAdded` migration on `trellis update`.

**Runtime config (project-side):**
- `.trellis/config.yaml` — `features.ccr_routing: true` (inherited from template on init; user may override)
- `.trellis/config/agent-models.json` — agent → CCR provider/model mapping

**CCR-side requirement:** `~/.claude-code-router/custom-router.js` must use `includes()` (not `startsWith()`) to match the `<CCR-SUBAGENT-MODEL>` tag, because Claude Code v2.1.178+ wraps subagent prompts in `<teammate-message>` tags.

**Post-sync verification:** After every upstream merge, confirm the CCR code survives:

```bash
grep "get_ccr_model_tag" packages/cli/src/templates/shared-hooks/inject-subagent-context.py
grep "ccr_routing" packages/cli/src/templates/trellis/config.yaml
```

### 3. Upstream Version Tracker

**File:** `.upstream-version` (repo root)

Contains the upstream commit hash that the fork is currently synced to. Updated after each successful merge.

---

## Removed Customizations (v0.6.2 cleanup)

The following were removed and should NOT be re-added:

| Item | Reason |
|------|--------|
| statusline.py hook | Replaced by ccline fork |
| Channel agents (architect/plan/research) | Upstream doesn't distribute; never adopted downstream |
| Codegraph ToolSearch preload in agent templates | No longer needed; tools load on demand |
| sync-trellis-to-nocturne.py | Nocturne no longer used |
| subagent-audit toolkit | MCP tools universally available |

---

## Upstream Sync Workflow

### Step 1: Fetch & Assess

```bash
cd /home/hcx/github/Trellis_Hiskens
git fetch upstream main --tags
CURRENT=$(cat .upstream-version)
git log --oneline $CURRENT..upstream/main
git diff --stat $CURRENT..upstream/main -- packages/cli/src/
```

Focus on overlay-relevant paths: `templates/shared-hooks/inject-subagent-context.py`, `templates/trellis/config.yaml`.

### Step 2: Merge Upstream

```bash
git merge upstream/main --no-edit
```

**Typical conflicts:** `packages/cli/package.json` (name + version), `.trellis/.version`, `.trellis/config.yaml`, `.trellis/.template-hashes.json`. Resolution:
- `package.json`: keep `@hiskens/trellis` name, set version to `{new-upstream-version}-hiskens`
- `.trellis/.version`: set to `{new-upstream-version}-hiskens`
- `.trellis/config.yaml`: take upstream's new sections, preserve Feature Flags section with `ccr_routing: true`
- `.trellis/.template-hashes.json`: take upstream's hashes
- workspace journals: keep ours (`git checkout --ours`)

### Step 3: Verify Customizations

After merge resolves, check each customization point:

```bash
# Check CCR model routing in hook
grep "get_ccr_model_tag" packages/cli/src/templates/shared-hooks/inject-subagent-context.py

# Check Feature Flags section in config template (ccr_routing default)
grep "ccr_routing" packages/cli/src/templates/trellis/config.yaml || echo "FAIL: ccr_routing missing from config template"

# Check version
grep '"version"' packages/cli/package.json
```

If upstream modified `inject-subagent-context.py`, re-apply the CCR functions manually.

### Step 4: Update Metadata

```bash
echo "<new-upstream-commit-hash>" > .upstream-version
grep '"version"' packages/cli/package.json
```

### Step 5: Commit & Push

```bash
git commit -m "feat: @hiskens/trellis v{version} — sync upstream {tag} + overlay"
git push origin main
```

### Step 6: Publish & Dogfood

Run the `trellis-publish` skill (`/trellis-publish`) which handles:
- Version bump → build → npm publish → global install → `trellis update --force` → commit dogfood

---

## Pitfalls

| Issue | Why it happens | Fix |
|-------|---------------|-----|
| `package.json` conflict on merge | Both sides touch version/name | Keep hiskens name, set `{upstream-version}-hiskens` |
| CCR routing lost after update | Upstream overwrote inject-subagent-context.py | Verify `get_ccr_model_tag` exists; re-add `_load_features`, `_ccr_model_keys`, `get_ccr_model_tag` + 2 call sites in `main()` |
| Feature Flags missing from config template | Upstream overwrote `templates/trellis/config.yaml` | Re-add `Feature Flags` `#---` block with `features.ccr_routing: true` before the Codex section |
| CCR routing works but no model switch | Claude Code updated subagent message format | Verify `custom-router.js` uses `includes()` not `startsWith()` |

---

## Key Facts

- **Upstream remote:** `https://github.com/mindfold-ai/Trellis.git`
- **Upstream branch:** `main`
- **npm package:** `@hiskens/trellis`
- **Overlay surface:** 2 customization points (package identity + CCR routing)
- **Only `packages/cli/src/templates/` matters** — root-level `.claude/`, `.opencode/` etc. are this repo's own dogfood config, not the distributed templates
