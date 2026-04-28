# Phase A/B/C Playbook Specialized for v0.4.0-beta.10 → v0.5.0-beta.14

> Replacement for failed Agent 4 (Kimi 262K-token limit hit). Authored by integrating dispatcher
> from Agents 1, 2b, 3 + ground-truth re-verification.
>
> **Cross-references**: `01-topic-map.md` (themes), `02-critical-overrides.md` (engine/manifests),
> `03-overlay-conflict-map.md` (per-file map). Master playbook: `.trellis/spec/guides/fork-sync-guide.md`.

---

## 0. Sync Target Decision

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| Tag `v0.5.0-beta.14` (`943a608`) | Stable label, latest beta on tag, breaking-change manifests already locked | Still "beta" — upstream may follow with beta.15+ before 0.5.0 stable | **PICK THIS** |
| Branch tip `upstream/feat/v0.5.0-beta` (`f433ce5e`) | Bleeding edge, includes `45627fd chore(release): 0.5.0-beta.14 manifest + docs-site changelog` already | Moving target; sync may go stale before merge to main | reject |
| Wait for `v0.5.0` stable | No beta-tag churn | Unknown timeline; v0.5.0-beta has been out since beta.0; stable may add another month | reject for now |

**Decision**: target `v0.5.0-beta.14`. If upstream tags beta.15 before the maintainer executes, re-pin the head reference and continue.

**Rationale**: 12 of 15 beta manifests are empty (patch-only). The breaking surface is concentrated in beta.0 (206 ops: 68 rename + 138 safe-file-delete) and beta.5 (30 rename). Beyond beta.5, the upgrade path is essentially flat. Picking beta.14 absorbs all bug fixes (Windows statusline, GBK encoding, session-start announce) at zero additional migration cost.

---

## 1. Pre-flight Checklist

```bash
cd /home/hcx/github/Trellis_Hiskens

# A. Working tree must be clean (Pitfall 8)
git status --porcelain   # expect zero output
git fetch origin --prune
[ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] || git pull --ff-only origin main

# B. Active task scan — warn if any in-progress task would be disrupted
python3 ./.trellis/scripts/task.py list
# Currently 5 active (3 @taosu planning, 1 @codex-agent done, 1 @Hiskens planning P2). All planning/done — safe.

# C. Backup tag (named so future grep -lE 'fork-pre' finds it)
git tag fork-pre-v0.5.0-sync-$(date +%Y%m%d)
git tag -l 'fork-pre-*'

# D. Confirm upstream refs locally
git fetch upstream --tags --prune
git rev-parse v0.4.0-beta.10 v0.5.0-beta.14 upstream/feat/v0.5.0-beta
# expect: 737f7508..., 943a6087..., f433ce5e...

# E. Disk + node_modules sanity (rebuild required if packages/cli/src/**.ts changed in merge)
du -sh node_modules packages/cli/dist 2>/dev/null
find packages/cli/src -name '*.ts' -newer packages/cli/dist/cli/index.js 2>/dev/null | head
# After merge, expect MANY .ts files newer than dist → REBUILD MANDATORY before any downstream sync

# F. Snapshot fork-internal user data so we can prove preservation
mkdir -p /tmp/sync-v0.5.0
find .trellis/tasks .trellis/workspace -type f \
  \( -name "*.md" -o -name "*.json" -o -name "*.jsonl" -o -name "*.yaml" \) \
  -print0 | sort -z | xargs -0 sha256sum > /tmp/sync-v0.5.0/fork-pre.sha256
# Note: this fork repo's .trellis/{tasks,workspace} are also dev artifacts. Sync should not touch them.
```

**Stop here and review with maintainer if** any of the following:
- `task.py list` shows in-progress tasks with active jsonl edits
- working tree dirty in any path beyond `.trellis/tasks/04-26-research-v0-5-0-beta-sync/` (this research)
- `node_modules` missing (run `pnpm install` first)

---

## 2. Phase A — Safe Merge

### 2.1 Branch creation + pre-merge overlay relaxation

The current `overlays/hiskens/overlay.yaml` declares `compatible_upstream: ">=0.4.0-beta.10 <0.5.0"`. This is a hard gate — the overlay loader will refuse to run on a 0.5 base. **The very first commit on the sync branch must relax this**, because otherwise `pnpm test` will fail before we have a chance to triage merge conflicts.

```bash
git checkout -b sync/upstream-v0.5.0-beta.14

# Edit overlay.yaml: bump compatible_upstream
# from: ">=0.4.0-beta.10 <0.5.0"
# to:   ">=0.5.0-beta.14 <0.6.0"
# (we are upgrading the floor, not just relaxing the ceiling — overlay v0.5 will not be installable on
#  pre-0.5 upstream after the structural rewrite)

# Also bump version: 1.0.0 → 2.0.0 (semver: this overlay release is a breaking change to consumers)

# Update .upstream-version: v0.4.0-beta.10 → v0.5.0-beta.14
echo 'v0.5.0-beta.14' > .upstream-version

# Update HISKENS.md "Based on" line correspondingly.

git add overlays/hiskens/overlay.yaml .upstream-version HISKENS.md
git commit -m "chore(overlay): relax compatible_upstream + version bump for v0.5.0-beta.14 sync

Pre-merge bump so the post-merge tree validates against the new upstream floor.
Companion to upcoming sync/upstream-v0.5.0-beta.14 merge commit.

- compatible_upstream: '>=0.4.0-beta.10 <0.5.0' → '>=0.5.0-beta.14 <0.6.0'
- overlay version: 1.0.0 → 2.0.0 (breaking: skill-first refactor + shared-hooks migration)
- .upstream-version: v0.4.0-beta.10 → v0.5.0-beta.14"
```

### 2.2 Merge

```bash
# Merge target tag (NOT branch tip — pin to immutable commit for reproducibility)
git merge v0.5.0-beta.14 --no-ff -m "merge: sync upstream v0.5.0-beta.14 into hiskens fork

Upstream notable changes:
- Skill-first template refactor (700e7d3): 14 platforms unified under common/
- Claude hooks migrated to shared-hooks/ (4476844): 4 hook files relocated
- Sub-agent rename + model: opus drop (79801ed): trellis-* prefix on 30 agents
- Multi-agent pipeline removed (efccf6f): multi_agent/, worktree.yaml, phase.py deleted
- iFlow platform deleted, Factory Droid added
- Workflow enforcement v2 (c5387df): UserPromptSubmit replaces SubagentStop
- Task lifecycle: init-context dropped (9b92941), planning→in_progress on start (50149f4)
- Migration system: 15 new manifests, beta.0 has 206 breaking ops

Conflicts expected in:
- overlays/hiskens/templates/claude/hooks/* (overlay still ships there; upstream moved them)
- overlays/hiskens/templates/claude/agents/*.md (overlay uses old names)
- overlays/hiskens/templates/trellis/scripts/common/{task.py,task_context.py,task_store.py}
- packages/cli/src/utils/overlay.ts (fork-only file; not touched by upstream — should auto-merge clean)
- packages/cli/src/cli/index.ts (overlay loader registration; small but load-bearing)

See .trellis/tasks/04-26-research-v0-5-0-beta-sync/findings/ for full Phase A/B/C plan."
```

### 2.3 Post-merge static verification

```bash
# Runs in the sync branch with merge applied
cd packages/cli
pnpm install   # in case package.json changed
pnpm run build 2>&1 | tail -30   # MUST succeed; if not, the merge dropped a file the loader needs

# TypeScript check
npx tsc --noEmit 2>&1 | tail -30

# Tests — expect a regression count from upstream's structural changes; don't panic, triage them
pnpm test 2>&1 | tail -50
```

**Triage policy for test failures**:

| Failure pattern | Likely cause | Action |
|---|---|---|
| `expected 624, got 487` test count drop | Upstream removed test files (windsurf.test.ts deleted, qoder.test.ts removed) | Confirm by `git log v0.4.0-beta.10..v0.5.0-beta.14 -- packages/cli/test/`. If matches, accept the new baseline. |
| `cannot find module '../utils/overlay'` | TS path resolution drift after merge | Open the failing test, check imports — overlay.ts is fork-private but must be reachable from `cli/index.ts` |
| `expected '\n', got '\r\n'` | Pitfall 3 (CRLF) | Fix per playbook step P3 (`.gitattributes`, `core.autocrlf=false`, force re-checkout) |
| New tests under `test/utils/project-detector.test.ts` failing | Polyrepo detection added; test environment may not expose sibling .git dirs | Investigate — these are upstream tests, may need fixture |
| All configurator tests failing simultaneously | Skill-first refactor pipeline broke at merge time | Roll back merge; merge file-by-file in smaller steps |

### 2.4 Conflict-resolution policy by file class

| File class | Default resolution |
|---|---|
| `packages/cli/src/templates/claude/hooks/*` (deleted upstream, untouched in fork) | **Accept upstream deletion** — files removed. Note: fork's own `.claude/hooks/` — that is the installed copy, not source. Untouched. |
| `packages/cli/src/templates/claude/agents/{check,implement,research}.md` (renamed to trellis-*) | **Accept upstream rename**. Fork's `overlays/hiskens/templates/claude/agents/{check,implement,research}.md` continues to mirror the OLD path until Phase C ports it. |
| `packages/cli/src/templates/trellis/scripts/multi_agent/*` (deleted upstream) | **Accept upstream deletion**. Overlay's mirror at `overlays/hiskens/templates/trellis/scripts/multi_agent/*` is untouched and will be re-decided in Phase C. |
| `packages/cli/src/utils/overlay.ts` (fork-only, no upstream change) | **No conflict expected**. If git reports one, investigate immediately — it likely means fork branch picked up upstream history that diverges from our base. |
| `packages/cli/src/cli/index.ts` (both sides changed) | **Manual merge**. Keep fork's overlay-loader registration block (the `if (cliFlag === 'hiskens') { … }` injection) and accept upstream's other changes. |
| `packages/cli/src/configurators/*` (all rewritten upstream) | **Accept upstream verbatim**. Overlay does not customize configurators. |
| `packages/cli/src/migrations/manifests/0.5.0-beta.*.json` (15 new files) | **Accept upstream verbatim**. New files; no fork conflict. |
| `packages/cli/src/types/ai-tools.ts` (iFlow→droid) | **Accept upstream**. `overlays/hiskens/overlay.yaml` `dev_types` is a different concept — unaffected. |
| Root `.gitignore`, `package.json`, `pnpm-lock.yaml` | Manual merge — fork-only entries (RTK, hiskens overlay packaging) must survive. |

### 2.5 First commit point

After resolving conflicts, **do not yet** modify any `overlays/hiskens/templates/*` files. Commit the merge first:

```bash
git status   # zero unmerged paths
git add -A
git commit  # uses the prepared merge commit message
```

Then proceed to Phase B.

---

## 3. Phase B — Drift Detection (DUAL SCOPE — both required)

### 3.1 Narrow scope: "what upstream changed in the merge window"

```bash
MERGE_BASE=$(git merge-base HEAD^1 HEAD^2)   # = 737f750 (v0.4.0-beta.10)
echo "Merge base: $MERGE_BASE"

# All upstream-touched files
git diff --name-only $MERGE_BASE v0.5.0-beta.14 > /tmp/sync-v0.5.0/upstream-changed.txt
wc -l /tmp/sync-v0.5.0/upstream-changed.txt   # expect 625

# Filtered to template-mirror candidates only
grep '^packages/cli/src/templates/' /tmp/sync-v0.5.0/upstream-changed.txt \
  > /tmp/sync-v0.5.0/upstream-changed-templates.txt
wc -l /tmp/sync-v0.5.0/upstream-changed-templates.txt
```

### 3.2 Mirror-hit probe

```bash
# For each upstream template change, does overlay shadow that path?
while read f; do
  rel="${f#packages/cli/src/templates/}"
  overlay="overlays/hiskens/templates/$rel"
  if [ -f "$overlay" ]; then
    echo "MIRROR_HIT  $rel"
  fi
done < /tmp/sync-v0.5.0/upstream-changed-templates.txt | sort \
  > /tmp/sync-v0.5.0/mirror-hits.txt
cat /tmp/sync-v0.5.0/mirror-hits.txt
```

**Expected output (predicted by Agent 3's CRITICAL+HIGH lists, 35+10 = ~45 hits)**:
- `claude/agents/{check,debug,dispatch,implement,plan,research}.md` (6)
- `claude/commands/trellis/{brainstorm,break-loop,check,check-cross-layer,create-command,finish-work,integrate-skill,onboard,parallel,record-session,start,update-spec}.md` (12)
- `claude/hooks/{session-start,inject-subagent-context,statusline,ralph-loop}.py` (4)
- `claude/settings.json` → `claude/settings.overlay.json` mismatch (the overlay path is renamed, so basename grep won't match — verify manually)
- `codex/agents/{check,implement,research}.toml` (3)
- `codex/hooks.json`, `codex/hooks/session-start.py` (2)
- `trellis/scripts/{task.py, multi_agent/*}` (~7)
- `trellis/scripts/common/{cli_adapter,config,git_context,task_context,task_store,types}.py` (6)
- `trellis/config.yaml`, `trellis/worktree.yaml` (2)

### 3.3 Migration-manifest path-collision probe

The migration system was added upstream and is the **most-overlooked** conflict surface — manifests can rename or delete files that overlay still ships. Run:

```bash
# Extract every path mentioned in 0.5.0-beta.* migration manifests
mkdir -p /tmp/sync-v0.5.0/manifest-paths
for f in packages/cli/src/migrations/manifests/0.5.0-beta.*.json; do
  python3 -c "
import json
d = json.load(open('$f'))
for m in d.get('migrations', []):
    if 'from' in m: print(m['from'])
    if 'to' in m:   print(m['to'])
    if 'path' in m: print(m['path'])
" 2>/dev/null
done | sort -u > /tmp/sync-v0.5.0/manifest-paths/all.txt

wc -l /tmp/sync-v0.5.0/manifest-paths/all.txt   # ≈ 200+ unique paths

# Cross-reference: which manifest paths are also overlay-shadowed?
while read p; do
  # Manifests use INSTALLED paths (.claude/..., .trellis/...) not src/templates/ paths
  # Map back: .claude/agents/foo.md ↔ overlays/hiskens/templates/claude/agents/foo.md
  rel="$p"
  if [[ "$p" == .claude/* ]]; then rel="claude/${p#.claude/}"; fi
  if [[ "$p" == .trellis/* ]]; then rel="trellis/${p#.trellis/}"; fi
  overlay="overlays/hiskens/templates/$rel"
  if [ -f "$overlay" ]; then
    echo "MANIFEST_HITS_OVERLAY  $p  →  $overlay"
  fi
done < /tmp/sync-v0.5.0/manifest-paths/all.txt > /tmp/sync-v0.5.0/manifest-overlay-collisions.txt

# Each line in this file is a downstream consumer that, after running `trellis migrate`, will have
# the listed file deleted/renamed — even if overlay still expects to ship to that path.
cat /tmp/sync-v0.5.0/manifest-overlay-collisions.txt
```

### 3.4 Broad scope: "total overlay-vs-upstream drift right now"

This catches the cumulative drift Agent 3 already enumerated, but reproduce it on the post-merge tree to verify nothing was lost in the merge:

```bash
mkdir -p /tmp/sync-v0.5.0/broad
find overlays/hiskens/templates -type f \
  \( -name '*.py' -o -name '*.md' -o -name '*.json' -o -name '*.toml' -o -name '*.yaml' \) \
  -not -name '*.pyc' \
  -not -path '*/__pycache__/*' \
  | while read overlay; do
    rel="${overlay#overlays/hiskens/templates/}"
    upstream="packages/cli/src/templates/$rel"
    if [ ! -f "$upstream" ]; then
      echo "OVERLAY_ONLY    $rel"
      continue
    fi
    if cmp -s "$overlay" "$upstream"; then
      echo "BYTE_IDENTICAL  $rel"
      continue
    fi
    delta=$(diff "$overlay" "$upstream" 2>/dev/null | grep -cE '^[<>]')
    ovl=$(wc -l < "$overlay")
    ups=$(wc -l < "$upstream")
    echo "DRIFT  $rel  ovl=${ovl}L  ups=${ups}L  diff=${delta}L"
  done | sort > /tmp/sync-v0.5.0/broad/all.txt

# Summary
awk '{print $1}' /tmp/sync-v0.5.0/broad/all.txt | sort | uniq -c
```

**Expected distribution** (matches Agent 3 classification map):
- `OVERLAY_ONLY`: ~112 entries (hiskens-specific scientific-computing content)
- `DRIFT`: ~24 entries (APPEND files, both HIGH and MEDIUM)
- `BYTE_IDENTICAL`: ~2 entries (BASELINE files, candidates to drop from overlay)

### 3.5 New-upstream-file classification (BASELINE/APPEND/EXCLUDE)

Per `MAINTENANCE.md`, every NEW upstream file requires explicit classification:

```bash
# Files that exist at v0.5.0-beta.14 but did NOT exist at v0.4.0-beta.10
git diff --diff-filter=A --name-only v0.4.0-beta.10..v0.5.0-beta.14 \
  -- packages/cli/src/templates/ \
  > /tmp/sync-v0.5.0/upstream-new-files.txt
wc -l /tmp/sync-v0.5.0/upstream-new-files.txt
cat /tmp/sync-v0.5.0/upstream-new-files.txt
```

Then for each, write a 1-line decision (BASELINE / APPEND / EXCLUDE) into a worksheet:
```
packages/cli/src/templates/common/commands/start.md            BASELINE
packages/cli/src/templates/common/commands/finish-work.md      APPEND  (port hiskens record-session merger; spec/python/matlab refs)
packages/cli/src/templates/common/skills/check.md              APPEND  (Python/MATLAB lint commands; bug-pattern table)
…
packages/cli/src/templates/shared-hooks/inject-workflow-state.py  EXCLUDE  (overlay's enforcement is via Ralph-loop replacement; decide whether to ship at all)
…
```

If `EXCLUDE`, append the path to `overlays/hiskens/exclude.yaml` with a comment.

### 3.6 Hook-command + model audit (Pitfall 9 echo)

Even though this is fork-internal, run the audit on overlay sources too:

```bash
grep -HnE '^\s*command:' overlays/hiskens/templates/claude/agents/*.md \
  overlays/hiskens/templates/codex/agents/*.toml 2>/dev/null
# Expect: every `command:` line uses 'rtk hook claude' (no absolute paths)

grep -HnE '^model:' overlays/hiskens/templates/claude/agents/*.md \
  overlays/hiskens/templates/codex/agents/*.toml 2>/dev/null
# Expect: every line is 'opus[1m]' (overlay convention)
```

Issue from upstream change: upstream `79801ed` **dropped `model: opus` hardcoding** from all upstream agents. Overlay convention is to **pin `opus[1m]`**. Phase C must preserve this.

### 3.7 Drift triage (3-tier from playbook)

For every entry in `mirror-hits.txt` ∪ `manifest-overlay-collisions.txt` ∪ `broad/all.txt` DRIFT lines:

| Tier | Symptom | Action in Phase C |
|---|---|---|
| 🟢 Customization | overlay ≫ upstream (many added lines), overlay-specific concept (Nocturne, RTK, scientific computing, dev_type=python\|matlab) | KEEP — port only the upstream non-conflicting changes |
| 🟡 Attribution noise | 1–10 line diff, `# Ported from upstream` headers, blank lines, import order | KEEP — pure cosmetic |
| 🟠 Real missed sync | overlay has fewer lines than upstream, OR overlay has bug fix upstream re-fixed | INVESTIGATE — likely needs port |
| 🔴 New CRITICAL: upstream removed mirrored path | mirror file's upstream side gone | DECIDE: rename overlay (e.g. `check.md` → `trellis-check.md`), OR keep as overlay-only (debug.md, dispatch.md, plan.md), OR delete overlay (multi_agent/*) |

---

## 4. Phase C — Surgical Port

### 4.1 Must-keep list (overlay always wins)

For each, the rationale is a non-portable hiskens design choice:

| File | Must-keep | Reason |
|---|---|---|
| `overlay.yaml` | `dev_types: [python, matlab, both, trellis, test, docs]` | hiskens domain is scientific computing — backend/frontend/fullstack is incompatible |
| `overlay.yaml` | `compatible_upstream` (just bumped) | gate against re-running on pre-0.5 |
| `MAINTENANCE.md` | All BASELINE/APPEND/EXCLUDE rules | governs every future sync |
| `templates/trellis/spec/python/**` (all) | All overlay content | hiskens-specific scientific-computing spec corpus |
| `templates/trellis/spec/matlab/**` (all) | All overlay content | hiskens-specific scientific-computing spec corpus |
| `templates/trellis/spec/guides/**` (~17) | All overlay content unless byte-identical to upstream guide | most are hiskens-authored |
| `templates/trellis/scripts/init-nocturne-namespace.py` | All | Nocturne integration (overlay-only feature) |
| `templates/trellis/scripts/promote-to-nocturne.py` | All | Nocturne integration |
| `templates/trellis/scripts/sync-trellis-to-nocturne.py` | All | Nocturne integration |
| `templates/trellis/scripts/nocturne_client.py` | All | Nocturne integration |
| `templates/trellis/scripts/search/**` (4 files + API_CONFIG.md) | All | Grok/Tavily search wrappers (overlay-only) |
| `templates/claude/hooks/{todo-enforcer,intent-gate,context-monitor,parse_sub2api_usage,statusline-bridge}.py` | All | overlay-only behavioral hooks |
| `templates/claude/skills/grok-search/**`, `templates/claude/skills/github-explorer/**` | All | overlay-only skills |
| `templates/claude/settings.overlay.json` | overlay's `model` env, RTK env, Nocturne MCP, custom permission allowlist | merged on top of upstream `claude/settings.json` |
| `templates/codex/agents/codex-implement.toml` (overlay-only) | All | overlay-specific Codex sub-agent |
| All `.claude/agents/*.md` `model: opus[1m]` lines | always pin to `opus[1m]` | overlay convention, decided 2026-04 |
| All `.claude/agents/*.md` `command:` field | `rtk hook claude` (post-04-23) | overlay convention, P9 in playbook |

### 4.2 Must-port list (overlay needs an upstream-driven update)

Cross-referencing Agent 3's HIGH-risk table:

| Overlay file | Upstream change to port | Strategy |
|---|---|---|
| `claude/hooks/session-start.py` | shared-hooks rewrite — `_build_workflow_toc()`, `FIRST_REPLY_NOTICE`, `_has_curated_jsonl_entry()`, `configure_project_encoding()` | **Pattern 3 (full rewrite)**: take upstream `shared-hooks/session-start.py` as new base, graft Nocturne context + scientific-computing spec paths + LEGACY_MONOREPO_SPEC_MOVES on top. Then **relocate the file** in overlay tree from `claude/hooks/` to `shared-hooks/` (matches new upstream layout). |
| `claude/hooks/inject-subagent-context.py` | shared-hooks rewrite — `read_jsonl_entries` seed-row skip, `buildPullBasedPrelude` for Class-2 platforms | **Pattern 2 (helper port)**: copy upstream's seed-row skip and pull-based prelude functions, keep overlay-specific JSONL augmentation. Relocate to `shared-hooks/`. |
| `claude/hooks/statusline.py` | shared-hooks rewrite — Windows stream typed-detach fix (`192dabb`) | **Pattern 2**: tiny port. Relocate to `shared-hooks/`. Preserve `SEP = ` constant rename + `# noqa: N806`. |
| `claude/hooks/ralph-loop.py` | upstream **DELETED** | **DECIDE**: hiskens uses ralph-loop for completion-marker enforcement. Either (a) keep as overlay-only and document "upstream removed; we kept it" in MAINTENANCE.md, or (b) port the equivalent behavior into the new `inject-workflow-state.py` shared-hook. **Recommended (a)** for v0.5 round-1; revisit (b) in a follow-up task. |
| `claude/agents/{check,implement,research}.md` | upstream renamed to `trellis-{check,implement,research}.md`, dropped `model: opus` | **Rename overlay file + Pattern 3**: take upstream new file as base, graft `model: opus[1m]`, RTK `command: rtk hook claude`, Nocturne tools, completion markers. |
| `claude/agents/{debug,dispatch,plan,review,codex-implement}.md` | upstream **DELETED** all but their absence is silent (no manifest cleanup) | KEEP as overlay-only. They are extra hiskens agents; users not opting in are unaffected. Confirm overlay still installs them (verify `overlay.ts` registration includes the directory glob, not an enumerated list). |
| `claude/commands/trellis/{start,finish-work}.md` | upstream moved to `common/commands/{start,finish-work}.md` and uses `{{CMD_REF:x}}` placeholders | **Pattern 3**: take upstream new file as base, port hiskens additions: scientific-computing-aware brainstorm path, RTK installation note, Python/MATLAB dev type guidance. **Relocate** overlay from `claude/commands/trellis/` to `common/commands/`. |
| `claude/commands/trellis/{brainstorm,break-loop,check,update-spec}.md` | upstream moved to `common/skills/*.md` | **Pattern 3 + relocate** to `common/skills/`. |
| `claude/commands/trellis/check-cross-layer.md` | upstream **MERGED into check skill** | Decide: merge overlay's content into `common/skills/check.md` overlay version, OR keep `check-cross-layer.md` as overlay-only command. **Recommended**: merge into check skill (less file proliferation). |
| `claude/commands/trellis/{create-command,integrate-skill,onboard,parallel,record-session}.md` | upstream **DELETED** | KEEP overlay versions as overlay-only commands (some are hiskens-specific workflows). Confirm overlay loader still copies them. |
| `codex/agents/{check,implement,research}.toml` | upstream renamed to `trellis-*.toml`, sandbox_mode `read-only` → `workspace-write` for trellis-research | **Rename + Pattern 2**: rename overlay file basenames, graft sandbox_mode change. Preserve overlay-specific tool list and model. |
| `codex/hooks.json` | upstream added `UserPromptSubmit` hook with `inject-workflow-state.py` | **Pattern 1**: add the new hook entry. Preserve overlay's `PostToolUse` hook (overlay-only). |
| `codex/hooks/session-start.py` | major rewrite (Agent 3 ranked #2 hardest) | **Pattern 3**: same recipe as `claude/hooks/session-start.py` — upstream new base + Nocturne/spec grafts. |
| `trellis/scripts/task.py` | upstream removed `init-context` and `create-pr` commands; added `planning→in_progress` transition; added deprecation guard | **Pattern 3 (most complex)**: take upstream new base. Graft: `complete`/`set-status` commands, state machine constants, Nocturne learning promotion, Windows UTF-8 fix, `--reference` flag, dev_types `python\|matlab\|both\|trellis`. Specifically: do NOT graft `init-context` back even though hiskens used it — upstream's deprecation guard handles it; instead absorb the new `cmd_create` JSONL-seed path and adapt for hiskens dev_types. |
| `trellis/scripts/common/task_context.py` | upstream removed `cmd_init_context` + all default content generators | **Pattern 3 + redesign**: hiskens scientific-computing context generators move into `task_store.py` `_write_seed_jsonl()` extension. The standalone `task_context.py` shrinks to just helper functions. |
| `trellis/scripts/common/task_store.py` | upstream added `_has_subagent_platform`, `_write_seed_jsonl`, `_SUBAGENT_CONFIG_DIRS`, `_SEED_EXAMPLE` | **Pattern 2**: graft upstream's new helpers; preserve overlay's `cmd_complete`, `cmd_set_status`, `VALID_STATUS_TRANSITIONS`, Nocturne promotion. Reconcile `_SUBAGENT_CONFIG_DIRS` with hiskens platform set. |
| `trellis/scripts/common/cli_adapter.py` | upstream added `droid` platform; renamed Codex/Kiro skill paths to `trellis-{name}/` | **Pattern 1**: add `droid` branches in 5+ methods (consult upstream's exact list); update Codex/Kiro paths to `trellis-` prefix. Preserve overlay's existing customizations. Note: Round 1 of v0.4 sync (commit `04-15-overlay-drift-v0.4.0`) already added droid for v0.4 sync — verify whether that work is still in place or needs re-port. |
| `trellis/scripts/common/config.py` | upstream rewrote `parse_simple_yaml()` (inlined from worktree.py with `_unquote()`) | **Pattern 2**: take upstream's improved parser. Preserve overlay's `get_features()` function for ccr_routing/reference_support/etc. flags. |
| `trellis/scripts/common/git_context.py` | upstream added `--mode phase`, `--step`, `--platform` arguments | **Pattern 2 (trivial)**: graft new arguments. Drop overlay's `# noqa: F401` if no longer needed (or keep, low cost). |
| `trellis/scripts/common/types.py` | upstream removed `current_phase` and `next_action` from TaskData | **Pattern 1 (trivial)**: accept upstream verbatim. Overlay was already minimally diverged. |
| `trellis/config.yaml` | upstream added `git: true` for polyrepo | **Pattern 1**: add `git: true`; keep overlay's `session.spec_scope`, `features.{ccr_routing, reference_support, java_support, extra_platforms}` |
| `trellis/worktree.yaml` | upstream **DELETED** | DECIDE: hiskens overlay had a Python/MATLAB version (`1eef0ea` 2026-04). KEEP as overlay-only since downstream consumers (Anhui, Topo) reference it. Document in MAINTENANCE.md that `worktree.yaml` is now an overlay-only concept. |

### 4.3 Must-evaluate list (need maintainer judgement)

| Question | Recommendation (subject to maintainer override) |
|---|---|
| Onboard `antigravity` configurator into hiskens? | **No**. Antigravity is upstream-only; hiskens consumers haven't asked for it. EXCLUDE in `exclude.yaml`. |
| Onboard `droid` configurator? | **Yes** (already partially done in v0.4 sync). Confirm overlay's cli_adapter has droid branches and that overlay agents are written to `.factory/`. |
| Drop `iflow` from overlay's `dev_types` enumeration? | iFlow is removed upstream. Overlay's `dev_types` = `[python, matlab, both, trellis, test, docs]` doesn't reference iflow as a dev_type — they're orthogonal. **No change needed**, but check `cli_adapter.py` for stray iflow branches. |
| Onboard upstream's `common/skills/parallel.md`? | **Decide later**. Currently overlay ships `claude/commands/trellis/parallel.md` (overlay-only multi-agent dispatcher). Upstream's new `parallel.md` is different. Recommend keep overlay version as a different file under `common/skills/parallel.md` namespace; will need conflict-resolution rule in overlay loader. |
| Preserve overlay's `multi_agent/*.py` after upstream removed the directory? | **Yes for round 1**. Hiskens overlay loader still installs them; consumer Anhui has used them. Mark deprecated in MAINTENANCE.md, schedule removal for v0.6 sync. |
| `spec/guides/` files — port or overlay-only? | Overlay-only. The 17 files under `overlays/hiskens/templates/trellis/spec/guides/` are nearly all hiskens-authored. Only verify byte-identity check from broad-scope drift output. |
| `agents/skills/trellis-meta/` overlap with upstream marketplace `trellis-meta` skill? | **Investigate before merging**. Upstream commit `192cad0 chore(skill): import 4 marketplace skills` may have introduced a `trellis-meta` skill that conflicts with overlay's. Run `find . -path '*trellis-meta*' -type f` post-merge. |

### 4.4 Per-file porting recipe (4-step pattern)

For each must-port file, do not ad-hoc edit. Follow:

1. **Diff upstream change**: `git show v0.5.0-beta.14:<upstream_path> > /tmp/v5-<basename>.txt` and `git show v0.4.0-beta.10:<upstream_path> > /tmp/v4-<basename>.txt`. Then `diff /tmp/v4-<basename>.txt /tmp/v5-<basename>.txt > /tmp/upstream-delta-<basename>.diff`.
2. **Diff overlay vs upstream-v4**: `diff /tmp/v4-<basename>.txt overlays/hiskens/templates/<overlay_path> > /tmp/overlay-customization-<basename>.diff`. This is the hiskens-specific delta to preserve.
3. **Identify hunks to port**: open both diffs side-by-side. Hunks in `/tmp/upstream-delta-*` that don't conflict with `/tmp/overlay-customization-*` are mechanical ports. Hunks that conflict (touching same lines) need maintainer judgement.
4. **Apply manually**: edit the overlay file. After every edit:
   ```
   python3 -m py_compile overlays/hiskens/templates/<overlay_path>   # Python files
   # md/json/toml/yaml: visual review
   cd packages/cli && pnpm test 2>&1 | tail -10                       # tests stay green
   ```

---

## 5. Sandbox Validation

### 5.1 Setup

```bash
# Build CLI from sync branch
cd /home/hcx/github/Trellis_Hiskens/packages/cli
pnpm run build

# Spin up a clean sandbox consumer
SANDBOX=/tmp/trellis-v0.5.0-sandbox
rm -rf "$SANDBOX" && mkdir -p "$SANDBOX"
cd "$SANDBOX"
git init -q
echo '# sandbox' > README.md
git add . && git commit -qm 'init' --no-verify
```

### 5.2 P0 — `init` with overlay

```bash
# Verbose run; capture for log
node /home/hcx/github/Trellis_Hiskens/packages/cli/bin/trellis.js init \
  --overlay hiskens 2>&1 | tee /tmp/sandbox-init.log

# Expected:
# - .trellis/, .claude/ exist
# - .trellis/.version contains 0.5.0-beta.14
# - .trellis/spec/ has python/, matlab/, guides/ subdirectories
# - .claude/agents/ has trellis-{check,implement,research}.md (NOT plain check.md)
# - .claude/skills/ has trellis-* skill directories
# - shared-hooks files installed under .claude/hooks/ (or wherever the new layout lands)
# - overlay-only agents (debug, dispatch, plan, review, codex-implement) all present
# - .claude/skills/grok-search/, github-explorer/ present
# - .trellis/scripts/init-nocturne-namespace.py present
# - .trellis/worktree.yaml present (overlay-only after upstream removal)

# Smoke run get_context
python3 .trellis/scripts/get_context.py 2>&1 | head -30
# Expect: developer init prompt OR full context
```

### 5.3 P1 — `update` with overlay (forced re-sync)

```bash
# Modify an overlay-managed file in the sandbox to simulate user customization
echo '# user touch' >> .claude/agents/trellis-check.md

yes | node /home/hcx/github/Trellis_Hiskens/packages/cli/bin/trellis.js update \
  --overlay hiskens --create-new --migrate 2>&1 | tee /tmp/sandbox-update.log

# Triage .new files per Pitfall 0
for f in $(find . -name '*.new' -not -path './.git/*'); do
  real="${f%.new}"
  if cmp -s "$f" "$real"; then echo "FALSE-POS  $real"; rm "$f"; fi
done
```

### 5.4 P2 — Hook execution

```bash
cd "$SANDBOX"
# Trigger a Claude Code session via the hook (requires Claude binary)
claude code 'echo "hello from sandbox"' 2>&1 | head -20
# Expect: SessionStart hook fires with FIRST_REPLY_NOTICE, no tracebacks
```

### 5.5 P3 — Agent spawn + context injection

(deferred to first real session in sandbox; manual verification)

### 5.6 Rollback drill

```bash
cd /home/hcx/github/Trellis_Hiskens
git checkout main
git tag -d sync/upstream-v0.5.0-beta.14 2>/dev/null
git branch -D sync/upstream-v0.5.0-beta.14
# Backup tag remains: fork-pre-v0.5.0-sync-<date>
git rev-parse HEAD     # should equal pre-merge fork main
```

---

## 6. Risk Register

| # | Risk | Sev | Likelihood | Mitigation |
|---|---|---|---|---|
| 1 | `compatible_upstream` semver range "<0.5.0" rejects 0.5.0-beta.14 → overlay loader refuses | HIGH | Certain (already true) | First commit on sync branch bumps it (Phase A.2.1) |
| 2 | Migration manifest beta.0 (206 ops) deletes overlay-shipped files in downstream consumers running `trellis migrate` | HIGH | Certain | Phase B.3.3 manifest-overlay-collisions probe; document in MAINTENANCE.md which paths overlay re-ships |
| 3 | `claude/hooks/` deletion + relocation to `shared-hooks/` confuses overlay loader | HIGH | High | Verify `overlay.ts` directory globs; update overlay tree to mirror upstream's `shared-hooks/` location |
| 4 | Agent rename (trellis- prefix) breaks downstream consumers' tooling that expects old names | HIGH | Medium | Old agents (debug/dispatch/plan/review) kept as overlay-only; renamed agents use both names if needed |
| 5 | `task.py init-context` removal collides with overlay's hiskens dev_type seed logic | HIGH | High | `task_store.py` `_write_seed_jsonl` extension absorbs hiskens dev_types; deprecate overlay's `cmd_init_context` |
| 6 | `inject-workflow-state.py` (new) replaces ralph-loop; overlay's ralph-loop becomes orphan | MED | Certain | Decision: keep overlay ralph-loop OR replace with shared inject-workflow-state hook; document |
| 7 | New `antigravity` configurator silently leaks into hiskens consumers | MED | Medium | Add `antigravity` to `exclude.yaml`; verify in sandbox P0 |
| 8 | Windows `core.autocrlf=true` causes CRLF noise in 100s of file diffs after merge (Pitfall 3) | MED | Medium (WSL fork) | Already have `.gitattributes` with `eol=lf`; double-check after merge with `git ls-files --eol \| grep -v lf$` |
| 9 | Stack-overflow fix in `update.ts` backup phase still hits if backup tree is huge (no max depth) | LOW | Low | Upstream `d0e04ab` already uses iterative traversal; document in sandbox test |
| 10 | Tests drop from 624/624 to lower count due to upstream removing windsurf/qoder tests | LOW | Certain | Accept new baseline; document in commit message |
| 11 | `inject-subagent-context.py` Class-2 (Codex) pull-based prelude unfamiliar to hiskens overlay | MED | High | Phase C must port `buildPullBasedPrelude` and `_has_curated_jsonl_entry` |
| 12 | Overlay's hiskens `_SUBAGENT_CONFIG_DIRS` set out of sync with upstream's | MED | Medium | Reconcile in `task_store.py` port |
| 13 | New SessionStart `<first-reply-notice>` block alters expected agent output, breaking tests in consumers | LOW | Low | This is a one-shot per session; tolerable. Verify in sandbox P2. |
| 14 | Migration runner accidentally renames overlay-only files that share basename with upstream (e.g. `check.md`) | HIGH | Low | Migration manifest paths are full (`.claude/agents/check.md` → `trellis-check.md`); but overlay-only `check-cross-layer.md` etc may be misclassified. Audit per file. |
| 15 | Codex `sandbox_mode` change `read-only → workspace-write` for research agent breaks hiskens trust model | LOW | Low | Hiskens already pin model:opus[1m] and use rtk hooks; document but accept upstream change |

---

## 7. Rollback Plan

### Pre-merge rollback (anytime before sync branch commit)
```bash
git checkout main
git branch -D sync/upstream-v0.5.0-beta.14    # only if branch exists
# Backup tag still exists: fork-pre-v0.5.0-sync-<date>
```

### Post-merge rollback (after sync branch commit but before merge to main)
```bash
git checkout sync/upstream-v0.5.0-beta.14
git reset --hard HEAD~N                       # N = number of commits to undo
# OR: git reset --hard fork-pre-v0.5.0-sync-<date>
```

### Post-merge-to-main rollback (after FF-merge to main)
This is the most dangerous case. Do NOT force-push origin/main.
```bash
# Create a revert PR
git checkout main
git revert -m 1 <merge-commit-sha>            # -m 1 = keep original main, undo upstream merge
git push origin main:revert/upstream-v0.5.0
# Open PR for review; do not auto-merge
```

### Downstream consumer rollback (if `trellis update` was already run on Anhui/Topo)
Each consumer was synced on a feature branch (`trellis-overlay-resync-roundN`). To roll back:
```bash
cd /path/to/consumer
git checkout main
git branch -D trellis-overlay-resync-round5    # if not yet merged
# OR if merged via FF: git reset --hard <pre-merge-sha>; do NOT push
```
Document each consumer's pre-sync sha in the round PR body for forensic reference.

---

## 8. Time Estimate + Checkpoints

| Phase | Activity | Estimate (focused) | Cumulative |
|---|---|---|---|
| Pre-flight | Backup tag, working-tree audit, fetch, dist sanity | 0.5 h | 0.5 h |
| Phase A | Branch + relax compatible_upstream + merge + conflict resolve + tsc/test | 2–4 h | 2.5–4.5 h |
| Phase A | **CHECKPOINT 1** — review with maintainer before continuing | (reflection) | |
| Phase B narrow + manifest probes | Run all greps, generate worksheets | 1 h | 3.5–5.5 h |
| Phase B broad + new-file classification | Cross-reference 174 overlay files; write BASELINE/APPEND/EXCLUDE per new upstream file | 2 h | 5.5–7.5 h |
| Phase B | **CHECKPOINT 2** — present worksheets to maintainer; lock must-keep / must-port / must-evaluate decisions | (reflection) | |
| Phase C must-port (HIGH) | 18 must-port files × ~30 min each (some trivial, some complex) | 6–10 h | 11.5–17.5 h |
| Phase C must-port (MED) | 14 MEDIUM files, mostly review-only | 2–3 h | 13.5–20.5 h |
| Phase C | **CHECKPOINT 3** — Phase C complete, all py_compile clean, tests green | (reflection) | |
| Sandbox | P0 + P1 + manual P2/P3 + rollback drill | 2 h | 15.5–22.5 h |
| Docs | Update HISKENS.md, MAINTENANCE.md (new rules: shared-hooks layout, deprecated overlay-only categories) | 1 h | 16.5–23.5 h |
| Sandbox | **CHECKPOINT 4** — sandbox validated, ready to merge sync branch to fork main | (reflection) | |
| Merge to main | FF merge sync/upstream-v0.5.0-beta.14 → main; push origin (require maintainer approval) | 0.5 h | 17–24 h |
| Downstream sync round 5 | Separate task — propagate to Anhui_CIM, Topo-Reliability, baseline-main | 4–6 h | (separate task) |

**Honest read**: 17–24 hours of focused work over 3–5 calendar days, for the fork sync alone. Downstream propagation adds another half-day per consumer. Plan 1 working week end-to-end.

**Checkpoint policy**: Do not advance past checkpoints 1, 2, or 4 without explicit maintainer review. Checkpoint 3 is internal (test-pass gate).

---

## 9. Open Questions for the Maintainer

(Final decisions needed before executing Phase A)

1. **Sync target**: confirm `v0.5.0-beta.14` (recommended) vs wait for `v0.5.0` stable (delays sync indefinitely; not recommended).
2. **Overlay version bump 1.0.0 → 2.0.0**: agreed? semver-correct since shared-hooks relocation is a breaking change for consumers that reference `.claude/hooks/foo.py` directly.
3. **`compatible_upstream` floor**: bump to `>=0.5.0-beta.14` (locks consumers off lower betas) vs `>=0.5.0-beta.0` (accept any 0.5 beta)?
4. **`ralph-loop.py`**: keep as overlay-only (recommended) vs reimplement on top of upstream `inject-workflow-state.py`?
5. **`worktree.yaml`**: overlay continues to ship it? Anhui/Topo reference it. Recommended **yes**, document in MAINTENANCE.md.
6. **`multi_agent/*.py`**: overlay continues to ship it for Round 1? Recommended **yes**, mark deprecated, target removal in v0.6 sync.
7. **`debug.md`/`dispatch.md`/`plan.md`/`review.md`/`codex-implement.md` agents**: keep as overlay-only? Recommended **yes**, they're hiskens scientific-computing-aware extensions.
8. **`antigravity` configurator**: EXCLUDE in `exclude.yaml`? Recommended **yes**.
9. **`agents/skills/trellis-meta/` collision** with upstream's marketplace import (`192cad0`): need to investigate post-merge. May require additional surgery.
10. **First downstream consumer for v0.5 round 1**: Anhui_CIM (recommended; primary sync target) vs Topo-Reliability (secondary)?
11. **Migration timing**: should overlay-using consumers run `trellis migrate` (which executes the breaking-change beta.0 manifest) immediately, or stage it? Recommended: stage; first do `--create-new` with overlay, then run `--migrate` only after manifest collisions are documented.
12. **PR vs direct merge**: do you want a GitHub PR for the sync branch (recommended; gives diff-review surface) vs FF-merge directly?

---

## 10. Cross-references

- Master playbook: `.trellis/spec/guides/fork-sync-guide.md` (513 lines, 9 pitfalls)
- Topic map: `findings/01-topic-map.md` (511 lines, 14 open questions for downstream)
- Critical override engine analysis: `findings/02-critical-overrides.md`
- Per-file conflict map: `findings/03-overlay-conflict-map.md` (538 lines, classification table + per-file appendix)
- Last upstream sync archive: `.trellis/tasks/archive/2026-04/04-15-overlay-drift-v0.4.0/prd.md` (4 drift files, 3 actionable)
- Last downstream sync archive: `.trellis/tasks/archive/2026-04/04-23-downstream-sync-round4/prd.md` (Round 4/4b experience: P8/P9 lessons)
- Maintenance rules: `overlays/hiskens/MAINTENANCE.md` (BASELINE/APPEND/EXCLUDE classification)

---

## Notes on Agent Failures (for transparency)

This document was authored by the dispatcher after Agent 4 (the original playbook-adaptation agent) hit the Kimi 262K-token limit at 5556 seconds / 621 tool calls. Agent 2 also hit the same limit on its first run; Agent 2b (token-budgeted retry) succeeded with ≤55 tool calls.

**Two of Agent 2b's findings were verified to be incorrect** during ground-truth re-checking:
- "`overlay.ts` is GREEN because no upstream file exists" — true that no upstream file exists, but only because `overlay.ts` is **fork-private** (commit `ca4267d feat: add hiskens overlay templates and loader`). It is not in upstream at any version. Sync does not threaten the overlay engine.
- "beta.0 manifest has 138 safe-file-deletes that auto-execute without `--migrate`" — beta.0 manifest is `breaking: true` + `recommendMigrate: true`; the 206 ops (68 rename + 138 safe-file-delete) DO require explicit `--migrate` flag (or the breaking-change gate added in `2374433` blocks them). Verified by reading `commands/update.ts` flow.

These corrections are folded into Sections 2.3, 4.2, 6, and 9 of this document.
