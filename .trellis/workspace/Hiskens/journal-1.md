# Journal - Hiskens (Part 1)

> AI development session journal
> Started: 2026-04-15

---



## Session 1: Upstream v0.4.0 sync + overlay drift resolution

**Date**: 2026-04-15
**Task**: Upstream v0.4.0 sync + overlay drift resolution
**Package**: cli
**Branch**: `sync/upstream-v0.4.0`

### Summary

(Add summary)

### Main Changes

## Scope

Full three-phase sync of `mindfold-ai/Trellis` v0.4.0 into the hiskens
fork, plus a fork-sync guide distilled from the experience. Ran as task
`04-15-overlay-drift-v0.4.0`, now archived.

## Phase A — Safe merge

| Step | Result |
|---|---|
| Fetch upstream (initial TLS failure, retried) | 32 new commits pulled incl. v0.4.0 release |
| Safety branch | `sync/upstream-v0.4.0` (not main) |
| Merge strategy | `git merge upstream/main --no-ff` — single merge commit `6ef8e5b` |
| Auto-merged files | 3 of 4 Tier-1 conflict candidates |
| Manual conflict | 1 file: `packages/cli/src/configurators/index.ts` — two imports collided, kept both + added missing `droid` entry to `PLATFORM_OVERLAY_TARGETS` Record |

## Pitfall hit during Phase A — autocrlf × YAML frontmatter

After merge, 3 tests failed on new droid command templates asserting
`startsWith("---\n")`. Root cause: global `core.autocrlf=true` converting
LF to CRLF in working tree while blobs remained LF. Fixed locally without
touching global config:

- Added `.gitattributes` enforcing `* text=auto eol=lf` + binary overrides
- `git config --local core.autocrlf false`
- `git rm --cached -r . && git reset --hard HEAD` to renormalize

Result: 624/624 tests green. Commit `525d9ac`.

## Phase B — Drift detection (dual scope)

First pass used narrow scope only (files changed in 32-commit window)
and found 4 drift candidates. User pushed back — "changelog has way more
stuff than that". Re-ran with broad scope (full overlay vs current
upstream diff) and found 52 drifted files. Classified:

| Tier | Count | Action |
|---|---|---|
| Customization (overlay > upstream, heavy hiskens features) | ~30 | KEEP |
| Attribution noise (1–10 line diff, `"""Ported from beta.7"""` headers) | ~10 | KEEP |
| Real missed sync | 4 | PORT (handled in Phase C) |
| Intentional philosophy difference (python/matlab vs backend/frontend) | ~8 | KEEP |

**Key finding**: hiskens overlay was created in `ca4267d` (2026-04-13),
4 days AFTER `v0.4.0-beta.10` tag. So all the big architectural changes
(monorepo, per-package specs, before-dev unification, .agents/skills,
Python script refactoring) were ALREADY inherited — only the final 32
commits of polish/bugfix had actionable drift.

## Phase C — Surgical port

**3 files ported in first implement pass** (task `04-15-overlay-drift-v0.4.0`):

| File | Changes | Guardrails held |
|---|---|---|
| `claude/hooks/session-start.py` | +31/−14 — `_build_workflow_toc()` TOC helper replaces full workflow.md injection | plain print() stdout preserved (NOT JSON envelope), nocturne/memory/thinking-framework/stale-session untouched |
| `codex/hooks/session-start.py` | +29/−14 — same TOC refactor + drop start-skill instructions block | simpler `_get_task_status` preserved |
| `trellis/scripts/common/cli_adapter.py` | +31/−5 — Factory Droid platform across 13 touch points | no windsurf/copilot added (deliberate scope) |

**4th file fixed in second pass** (scope extension to same task):

| File | Changes |
|---|---|
| `claude/commands/trellis/parallel.md` | Spec discovery: `cat python/matlab/index.md` → `get_context.py --mode packages` |

**start.md rewrite (Option C — full upstream base + graft)**:

