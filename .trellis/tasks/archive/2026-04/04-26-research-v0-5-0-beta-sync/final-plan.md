# Trellis_Hiskens upstream sync v0.4.0-beta.10 → v0.5.0-beta.14

> Executive plan for the maintainer. Author: dispatcher (Hiskens session, 2026-04-26).
> Synthesizes 4 background research agents (1 + 2b succeeded; 2 and 4 hit Kimi 262K-token limits and were
> replaced by token-budgeted retries / dispatcher integration).

---

## TL;DR

- Upstream `v0.5.0-beta.14` is **a structural rewrite**, not a normal beta bump. **Templates dropped from 293 to 146 files (−50%).**
- The sync is **substantial but tractable**: 35 overlay files have their upstream mirror removed/renamed (CRITICAL), 10 need surgical port (HIGH), 14 are safe APPEND, ~112 are overlay-only.
- The **overlay engine itself is not at risk** — `packages/cli/src/utils/overlay.ts` is a fork-private file (`ca4267d`); upstream never had it. Disregard any earlier statement that "upstream removed overlay.ts."
- Estimated focused effort: **17–24 hours** spread across 3–5 calendar days. Downstream propagation to consumers (Anhui_CIM, Topo, baseline-main) is a separate follow-up task (~4–6 h per consumer).
- **Pre-merge gate**: `overlays/hiskens/overlay.yaml` declares `compatible_upstream: ">=0.4.0-beta.10 <0.5.0"`. This MUST be relaxed in the FIRST commit of the sync branch (before the merge), or the post-merge tree won't validate.

---

## What upstream actually did between v0.4.0-beta.10 and v0.5.0-beta.14

179 commits, 625 files changed. 8 themes, in priority order for overlay maintainer:

| # | Theme | Commit | Overlay impact |
|---|---|---|---|
| 1 | **Skill-first refactor** — all 14 platforms now consume from `common/` source of truth | `700e7d3` | CRITICAL — overlay's 20+ command files and 12+ skill files must align with new common/ system |
| 2 | **Claude hooks → shared-hooks** — `claude/hooks/` deleted (4 files), all hooks live in `shared-hooks/` | `4476844` | CRITICAL — overlay ships 9 hook files at the deleted path; relocate or replace |
| 3 | **Sub-agent rename + drop `model: opus`** — `implement.md` → `trellis-implement.md` etc; hardcoded model removed across 30 files in 10 platforms | `79801ed` | CRITICAL — overlay agents use old names; must rename + preserve `model: opus[1m]` (overlay convention) |
| 4 | **Workflow enforcement v2** — new `inject-workflow-state.py`, `UserPromptSubmit` replaces `SubagentStop` in settings.json | `c5387df` | HIGH — overlay's `claude/settings.overlay.json` must update |
| 5 | **Task lifecycle** — `task.py init-context` removed, jsonl seeded at create time, `planning → in_progress` transition | `9b92941`, `50149f4`, `8b75d9c` | HIGH — overlay's `task.py` and `task_context.py` need surgical port (overlay added `complete`/`set-status`, dev_types `python\|matlab\|both\|trellis`, Nocturne promotion) |
| 6 | **Multi-agent pipeline removed** — `multi_agent/`, `worktree.yaml`, `phase.py`, `registry.py`, `create_bootstrap.py` all deleted | `efccf6f`, `b323e93` | MED — overlay still ships these; recommendation: keep for round 1 (Anhui consumes them), schedule removal for v0.6 |
| 7 | **iFlow removed, Droid added** — Factory Droid is the new platform; iFlow gone | `efccf6f`, `0015246` | MED — overlay's `cli_adapter.py` already has droid (round-3 ports); verify still aligned. EXCLUDE upstream's new `antigravity` |
| 8 | **Migration system** — 15 new beta manifests, `beta.0` has 206 breaking ops (68 rename + 138 safe-file-delete), `--migrate` gate hard-stops | `403657d`, `2374433` | LOW for fork itself; HIGH for downstream consumers — they MUST use `--migrate` or the gate blocks update |

Full theme map: `findings/01-topic-map.md`. Per-file conflict map: `findings/03-overlay-conflict-map.md`. Override deep-dive: `findings/02-critical-overrides.md`. Adapted playbook: `findings/04-playbook-adaptation.md`.

---

## Recommended Execution Path (with checkpoints)

### Step 1 — Pre-flight (0.5 h)
Working tree clean, `git pull --ff-only origin main`, backup tag `fork-pre-v0.5.0-sync-<date>`, fork user-data digest snapshot, fetch upstream tags.

### Step 2 — Phase A: Safe Merge (2–4 h)
1. Branch `sync/upstream-v0.5.0-beta.14`
2. **First commit**: relax `overlay.yaml` `compatible_upstream` to `>=0.5.0-beta.14 <0.6.0`, bump overlay version to `2.0.0`, update `.upstream-version` and `HISKENS.md`.
3. **Second commit**: `git merge v0.5.0-beta.14 --no-ff` (NOT branch tip; pinned to immutable tag).
4. Resolve conflicts per file-class policy (Phase A.2.4 in `04-playbook-adaptation.md`).
5. `pnpm install && pnpm run build && pnpm test` — accept lower test count if upstream removed tests; investigate genuine failures.

> **Checkpoint 1**: Maintainer reviews merged tree before continuing. Agreed file-class policies?

### Step 3 — Phase B: Drift Detection (3 h)
1. **Narrow scope** + mirror-hit probe → `mirror-hits.txt`.
2. **Migration manifest path-collision** probe → `manifest-overlay-collisions.txt`. (This is unique to v0.5; v0.4 sync didn't have this surface.)
3. **Broad scope** drift probe → `broad/all.txt`.
4. **New-upstream-file classification** worksheet (BASELINE / APPEND / EXCLUDE) for files that didn't exist at v0.4.0-beta.10.
5. **Hook-command + model audit** (Pitfall 9 echo) on overlay sources.
6. **Drift triage** → 4 buckets (🟢 customization, 🟡 noise, 🟠 real, 🔴 critical-rename).

> **Checkpoint 2**: Present worksheets to maintainer; lock must-keep / must-port / must-evaluate decisions.

### Step 4 — Phase C: Surgical Port (8–13 h)
- **18 must-port files** (HIGH risk per Agent 3): includes the three hardest — `codex/hooks/session-start.py`, `trellis/scripts/task.py`, `trellis/scripts/common/task_context.py`. Per-file 4-step recipe: diff upstream change → diff overlay vs upstream-v4 → identify port hunks → apply manually + py_compile + tests.
- **14 MEDIUM files**: review-only or trivial port.
- **CRITICAL renamed files**: overlay basenames `check.md` → `trellis-check.md` etc. Locate file moves (`claude/hooks/*.py` → `shared-hooks/*.py`).
- **Decision-driven files**: `ralph-loop.py` (KEEP overlay-only recommended), overlay-only agents (KEEP), `worktree.yaml` (KEEP), multi_agent/ (KEEP for round 1, deprecate in v0.6).

> **Checkpoint 3**: All `py_compile` clean, `pnpm test` green, `grep command:` clean (rtk hook claude), `grep model:` clean (opus[1m]).

### Step 5 — Sandbox Validation (2 h)
- P0: `trellis init --overlay hiskens` in clean sandbox; verify trellis-* names, shared-hooks layout, overlay-only assets present.
- P1: `trellis update --overlay hiskens --create-new --migrate`; triage `.new` files per Pitfall 0.
- P2: hook smoke; P3: agent spawn (manual).
- Rollback drill.

### Step 6 — Documentation Update (1 h)
Update `HISKENS.md` (Based-on line), `overlays/hiskens/MAINTENANCE.md` (new shared-hooks rules, deprecated overlay-only categories, `worktree.yaml` is now overlay-only).

> **Checkpoint 4**: Sandbox validated, ready to FF-merge sync branch to fork main.

### Step 7 — Merge to main (0.5 h)
FF merge sync/upstream-v0.5.0-beta.14 → main. Push to `origin` only with maintainer approval.

### Step 8 — Downstream Round 5 (separate task)
Propagate to Anhui_CIM (primary), Topo-Reliability, baseline-main. Each consumer gets a `trellis-overlay-resync-round5` branch. Strict pre-flight: fork main is at the post-sync HEAD before downstream `trellis update`. Apply Pitfall 0 (.new triage), Pitfall 8 (fork at origin/main), Pitfall 9 (hook command audit) on every consumer.

---

## Critical Decisions Required from Maintainer (before Phase A)

These are blocking. Must decide first:

1. **Sync target**: `v0.5.0-beta.14` (recommended) vs wait for `v0.5.0` stable.
2. **Overlay version bump 1.0.0 → 2.0.0**: agree?
3. **`compatible_upstream` floor**: `>=0.5.0-beta.14 <0.6.0` (recommended)?
4. **`ralph-loop.py`**: overlay keeps as fork-only?
5. **`worktree.yaml`**: overlay keeps as fork-only after upstream removed it?
6. **`multi_agent/*.py`**: overlay keeps for round 1 (deprecation note in MAINTENANCE.md), removal targeted at v0.6?
7. **Overlay-only agents (debug, dispatch, plan, review, codex-implement)**: keep all?
8. **`antigravity` configurator**: add to overlay's `exclude.yaml`?
9. **First consumer for round 5**: Anhui_CIM (primary) vs Topo-Reliability?

Suggested defaults are noted in `04-playbook-adaptation.md` §9.

---

## Top 5 Risks (with mitigations)

| Risk | Mitigation |
|---|---|
| `compatible_upstream` blocks overlay loader on 0.5 base | Pre-merge bump in first commit (Step 2.2) |
| Migration manifest beta.0 deletes overlay-shipped files in consumers | Phase B.3 collision probe; document re-shipped paths in MAINTENANCE.md before allowing `--migrate` on consumers |
| `claude/hooks/` → `shared-hooks/` relocation breaks overlay loader's directory globs | Verify `overlay.ts` walks the directory tree (not enumerated paths) before merge; update overlay tree to mirror new layout |
| Agent rename (`trellis-` prefix) breaks consumer tooling that expects old names | Old agents (debug, dispatch, plan, review) kept as overlay-only; renamed agents preserve hiskens model + RTK hook lines |
| `task.py init-context` removal vs hiskens dev_type seed logic conflict | New seeding path goes through `task_store.py` `_write_seed_jsonl` extension; overlay drops standalone `cmd_init_context` |

Full register: `04-playbook-adaptation.md` §6.

---

## Key Ground-Truth Verifications (all confirmed by dispatcher post-agent)

| Claim | Verified by | Result |
|---|---|---|
| `claude/hooks/` deleted in v0.5 | `git ls-tree v0.5.0-beta.14 -- packages/cli/src/templates/claude/hooks/` | ✅ Empty (was 4 files at v0.4) |
| `shared-hooks/` exists with 5 files | `git ls-tree v0.5.0-beta.14 -- packages/cli/src/templates/shared-hooks/` | ✅ index.ts, inject-subagent-context.py, inject-workflow-state.py, session-start.py, statusline.py |
| Agent files `trellis-` prefixed and reduced to 3 | `git ls-tree v0.5.0-beta.14 -- packages/cli/src/templates/claude/agents/` | ✅ trellis-check.md, trellis-implement.md, trellis-research.md (down from 7) |
| `multi_agent/` directory deleted | `git ls-tree v0.5.0-beta.14 -- packages/cli/src/templates/trellis/scripts/multi_agent/` | ✅ Empty (was 9 files at v0.4) |
| `overlay.ts` fork-private (NOT upstream-deleted) | `git log --all --oneline -- packages/cli/src/utils/overlay.ts` → first appears at `ca4267d` (fork commit) | ✅ Always was fork-only; sync poses no engine-deletion risk |
| Migration manifest beta.0 = 206 ops, breaking | `jq` on `0.5.0-beta.0.json` | ✅ 68 rename + 138 safe-file-delete; `breaking: true`, `recommendMigrate: true`, requires `--migrate` |
| Other beta manifests are mostly empty | per-file aggregate | ✅ beta.5 = 30 rename (breaking), beta.9 = 4 safe-file-delete; 12 others = 0 ops |

---

## File Inventory (deliverables produced by this research)

```
.trellis/tasks/04-26-research-v0-5-0-beta-sync/
├── prd.md                                          # Research brief (this task)
├── final-plan.md                                   # ← THIS FILE (executive plan)
├── task.json
└── findings/
    ├── 01-topic-map.md                             (511 lines) Agent 1 — upstream theme map
    ├── 02-critical-overrides.md                    Agent 2b — engine + manifests + configurators
    ├── 03-overlay-conflict-map.md                  (538 lines) Agent 3 — per-file conflict classification
    ├── 04-playbook-adaptation.md                   ← Dispatcher — Phase A/B/C specialized
    ├── classification-v2.csv                        Agent 3 — full overlay classification CSV
    ├── upstream-v4-files.txt / upstream-v5-files.txt  Agent 3 — file-tree snapshots
    ├── overlay-files.txt / overlay-files-v2.txt    Agent 3 — overlay inventory
    └── scratch-03-classify*.sh                      Agent 3 — classification helper script
```

---

## When the maintainer is ready to start

1. Read `final-plan.md` (this file) end-to-end.
2. Walk through `04-playbook-adaptation.md` §1 (pre-flight) and §2 (Phase A).
3. Resolve the 9 critical decisions above (Section "Critical Decisions Required").
4. Create a new task: `python3 ./.trellis/scripts/task.py create "v0.5.0-beta.14 upstream sync" --slug upstream-sync-v0.5.0-beta.14` and link this PRD as the source brief.
5. Begin Step 1 (pre-flight). Stop at every checkpoint. Do not push to origin without explicit approval.
6. Round 5 downstream propagation is a follow-up task; reuse the round-4 archive PRD as a template (`.trellis/tasks/archive/2026-04/04-23-downstream-sync-round4/prd.md`).

---

## Acknowledgements

- Master playbook authored by prior maintainer in `.trellis/spec/guides/fork-sync-guide.md` (513 lines, 9 numbered pitfalls).
- Round-4 downstream sync archive (2026-04-23) provided P8 + P9 lessons that hardened this plan.
- Research agents 1 (topic map), 2b (token-budgeted retry of overrides), 3 (overlay conflict map) ran in parallel; agents 2 and 4 failed at Kimi token limits and were replaced or absorbed by the dispatcher.
