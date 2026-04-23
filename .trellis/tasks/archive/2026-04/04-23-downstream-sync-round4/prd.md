# Sync hiskens overlay v0.4.0 round 4 to downstream projects

**Type**: Ops / maintenance
**Scope primary**: `/mnt/e/Github/repo/Anhui_CIM`
**Scope secondary**: `/mnt/e/Github/repo/Topo-Reliability`
**Out of scope (this round)**: `baseline-main`, `AutoResearchClawFork`
**Upstream**: `Trellis_Hiskens` at HEAD `ef56d94` (v0.4.0 overlay aligned)

## Trigger

User request: "目前我定制化的 trellis 有很多修改了，是不是要同步到各个子项目中（主要是anhui项目）"

Commits since last archived sync (`abb5999`):

| Commit | Impact |
|---|---|
| `ef56d94` feat(hiskens): prefer /codex:adversarial-review + route subagents to opus[1m] | agents/{check,debug,dispatch,implement,plan,research,review}.md |
| `3d3f875` feat(hiskens): prefer grok MCP search and add statusline overlay | hooks/{statusline,statusline-bridge,parse_sub2api_usage}.py, skills/grok-search, skills/github-explorer, scripts/search/web_search.py, spec guides |
| `90e2906` docs(spec): fork-sync-guide additions | spec guide (docs-only, may or may not affect consumer projects) |

Overlay files changed in `abb5999..HEAD`: 19 files across agents/hooks/skills/scripts/guides.

## Goal

Propagate the 19 overlay file changes from Hiskens fork `ef56d94` into Anhui_CIM and Topo-Reliability while preserving:

1. All user data (`.trellis/tasks/`, `.trellis/workspace/`, `.trellis/spec/`, `.trellis/.developer`, `.trellis/.current-task`)
2. Project-local customizations (`.trellis/worktree.yaml`, `.trellis/.gitignore`, `.claude/settings.json`)
3. Executable bits on `.claude/hooks/*.py`, `.trellis/scripts/*.py`

## Preflight

- [x] HEAD = `ef56d94` verified clean
- [x] CLI dist fresh: no TS source newer than `packages/cli/dist/cli/index.js` (2026-04-15 21:59) → no rebuild needed
- [x] Overlay files read at runtime (per PRD fact #1 of previous sync task), no rebuild needed

## Execution plan

### Phase 1: Anhui_CIM (primary)

```bash
cd /mnt/e/Github/repo/Anhui_CIM
git status -sb                                 # must be clean
git checkout -b trellis-overlay-resync-round4

# digest (verify user data preserved)
mkdir -p /tmp/anhui-r4 && \
  find .trellis/tasks .trellis/workspace -type f \
    \( -name "*.md" -o -name "*.json" -o -name "*.jsonl" -o -name "*.yaml" \) \
    -print0 | sort -z | xargs -0 sha256sum > /tmp/anhui-r4/pre.sha256

# dry-run
yes | node /home/hcx/github/Trellis_Hiskens/packages/cli/bin/trellis.js update \
  --overlay hiskens --dry-run 2>&1 | tee /tmp/anhui-r4/dryrun.log

# execute with --create-new for non-destructive conflicts
yes | node /home/hcx/github/Trellis_Hiskens/packages/cli/bin/trellis.js update \
  --overlay hiskens --create-new 2>&1 | tee /tmp/anhui-r4/update.log
```

### Phase 2: Topo-Reliability

Same pattern; branch `trellis-overlay-resync-round4`, logs under `/tmp/topo-r4/`.

### Phase 3: Per-file conflict triage

For each `.new` file generated, run:

```bash
for f in $(find . -name '*.new' -not -path './.git/*' -not -path './.venv/*'); do
  real="${f%.new}"
  git_hash=$(git ls-tree HEAD -- "$real" 2>/dev/null | awk '{print $3}')
  new_hash=$(git hash-object "$f")
  if [ "$git_hash" = "$new_hash" ]; then
    echo "FALSE-POSITIVE (rm .new): $real"
    rm "$f"
  else
    echo "REAL-DIFF (decide): $real"
  fi
done
```

**Decision rules** (from Round 3 experience):

| File | Action |
|---|---|
| `.trellis/worktree.yaml` | Keep local (project-specific verify/copy) |
| `.trellis/.gitignore` | Keep local |
| `.claude/settings.json` | Keep local |
| Agent/hook/skill/spec-guide `.new` with real diff | Accept overlay (the whole point of this sync) |
| Whitespace-only or trailing-whitespace diff | Keep local, delete `.new` |

### Phase 4: Verify + commit

Per project:

```bash
# digest check (expect zero diff)
find .trellis/tasks .trellis/workspace -type f \
  \( -name "*.md" -o -name "*.json" -o -name "*.jsonl" -o -name "*.yaml" \) \
  -print0 | sort -z | xargs -0 sha256sum > /tmp/<proj>-r4/post.sha256
diff /tmp/<proj>-r4/pre.sha256 /tmp/<proj>-r4/post.sha256

# version
cat .trellis/.version

# exec bits
find .claude/hooks .trellis/scripts -name '*.py' -not -executable 2>&1

# lint (Anhui has uv, Topo has uv)
uv run ruff check . 2>&1 | tail -5

# commit
git add -A
git commit -m "chore(trellis): round 4 overlay resync (ef56d94: grok + opus-routing)"

# merge
git checkout main
git merge --ff-only trellis-overlay-resync-round4
```

## Acceptance criteria

- [ ] Anhui: `.new` files created, each triaged (accept/reject/false-positive), none remain
- [ ] Anhui: tasks+workspace digests unchanged
- [ ] Anhui: `.claude/hooks/statusline.py`, `statusline-bridge.py` byte-match overlay
- [ ] Anhui: `.claude/agents/{check,debug,implement,plan,research,review,dispatch}.md` have `model: opus[1m]` after sync
- [ ] Anhui: `.claude/skills/grok-search/SKILL.md` present + matches overlay
- [ ] Anhui: ruff check clean
- [ ] Anhui: branch committed and FF-merged to main
- [ ] Topo: same 7 bullets (substituting Topo-specific paths)
- [ ] Neither project's origin pushed (user decides)

## Execution log

(append-only)

### 2026-04-23

**Preflight surprise**: Local `main` at `ef56d94` was 4 commits behind
`origin/main = b8a4df7`. User had merged PR #1
(`overlay/rtk-integration-refresh`) on GitHub containing `eab133f`
(rtk hook claude migration) + `1eef0ea` (Python/MATLAB worktree.yaml
template) + `96111a0` (RTK-INTEGRATION docs), but hadn't pulled
locally. Caused sync to run in two passes (4 then 4b post-pull).

**Round 4 (Anhui, HEAD=ef56d94)**:
- Branch: `trellis-overlay-resync-round4`
- Backup: `.trellis/.backup-2026-04-23T09-35-17/`
- Dry-run: 6 auto-update + 11 .new files (after `--create-new`)
- Triage: 1 false-positive (_common.py.new), 3 keep-local
  (worktree.yaml, .gitignore, settings.json), 7 accept (overlay)
- Lint: 4 ruff errors, 3 autofixed, 1 N806 (SEP constant-style in
  statusline.py) resolved with inline noqa comment — fork source
  passes because fork has no pep8-naming ruleset, Anhui's
  pyproject.toml enables N select
- Commit: `c0fbffb chore(trellis): round 4 overlay resync
  (ef56d94 + 3d3f875)` — 11 files, +22 -32
- FF-merged to Anhui `main`

**Round 4b (Anhui, HEAD=b8a4df7 post-pull)**:
- Branch: `trellis-overlay-resync-round4b`
- Backup: `.trellis/.backup-2026-04-23T10-56-56/`
- Dry-run: 1 auto-update (new codex-implement.md) + 17 .new
- Triage: 3 false-positive-same, 1 NEW-FILE .gitignore (keep-local),
  13 real-diff → decomposed via LF-normalized diff:
  - 3 pure CRLF drift (parse_sub2api_usage.py, task_context.py,
    create_bootstrap.py) — reject
  - 3 always-keep-local (worktree.yaml, .gitignore, settings.json)
  - 1 local-patch-only (statusline.py: noqa preserved)
  - 7 real rtk migration (agents: check/debug/dispatch/implement/
    plan/research/review) — accept
- Commit: `c2d9243 chore(trellis): round 4b overlay resync
  (b8a4df7: rtk hook claude)` — 8 files, +8 -8
- FF-merged to Anhui `main`
- User data digest `cb4cbe52d3da...` byte-identical pre→post4→post4b

**Topo-Reliability: skipped (already in sync via parallel commits)**
- State: dirty tree with user's active work (notebooks, journals,
  memory) — do not touch
- Verified all 7 agents already use `rtk hook claude` (Topo's own
  `ffa9a0b fix(claude): migrate subagent rtk hooks` commit)
- All 7 agents already `model: opus[1m]` (Topo's `6dcbaf2
  docs(spec): prefer /codex:adversarial-review...`)
- statusline.py already has `SEP = ` rename
- grok-search skill present
- No substantive sync needed; any next sync would be CRLF noise

**Out-of-scope projects flagged for future decision**:
- `/mnt/e/Github/repo/baseline-main` — `.trellis/.version=0.4.0`,
  agents on old `rtk-rewrite.sh` path + `model: opus` (no `[1m]`).
  Needs sync, but has uncommitted benchmark output CSVs.
- `/home/hcx/github/AutoResearchClawFork` — no `.trellis/.version`,
  agents on `model: opus`, different hook structure (no `command:`
  field in check.md). Unclear Trellis/overlay state.

**Hiskens local commits vs origin**:
- Hiskens `main` is FF-updated from `ef56d94` → `b8a4df7` (no new
  local commits; just pulled origin)
- Anhui `main` is 2 commits ahead of origin (rounds 4 + 4b) +
  prior unpushed rounds — user pushes at discretion

**Lessons / new pitfalls for fork-sync-guide**:
- P8 (new): Always `git pull --ff-only origin main` in the fork
  repo BEFORE running a downstream sync. Remote PR merges are
  invisible to `git log` on the local main tip until pulled, and
  syncing from a stale HEAD silently ships partial overlay state.
- P9 (new): After `trellis update`, grep `grep -E "command:"
  .claude/agents/*.md` is a 2-second sanity check that catches rtk
  hook path migration state. If any agent still shows a hard-coded
  `/home/<user>/.claude/hooks/...` path, the sync is incomplete.