After audit showed `start.md` had a silent behavioral regression
(hiskens rewrite dropped upstream's "execute ALL steps below without
stopping" directive), user chose to rebase it entirely on upstream v0.4.0
and graft minimal hiskens features.

Rewrite result: 325 → 429 lines, +246/−113 diff.
- Dropped: Step 1 Challenge & Reframe, research-before-task-create ordering,
  `frontend/backend/fullstack` terminology
- 9 MUST KEEP grafts applied verbatim: python/matlab terminology, memory
  status hint, python/matlab spec fallback examples, narrowed D3/ruff
  Check Agent, NEW Step 10 Semantic Review (review agent), review row
  in Sub Agents table, stale-session warning bullet, Python↔MATLAB
  Code-Spec Depth Check triggers, thinking-framework.md passive pointer
- Also deleted orphan `start-base.md` (zero references in repo)

**record-session.md**: small port (`--mode record` + archive judgment
guidance). Initial research claim that hiskens didn't support
`--mode record` turned out wrong — empirical test showed the flag works
via `common/git_context.py`. Research agent had only grepped the thin
15-line wrapper, missing the real implementation in the imported module.

## Spec capture — fork-sync-guide.md

Distilled the entire experience into a new thinking guide (337 lines,
`.trellis/spec/guides/fork-sync-guide.md`) covering:

- Three-Phase Workflow (Safe Merge / Drift Detection / Surgical Port)
- 5 Common Pitfalls (shallow grep, overlay vs installed templates,
  autocrlf × YAML, workflow file behavioral directives, narrow-scope-only)
- Decision heuristics table
- Anti-checklist

Also augmented `cross-platform-thinking-guide.md` with the autocrlf ×
YAML frontmatter pitfall, and registered the new guide in
`guides/index.md`.

## Final state

- **Branch**: `sync/upstream-v0.4.0`
- **Ahead of upstream v0.4.0**: 7 commits (fork customizations + sync work)
- **Behind upstream**: 0
- **Test suite**: 624/624 green throughout
- **TypeScript**: clean
- **Task**: `04-15-overlay-drift-v0.4.0` archived to `.trellis/tasks/archive/2026-04/`

## Updated Files (9 commits, this session)

**Phase A**:
- `6ef8e5b` merge: sync upstream v0.4.0 (32 upstream commits absorbed)
- `525d9ac` fix(repo): enforce LF line endings via .gitattributes

**Phase C ports**:
- `0cd76f6` fix(overlay): port upstream v0.4.0 hooks refactor + droid adapter
  - `overlays/hiskens/templates/claude/hooks/session-start.py`
  - `overlays/hiskens/templates/codex/hooks/session-start.py`
  - `overlays/hiskens/templates/trellis/scripts/common/cli_adapter.py`
- `560102b` fix(overlay): sync parallel.md spec discovery
  - `overlays/hiskens/templates/claude/commands/trellis/parallel.md`
- `b6b4afa` refactor(overlay): rewrite start.md on upstream v0.4.0 base
  - `overlays/hiskens/templates/claude/commands/trellis/start.md`
  - `overlays/hiskens/templates/claude/commands/trellis/start-base.md` (deleted)
- `1b660de` fix(overlay): sync record-session.md to --mode record + archive guidance
  - `overlays/hiskens/templates/claude/commands/trellis/record-session.md`

**Spec capture**:
- `c18d8c5` docs(spec): capture fork sync guide from v0.4.0 sync experience
  - `.trellis/spec/guides/fork-sync-guide.md` (NEW, +337)
  - `.trellis/spec/guides/cross-platform-thinking-guide.md` (+9)
  - `.trellis/spec/guides/index.md` (+10)

**Task metadata**:
- `67e0b88` chore(trellis): record overlay-drift-v0.4.0 task and sync report
- `1d4af6b` chore(task): archive 04-15-overlay-drift-v0.4.0

## Takeaways (for next upstream sync)

1. **Always use dual-scope drift detection** — narrow scope alone misses files the fork inherited from older upstream eras.
2. **Don't trust shallow grep** — when verifying feature support, follow the import chain to the leaf module. Better: just run the command empirically.
3. **Behavioral directives in workflow files are load-bearing** — before rewriting any agent-facing workflow file, grep upstream for imperative sentences ("execute ALL steps", "Do NOT ask", "without stopping") and explicitly decide port vs drop for each.
4. **`overlays/` is shipped to downstream consumers; `.claude/commands/` is the publisher's own installed copy** — editing overlay files does not change local skill behavior. Test overlay changes in a downstream sandbox project.
5. **Merge beats rebase for fork sync** — preserves hiskens big commits and concentrates conflicts into one merge commit.


### Git Commits

| Hash | Message |
|------|---------|
| `6ef8e5b` | (see git log) |
| `525d9ac` | (see git log) |
| `c18d8c5` | (see git log) |
| `0cd76f6` | (see git log) |
| `560102b` | (see git log) |
| `b6b4afa` | (see git log) |
| `1b660de` | (see git log) |
| `67e0b88` | (see git log) |
| `1d4af6b` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete
