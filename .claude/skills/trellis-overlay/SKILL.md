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

Eight numbered points, six still active (#4 retired at v0.6.14, numbering kept stable so older notes still resolve). The authoritative check is not this list but the diff itself — see **Overlay Audit** below, which regenerates the list from the repo and will catch anything this prose has drifted away from.

### 1. Package Identity

**File:** `packages/cli/package.json`

| Field | Upstream | Hiskens |
|-------|----------|---------|
| name | `@mindfoldhq/trellis` | `@hiskens/trellis` |
| version | `0.6.6` | `0.6.8-hiskens` |

Version format: `{upstream-version}-hiskens` — no trailing `.1` or build number.

**CRITICAL — `packages/core/package.json`:**
- **Name stays `@mindfoldhq/trellis-core`** (upstream's scope — we do NOT rename it)
- **Version stays aligned with upstream** (e.g., `0.6.6`, NOT `0.6.6-hiskens`)
- Reason: `pnpm publish` resolves `workspace:*` → the core version. The CLI declares `"@mindfoldhq/trellis-core": "workspace:*"`. If core's version is `0.6.6`, the published CLI depends on `@mindfoldhq/trellis-core@0.6.6` which already exists on npm (published by upstream). If we set it to `0.6.6-hiskens`, the published CLI depends on a version that doesn't exist on npm → `npm install -g` fails.
- **Rule:** During merge, if core has a conflict on version, always take upstream's version verbatim.

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

### 3. MCP Tool Provider (augment → ace-tool)

**Scope:** All agent templates + hooks across all platforms.

Upstream uses `mcp__augment-context-engine__*` (Augment's codebase-retrieval MCP). The hiskens fork replaces this with `mcp__ace-tool__*` (Ace-Tool MCP with `search_context` + `enhance_prompt`).

**Affected files (all under `packages/cli/src/templates/`):**
- `{claude,cursor,qoder,codebuddy}/agents/trellis-{check,implement}.md` — frontmatter `tools:` field
- `droid/droids/trellis-{check,implement}.md` — frontmatter `tools:` field
- `opencode/agents/trellis-{check,implement,research}.md` — `permission:` block
- `codex/agents/trellis-{check,implement,research}.toml` — instruction text
- `shared-hooks/inject-subagent-context.py` — search tool table + tips
- `opencode/plugins/inject-subagent-context.js` — search tool tips
- `packages/cli/src/configurators/shared.ts` — capability mapping `case`

**Post-sync verification:**

```bash
# Must return zero matches in src/ (not dist/)
grep -rn "augment-context-engine" packages/cli/src/ --include="*.md" --include="*.ts" --include="*.js" --include="*.py" --include="*.toml" | grep -v node_modules
```

**If upstream reintroduces `augment-context-engine`:** Replace all occurrences back to `ace-tool` after merge. The substitution is mechanical — `mcp__augment-context-engine__*` → `mcp__ace-tool__*` and `augment codebase-retrieval` → `ace-tool search_context` in instruction text.

### 4. ~~Pi Extension — SessionManager Method Binding~~ (RETIRED at v0.6.14)

Upstream fixed the same `this`-detachment bug in v0.6.14, using an explicit receiver instead of the fork's arrow-function wrapper:

```js
function callStr(cb, receiver?) { return str(cb.call(receiver)); }   // upstream v0.6.14+
callStr(ctx?.sessionManager?.getSessionId, ctx?.sessionManager)
```

Functionally equivalent to the fork's `callStr(() => ctx?.sessionManager?.getSessionId?.())`, and more explicit. The overlay was dropped during the v0.6.14 sync — `packages/cli/src/templates/pi/extensions/trellis/index.ts.txt` now tracks upstream verbatim.

**Do not re-add it.** If a future sync shows the fork diverging here again, that is a regression to revert, not an overlay to restore.

### 5. context7 MCP Capability

- `packages/cli/src/configurators/shared.ts` — `case "mcp__context7__*": return ["web"];`
- `packages/cli/src/templates/opencode/agents/trellis-research.md` — `mcp__context7__*: allow`

Upstream has zero `context7` references. Paired with the removal of `mcp__exa__*` (upstream's choice) from the opencode agents and `opencode/plugins/inject-subagent-context.js`.

### 6. Codex Tool-Routing Blocks

**Files:** `packages/cli/src/templates/codex/agents/trellis-{check,implement,research}.toml`

Each carries a `## Tool routing` section (~10 lines) steering the agent to `codegraph_impact` / `codegraph_callers` / `codegraph_search` / `codegraph_files` instead of defaulting to `grep -rn` and `ls`. `trellis-research.toml` additionally routes external research to the `smart-search` CLI. Upstream has no such section.

Related: every platform's agent `tools:` frontmatter gains `mcp__codegraph__*` alongside `mcp__ace-tool__*` (claude, cursor, qoder, codebuddy, droid).

### 7. session_auto_commit Enabled

**File:** `packages/cli/src/templates/trellis/config.yaml`

Upstream ships `# session_auto_commit: true` (commented, off by default). The fork uncomments it. A merge that takes upstream's line verbatim silently disables the feature for every newly-initialized project.

### 8. Upstream Version Tracker

**File:** `.upstream-version` (repo root)

Contains the upstream commit hash that the fork is currently synced to. Updated after each successful merge.

---

## Overlay Audit

Prose drifts; the diff does not. Run this after every merge — it reconstructs the *entire* overlay surface from the repo, so a customization nobody documented still shows up.

**Scan `test/` too, not just `src/`.** Fork test assertions are overlay: during the v0.6.14 sync a `platforms.test.ts` assertion still pinned the retired #4 arrow-function form and only surfaced as a test failure, because the audit was `src/`-only at the time. A fork overlay in `src/` almost always has a matching assertion in `test/`; retire them together.

```bash
cd /home/hcx/github/Trellis_Hiskens
python3 - "$(cat .upstream-version)" <<'PY'
import subprocess, sys, difflib
base = sys.argv[1]
files = subprocess.run(["git","diff","--name-only",base,"HEAD","--",
                        "packages/cli/src/","packages/cli/test/"],
                       capture_output=True,text=True).stdout.split()
for f in files:
    a = subprocess.run(["git","show",f"{base}:{f}"],capture_output=True,text=True).stdout.splitlines()
    try: b = open(f).read().splitlines()
    except FileNotFoundError: b = []
    d = [l for l in difflib.unified_diff(a,b,lineterm="",n=0)
         if l[:1] in "+-" and not l.startswith(("+++","---"))]
    if d:
        print(f"### {f}")
        for l in d: print("   ",l)
PY
```

Every hunk it prints is either a deliberate overlay edit or an accident. There is no third category. Reconcile each against the numbered list above; if something is unlisted, either document it or revert it.

**Fast per-point greps** (cheaper, but only catch what you remembered to write down — the audit above is the real check):

```bash
grep -c "get_ccr_model_tag" packages/cli/src/templates/shared-hooks/inject-subagent-context.py   # want 2
grep -c "ccr_routing" packages/cli/src/templates/trellis/config.yaml                             # want 1
diff <(git show <upstream-tag>:packages/cli/src/templates/pi/extensions/trellis/index.ts.txt) \
     packages/cli/src/templates/pi/extensions/trellis/index.ts.txt   # want empty (#4 retired)
grep -c "context7" packages/cli/src/configurators/shared.ts                                      # want 1
grep -lc "Tool routing" packages/cli/src/templates/codex/agents/*.toml | wc -l                   # want 3
grep -c "^session_auto_commit: true" packages/cli/src/templates/trellis/config.yaml              # want 1
grep -rn "augment-context-engine" packages/cli/src/ | grep -v node_modules                        # want empty
# exa: only the agent templates must be clean. shared.ts keeps mcp__exa__* capability cases and
# migrations/manifests/*.json quote upstream's historical changelogs — both are expected hits.
grep -rn "mcp__exa__" packages/cli/src/templates/{claude,cursor,qoder,codebuddy,droid,opencode,codex}/ # want empty
```

---

## Removed Customizations (v0.6.2 cleanup)

The following were removed and should NOT be re-added:

| Item | Reason |
|------|--------|
| statusline.py hook | Replaced by ccline fork (its `shared-hooks.test.ts` assertions were finally deleted during the v0.6.10 sync — they had been failing since v0.6.2) |
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

**Predict conflicts before merging** — don't guess from commit subjects. Two commits can both "touch context key resolution" and still never collide, because upstream edits workspace scripts (`.trellis/scripts/common/*.py`) while the fork edits distributed templates (`packages/cli/src/templates/`). These are parallel copies with separate paths.

```bash
# Which files do both sides actually touch?
MB=$(git merge-base HEAD upstream/main)
comm -12 <(git diff --name-only $MB HEAD | sort) <(git diff --name-only $MB upstream/main | sort)

# Dry-run the merge without touching the worktree; prints real conflicts
git merge-tree --write-tree --name-only HEAD upstream/main
```

`merge-tree` emits the merged tree hash on line 1 — inspect overlay survival in it *before* committing to the merge:

```bash
T=<tree-hash-from-line-1>
git show $T:packages/cli/src/templates/shared-hooks/inject-subagent-context.py | grep -c get_ccr_model_tag
git grep -l "augment-context-engine" $T -- packages/cli/src   # want no output
```

**Capture the pre-merge test baseline.** The fork carries long-standing failures; without a baseline you cannot tell a regression from inherited breakage.

```bash
git worktree add /tmp/pre-merge HEAD
cd /tmp/pre-merge && pnpm install --frozen-lockfile && cd packages/cli && pnpm test 2>&1 | grep -E "Tests |×"
# ...after merging, diff the failure lists. Then:
git worktree remove /tmp/pre-merge --force
```

### Step 2: Merge Upstream

```bash
git merge upstream/main --no-edit
```

**Typical conflicts:** `packages/cli/package.json` (name + version), `packages/core/package.json` (version), `.trellis/.version`, `.trellis/config.yaml`, `.trellis/.template-hashes.json`, submodules (`docs-site`, `marketplace`). Resolution:
- `packages/cli/package.json`: keep `@hiskens/trellis` name, set version to `{new-upstream-version}-hiskens`
- `packages/core/package.json`: **take upstream's version verbatim** (e.g., `0.6.6`). Do NOT add `-hiskens` suffix — the CLI depends on this version via `workspace:*`, and only upstream's version exists on npm.
- `.trellis/.version`: set to `{new-upstream-version}-hiskens`
- `.trellis/config.yaml`: take upstream's new sections, preserve Feature Flags section with `ccr_routing: true`
- `.trellis/.template-hashes.json`: take upstream's hashes
- Submodules (`docs-site`, `marketplace`): take upstream's commit pointers — `git checkout --theirs <submodule> && cd <submodule> && git checkout <upstream-commit> && cd .. && git add <submodule>`
- Workspace journals: keep ours (`git checkout --ours`)

### Step 3: Verify Customizations

Run the **Overlay Audit** script (see above) with `.upstream-version` still holding the *previous* baseline — that diff is the fork's entire delta against upstream. Reconcile every hunk against customization points 1–8 (#4 is retired — a hunk there is a regression, not an overlay). Anything unlisted is either an undocumented overlay (document it) or an accident (revert it).

Then the fast greps from the Overlay Audit section, plus:

```bash
grep '"version"' packages/cli/package.json          # {upstream}-hiskens
grep '"version"' packages/core/package.json         # plain upstream, NO -hiskens
```

Repair notes when a check fails:
- `get_ccr_model_tag` missing → re-add `_load_features`, `_ccr_model_keys`, `get_ccr_model_tag` + the 2 call sites in `main()`
- `augment-context-engine` reappeared → mechanical replace back to `ace-tool` (point 3)
- pi `callStr` unwrapped → re-wrap both call sites in arrow functions (point 4)
- `session_auto_commit` re-commented → uncomment (point 7)

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
| **core version set to `-hiskens`** | **Merge resolved core/package.json wrong** | **Always take upstream's core version verbatim — the CLI depends on it via `workspace:*` and only upstream's version exists on npm** |
| CCR routing lost after update | Upstream overwrote inject-subagent-context.py | Verify `get_ccr_model_tag` exists; re-add `_load_features`, `_ccr_model_keys`, `get_ccr_model_tag` + 2 call sites in `main()` |
| Feature Flags missing from config template | Upstream overwrote `templates/trellis/config.yaml` | Re-add `Feature Flags` `#---` block with `features.ccr_routing: true` before the Codex section |
| `augment-context-engine` reappears after merge | Upstream updated agent templates or hooks | Replace all `mcp__augment-context-engine__*` → `mcp__ace-tool__*` and `augment codebase-retrieval` → `ace-tool search_context` in `packages/cli/src/` |
| CCR routing works but no model switch | Claude Code updated subagent message format | Verify `custom-router.js` uses `includes()` not `startsWith()` |
| Version already published before the sync landed | A dogfood release used `{upstream}-hiskens` while the fork's baseline was still an older upstream tag, burning the name | Check `npm view @hiskens/trellis version` during Step 4. If it already equals the target, publish the next patch (e.g. `0.6.11-hiskens`) — never republish |
| An overlay edit silently reverts to upstream's version | Merge resolved a template file toward upstream, and no grep covered that customization | Run the **Overlay Audit** (diff-based, catches undocumented points) — not just the per-point greps, which only find what someone remembered to write down |
| Pi extension diverges from upstream again | Someone re-applied the retired #4 arrow-function overlay | Revert to upstream verbatim — upstream's `cb.call(receiver)` already fixes the `this` detachment |
| New projects stop auto-committing sessions | `templates/trellis/config.yaml` took upstream's commented-out `# session_auto_commit: true` | Uncomment it (point 7) |
| Predicted a conflict from commit subjects, found none (or vice versa) | Upstream `.trellis/scripts/common/*.py` and fork `packages/cli/src/templates/**` are parallel copies with distinct paths | Use `merge-tree` + `comm` (Step 1) instead of reasoning from commit messages |
| npm unpublish then republish same version | npm has a 24h cooldown after unpublish | Bump patch version (e.g., `0.6.6-hiskens` → `0.6.7-hiskens`). Note: semver does NOT allow 4-segment versions (`0.6.6.1-hiskens` is invalid) |

---

## Key Facts

- **Upstream remote:** `https://github.com/mindfold-ai/Trellis.git`
- **Upstream branch:** `main`
- **npm package:** `@hiskens/trellis`
- **Overlay surface:** 6 active customization points — package identity, CCR routing, ace-tool (replacing augment + exa), context7, Codex tool-routing blocks, session_auto_commit. (#4 pi SessionManager binding retired at v0.6.14.) Verify with the Overlay Audit, not from memory.
- **Only `packages/cli/src/templates/` matters** — root-level `.claude/`, `.opencode/` etc. are this repo's own dogfood config, not the distributed templates
