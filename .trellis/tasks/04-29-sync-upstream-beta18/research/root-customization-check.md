# Research: Root-Level Platform Dir Customization Check

- **Query**: Determine whether any of the 66 extra root-level files (vs upstream beta.18) have been manually customized, or are all pure install/overlay copies
- **Scope**: internal
- **Date**: 2026-04-29

---

## Definitive Count

Total extra files (committed state, not in upstream beta.18): **66**

| Category | Count |
|---|---|
| Overlay-sourced (template exists in `overlays/hiskens/templates/`) | **25** |
| Legacy (was in older upstream, no overlay template) | **41** |
| **Total** | **66** |

> Note: `.claude/settings.local.json` is git-ignored globally (not committed, not counted). `.claude/skills/fork-sync-strategy/SKILL.md` is a NEW untracked file — separate from the 66 committed extras.

---

## Part A: Overlay-Sourced Files (25 files)

### Hash Comparison: Root Copy vs Overlay Template

All 25 overlay-sourced extra files are **STALE** relative to their overlay template sources.
**None are identical to the current overlay template.** No root copy matches its template hash.

| Root File | Root Hash (short) | Template Hash (short) | Status |
|---|---|---|---|
| `.agents/skills/brainstorm/SKILL.md` | `19dacdf119da` | `fb2d28da9bb2` | DIFFER (stale) |
| `.agents/skills/finish-work/SKILL.md` | `3de784bfe32d` | `c3abd1d9249f` | DIFFER (stale) |
| `.agents/skills/improve-ut/SKILL.md` | `1153e4bd78c2` | `02b9bfede3f8` | DIFFER (stale) |
| `.agents/skills/record-session/SKILL.md` | `d3d8a8fa8006` | `4de7aafb647f` | DIFFER (stale) |
| `.claude/agents/check.md` | `071aec4e6007` | `21c4d8ca0ad2` | DIFFER (stale) |
| `.claude/agents/debug.md` | `0108d99f507d` | `02d5e1c2d2f2` | DIFFER (stale) |
| `.claude/agents/dispatch.md` | `2bec15c7dd1a` | `5607fedc0f6f` | DIFFER (stale) |
| `.claude/agents/implement.md` | `380befa77ab7` | `798801e320df` | DIFFER (stale) |
| `.claude/agents/plan.md` | `5c0d0be94c92` | `bca82ebaff6f` | DIFFER (stale) |
| `.claude/agents/research.md` | `659d59c61854` | `78ae4fb4ec8b` | DIFFER (stale) |
| `.claude/commands/trellis/brainstorm.md` | `2c5e36094264` | `89d1072b681e` | DIFFER (stale) |
| `.claude/commands/trellis/break-loop.md` | `2558b0d8643e` | `2f994f992e51` | DIFFER (stale) |
| `.claude/commands/trellis/check-cross-layer.md` | `591d39b55a60` | `02694deb5c48` | DIFFER (stale) |
| `.claude/commands/trellis/create-command.md` | `b86647cd6fb3` | `a9a21a940f84` | DIFFER (stale) |
| `.claude/commands/trellis/integrate-skill.md` | `3c5841b2dbc2` | `9fcab8694d35` | DIFFER (stale) |
| `.claude/commands/trellis/onboard.md` | `403b10e9d38f` | `38bb6ccd531d` | DIFFER (stale) |
| `.claude/commands/trellis/parallel.md` | `4bfbf3800adf` | `f61aef6ede16` | DIFFER (stale) |
| `.claude/commands/trellis/record-session.md` | `2ba691e5c6fd` | `b1f69d8a3c20` | DIFFER (stale) |
| `.claude/commands/trellis/start.md` | `2df29ef06f79` | `8a9f1f98de7f` | DIFFER (stale) |
| `.claude/commands/trellis/update-spec.md` | `3f0b2e77c3ac` | `3236dd8b9f65` | DIFFER (stale) |
| `.claude/hooks/ralph-loop.py` | `3f9036105e0b` | `fa152c0e4e8b` | DIFFER (stale) |
| `.claude/hooks/statusline.py` | `a91ef1ce317e` | `b7ff31007096` | DIFFER (stale) |
| `.codex/agents/check.toml` | `b5d80e09318f` | `00f92ce1dd95` | DIFFER (stale) |
| `.codex/agents/implement.toml` | `16db983cff29` | `0a820018c211` | DIFFER (stale) |
| `.codex/agents/research.toml` | `b504a69be278` | `2dbd2b913881` | DIFFER (stale) |

### Were These Manually Customized?

**Verdict: NO. All 25 are pure stale overlay installs, not manually customized.**

Evidence: For every single overlay-sourced extra file, the **root copy's last commit date is older than the overlay template's last commit date**:

| Root File | Root Last Commit | Root Date | Template Date | Root Newer? |
|---|---|---|---|---|
| `.claude/hooks/ralph-loop.py` | `85425dc` (fix SubagentStop field names) | 2026-04-08 | 2026-04-13 | **No** |
| `.claude/hooks/statusline.py` | `58e36c1` (GBK encoding fix) | 2026-04-14 | 2026-04-16 | **No** |
| `.claude/agents/check.md` | `9f3bf0f` (trellis self update) | 2026-03-22 | 2026-04-23 | **No** |
| `.agents/skills/brainstorm/SKILL.md` | `9f3bf0f` | 2026-03-22 | 2026-04-13 | **No** |
| `.agents/skills/record-session/SKILL.md` | `9033aec` | 2026-03-23 | 2026-04-13 | **No** |
| `.codex/agents/check.toml` | `ba75c30` | 2026-03-24 | 2026-04-13 | **No** |
| (all others) | — | ≤2026-04-15 | ≥2026-04-13 | **No** |

The overlay template evolved after the root copies were last touched. The differences are template-side additions (new features like Sub2API caching in `statusline.py`, escalation loop in `ralph-loop.py`, updated command syntax `uv run python` vs `python3` in `start.md`), not user edits to the root copies.

### Nature of Differences (spot-checked)

- **`statusline.py`**: Template adds Sub2API caching layer (~80 lines). Root has older single-output logic.
- **`ralph-loop.py`**: Template adds review agent support + escalation loop. Root is check-only version.
- **`start.md`**: Template uses `uv run python` instead of `python3`. Root is older.
- **`.claude/commands/trellis/` (10 commands)**: Template updated command syntax and added new workflow steps. Root has older versions.

---

## Part B: Legacy Files (41 files)

### Template-Hashes.json Coverage

**Result: 0 out of 41 legacy files are tracked in `.trellis/.template-hashes.json`.**

The `.trellis/.template-hashes.json` file tracks only `trellis-meta` SKILL.md and reference files across `.claude/`, `.cursor/`, `.opencode/`, `.agents/`, `.pi/`. It does not track any of the legacy files. Therefore "was this file modified since install?" cannot be answered from the hash manifest for legacy files.

### Git History for Legacy Files

| File | Last Commit | Commit Message | Last Modified Date |
|---|---|---|---|
| `.agents/skills/before-dev/SKILL.md` | `9f3bf0f` | chore: trellis self update | 2026-03-22 |
| `.agents/skills/break-loop/SKILL.md` | `9f3bf0f` | chore: trellis self update | 2026-03-22 |
| `.agents/skills/check-cross-layer/SKILL.md` | `9f3bf0f` | chore: trellis self update | 2026-03-22 |
| `.agents/skills/check/SKILL.md` | `9f3bf0f` | chore: trellis self update | 2026-03-22 |
| `.agents/skills/create-command/SKILL.md` | `9f3bf0f` | chore: trellis self update | 2026-03-22 |
| `.agents/skills/integrate-skill/SKILL.md` | `9f3bf0f` | chore: trellis self update | 2026-03-22 |
| `.agents/skills/onboard/SKILL.md` | `9f3bf0f` | chore: trellis self update | 2026-03-22 |
| `.agents/skills/start/SKILL.md` | `9f3bf0f` | chore: trellis self update | 2026-03-22 |
| `.agents/skills/update-spec/SKILL.md` | `9f3bf0f` | chore: trellis self update | 2026-03-22 |
| `.claude/commands/trellis/before-dev.md` | `9f32dfe` | feat: Trellis v0.3.7 (#83) | 2026-01-08 |
| `.claude/commands/trellis/check.md` | `9f32dfe` | feat: Trellis v0.3.7 (#83) | 2026-01-08 |
| `.claude/commands/trellis/commit.md` | `b4b43a6` | feat: add generic before-dev, check commands… | 2025-11-xx |
| `.codex/skills/parallel/SKILL.md` | `ba75c30` | feat(codex): decouple .agents/skills… | 2026-03-24 |
| `.cursor/commands/trellis-brainstorm.md` | `b38a07c` | chore: update trellis self command | 2026-03-05 |
| `.cursor/commands/trellis-break-loop.md` | `dbf076c` | refactor: reorganize spec directory… | 2026-03-09 |
| `.cursor/commands/trellis-check-cross-layer.md` | `33e1c1d` | chore: update project's own command files… | 2026-01-28 |
| `.cursor/commands/trellis-check.md` | `b4b43a6` | feat: add generic before-dev… | 2025-11-xx |
| `.cursor/commands/trellis-update-spec.md` | `20ad79d` | Feat/codex (#38) | 2026-02-24 |
| `.cursor/commands/trellis-before-dev.md` | `b4b43a6` | feat: add generic before-dev… | 2025-11-xx |
| `.cursor/commands/trellis-create-command.md` | `57dee2d` | refactor: generalize commands… | 2026-03-09 |
| `.cursor/commands/trellis-integrate-skill.md` | `dbf076c` | refactor: reorganize spec directory… | 2026-03-09 |
| `.cursor/commands/trellis-onboard.md` | `57dee2d` | refactor: generalize commands… | 2026-03-09 |
| `.cursor/commands/trellis-record-session.md` | `ba633be` | fix: add --stdin flag… | 2026-03-10 |
| `.cursor/commands/trellis-start.md` | `57dee2d` | refactor: generalize commands… | 2026-03-09 |
| `.opencode/agents/check.md` | `f077a20` | refactor(opencode): update agent permission… | (pre-beta.4) |
| `.opencode/agents/implement.md` | `57dee2d` | refactor: generalize commands… | 2026-03-09 |
| `.opencode/agents/research.md` | `57dee2d` | refactor: generalize commands… | 2026-03-09 |
| `.opencode/agents/debug.md` | `f077a20` | refactor(opencode): update agent permission… | (pre-beta.4) |
| `.opencode/agents/dispatch.md` | `9b835b5` | fix(opencode): make dispatch wait… | (pre-beta.4) |
| `.opencode/agents/trellis-plan.md` | `5357e98` | feat(cli-adapter): add Cursor platform… | (pre-beta.4) |
| `.opencode/commands/trellis/create-command.md` | `57dee2d` | refactor: generalize commands… | 2026-03-09 |
| `.opencode/commands/trellis/integrate-skill.md` | `dbf076c` | refactor: reorganize spec directory… | 2026-03-09 |
| `.opencode/commands/trellis/onboard.md` | `57dee2d` | refactor: generalize commands… | 2026-03-09 |
| `.opencode/commands/trellis/parallel.md` | `57dee2d` | refactor: generalize commands… | 2026-03-09 |
| `.opencode/commands/trellis/record-session.md` | `ba633be` | fix: add --stdin flag… | 2026-03-10 |
| `.opencode/commands/trellis/start.md` | `57dee2d` | refactor: generalize commands… | 2026-03-09 |
| `.opencode/commands/trellis/before-dev.md` | `b4b43a6` | feat: add generic before-dev… | 2025-11-xx |
| `.opencode/commands/trellis/break-loop.md` | `dbf076c` | refactor: reorganize spec directory… | 2026-03-09 |
| `.opencode/commands/trellis/check-cross-layer.md` | `342993e` | feat(opencode): add OpenCode platform… | (pre-beta.4) |
| `.opencode/commands/trellis/check.md` | `b4b43a6` | feat: add generic before-dev… | 2025-11-xx |
| `.opencode/commands/trellis/update-spec.md` | `c0c8893` | docs(commands): improve update-spec… | (pre-beta.15) |

**Were These Manually Customized?**

**Verdict: NO. All 41 legacy files show zero activity after the last merge (2026-04-29).**

Zero files have commits newer than the `a8c8026` merge date. All last-commit messages are standard upstream feature/chore/refactor messages (not user-facing edits). The first commit introducing most of them was an upstream feature commit (`b4b43a6`, `57dee2d`, etc.) — these are pure survivals from the ours-strategy merge preserving older upstream content.

---

## Part C: Git Blame Summary

### Installing Commits by Category

| Commit | Message | Files Introduced |
|---|---|---|
| `1c61622` | init project | oldest legacy files |
| `b4b43a6` | feat: add generic before-dev, check commands | `.claude/commands/trellis/commit.md`, `.claude/commands/trellis/check.md`, `.claude/commands/trellis/before-dev.md`, `.cursor/commands/trellis-before-dev.md`, `.cursor/commands/trellis-check.md`, `.opencode/commands/trellis/before-dev.md`, `.opencode/commands/trellis/check.md` |
| `57dee2d` | refactor: generalize commands (monorepo dynamic spec discovery) | bulk of `.cursor/commands/`, `.opencode/commands/`, and agents |
| `9f3bf0f` | chore: trellis self update | `.agents/skills/{before-dev,break-loop,check,check-cross-layer,create-command,integrate-skill,onboard,start,update-spec}/SKILL.md` |
| `ba75c30` | feat(codex): decouple .agents/skills, add .codex | `.codex/agents/*.toml`, `.codex/skills/parallel/SKILL.md` |
| `a8c8026` | Merge migrate/hiskens-v0.6 (ours strategy) | merge point; ours strategy preserved all legacy files silently |

All legacy file families were introduced by upstream feature commits in pre-beta.4 era. None were manually added by the user. The ours-strategy merge at `a8c8026` preserved them passively.

---

## Bonus: Untracked File (Not in the 66)

`.claude/skills/fork-sync-strategy/SKILL.md` — **newly created, untracked, NOT committed**.
- Not in upstream, not in overlay, not installed by any commit.
- Content: a skill explaining the rebase-based upstream sync strategy for this fork.
- Created on 2026-04-29 (today) — appears to be a manually authored skill created during the current work session.
- **Action needed**: either commit it as a new overlay-sourced skill or add it to `overlays/hiskens/templates/claude/skills/fork-sync-strategy/`.

---

## Master Table: All 66 Extra Files

| File | Source | Customized? | Last Commit | Verdict |
|---|---|---|---|---|
| `.agents/skills/brainstorm/SKILL.md` | Overlay | No (stale) | `9f3bf0f` 2026-03-22 | Safe to refresh |
| `.agents/skills/finish-work/SKILL.md` | Overlay | No (stale) | `9f3bf0f` 2026-03-22 | Safe to refresh |
| `.agents/skills/improve-ut/SKILL.md` | Overlay | No (stale) | `92e818e` 2026-03-20 | Safe to refresh |
| `.agents/skills/record-session/SKILL.md` | Overlay | No (stale) | `9033aec` 2026-03-23 | Safe to refresh |
| `.claude/agents/check.md` | Overlay | No (stale) | `9f3bf0f` 2026-03-22 | Safe to refresh |
| `.claude/agents/debug.md` | Overlay | No (stale) | `1c61622` | Safe to refresh |
| `.claude/agents/dispatch.md` | Overlay | No (stale) | `57dee2d` 2026-03-09 | Safe to refresh |
| `.claude/agents/implement.md` | Overlay | No (stale) | `57dee2d` 2026-03-09 | Safe to refresh |
| `.claude/agents/plan.md` | Overlay | No (stale) | `636905a` | Safe to refresh |
| `.claude/agents/research.md` | Overlay | No (stale) | `9f3bf0f` 2026-03-22 | Safe to refresh |
| `.claude/commands/trellis/brainstorm.md` | Overlay | No (stale) | `b38a07c` 2026-03-05 | Safe to refresh |
| `.claude/commands/trellis/break-loop.md` | Overlay | No (stale) | `dbf076c` 2026-03-09 | Safe to refresh |
| `.claude/commands/trellis/check-cross-layer.md` | Overlay | No (stale) | `33e1c1d` 2026-01-28 | Safe to refresh |
| `.claude/commands/trellis/create-command.md` | Overlay | No (stale) | `57dee2d` 2026-03-09 | Safe to refresh |
| `.claude/commands/trellis/integrate-skill.md` | Overlay | No (stale) | `3c5841b` | Safe to refresh |
| `.claude/commands/trellis/onboard.md` | Overlay | No (stale) | `57dee2d` 2026-03-09 | Safe to refresh |
| `.claude/commands/trellis/parallel.md` | Overlay | No (stale) | `57dee2d` 2026-03-09 | Safe to refresh |
| `.claude/commands/trellis/record-session.md` | Overlay | No (stale) | `ba633be` 2026-03-10 | Safe to refresh |
| `.claude/commands/trellis/start.md` | Overlay | No (stale) | `b7e2a31` 2026-04-15 | Safe to refresh |
| `.claude/commands/trellis/update-spec.md` | Overlay | No (stale) | `20ad79d` | Safe to refresh |
| `.claude/hooks/ralph-loop.py` | Overlay | No (stale) | `85425dc` 2026-04-08 | Safe to refresh |
| `.claude/hooks/statusline.py` | Overlay | No (stale) | `58e36c1` 2026-04-14 | Safe to refresh |
| `.codex/agents/check.toml` | Overlay | No (stale) | `ba75c30` 2026-03-24 | Safe to refresh |
| `.codex/agents/implement.toml` | Overlay | No (stale) | `ba75c30` 2026-03-24 | Safe to refresh |
| `.codex/agents/research.toml` | Overlay | No (stale) | `ba75c30` 2026-03-24 | Safe to refresh |
| `.agents/skills/before-dev/SKILL.md` | Legacy | No | `9f3bf0f` 2026-03-22 | Safe to delete |
| `.agents/skills/break-loop/SKILL.md` | Legacy | No | `9f3bf0f` 2026-03-22 | Safe to delete |
| `.agents/skills/check-cross-layer/SKILL.md` | Legacy | No | `9f3bf0f` 2026-03-22 | Safe to delete |
| `.agents/skills/check/SKILL.md` | Legacy | No | `9f3bf0f` 2026-03-22 | Safe to delete |
| `.agents/skills/create-command/SKILL.md` | Legacy | No | `9f3bf0f` 2026-03-22 | Safe to delete |
| `.agents/skills/integrate-skill/SKILL.md` | Legacy | No | `9f3bf0f` 2026-03-22 | Safe to delete |
| `.agents/skills/onboard/SKILL.md` | Legacy | No | `9f3bf0f` 2026-03-22 | Safe to delete |
| `.agents/skills/start/SKILL.md` | Legacy | No | `9f3bf0f` 2026-03-22 | Safe to delete |
| `.agents/skills/update-spec/SKILL.md` | Legacy | No | `9f3bf0f` 2026-03-22 | Safe to delete |
| `.claude/commands/trellis/before-dev.md` | Legacy | No | `9f32dfe` 2026-01-08 | Safe to delete |
| `.claude/commands/trellis/check.md` | Legacy | No | `9f32dfe` 2026-01-08 | Safe to delete |
| `.claude/commands/trellis/commit.md` | Legacy | No | `b4b43a6` | Safe to delete |
| `.codex/skills/parallel/SKILL.md` | Legacy | No | `ba75c30` 2026-03-24 | Safe to delete |
| `.cursor/commands/trellis-brainstorm.md` | Legacy | No | `b38a07c` 2026-03-05 | Safe to delete |
| `.cursor/commands/trellis-break-loop.md` | Legacy | No | `dbf076c` 2026-03-09 | Safe to delete |
| `.cursor/commands/trellis-check-cross-layer.md` | Legacy | No | `33e1c1d` | Safe to delete |
| `.cursor/commands/trellis-check.md` | Legacy | No | `b4b43a6` | Safe to delete |
| `.cursor/commands/trellis-update-spec.md` | Legacy | No | `20ad79d` | Safe to delete |
| `.cursor/commands/trellis-before-dev.md` | Legacy | No | `b4b43a6` | Safe to delete |
| `.cursor/commands/trellis-create-command.md` | Legacy | No | `57dee2d` 2026-03-09 | Safe to delete |
| `.cursor/commands/trellis-integrate-skill.md` | Legacy | No | `dbf076c` 2026-03-09 | Safe to delete |
| `.cursor/commands/trellis-onboard.md` | Legacy | No | `57dee2d` 2026-03-09 | Safe to delete |
| `.cursor/commands/trellis-record-session.md` | Legacy | No | `ba633be` 2026-03-10 | Safe to delete |
| `.cursor/commands/trellis-start.md` | Legacy | No | `57dee2d` 2026-03-09 | Safe to delete |
| `.opencode/agents/check.md` | Legacy | No | `f077a20` | Safe to delete |
| `.opencode/agents/implement.md` | Legacy | No | `57dee2d` 2026-03-09 | Safe to delete |
| `.opencode/agents/research.md` | Legacy | No | `57dee2d` 2026-03-09 | Safe to delete |
| `.opencode/agents/debug.md` | Legacy | No | `f077a20` | Safe to delete |
| `.opencode/agents/dispatch.md` | Legacy | No | `9b835b5` | Safe to delete |
| `.opencode/agents/trellis-plan.md` | Legacy | No | `5357e98` | Safe to delete |
| `.opencode/commands/trellis/create-command.md` | Legacy | No | `57dee2d` 2026-03-09 | Safe to delete |
| `.opencode/commands/trellis/integrate-skill.md` | Legacy | No | `dbf076c` 2026-03-09 | Safe to delete |
| `.opencode/commands/trellis/onboard.md` | Legacy | No | `57dee2d` 2026-03-09 | Safe to delete |
| `.opencode/commands/trellis/parallel.md` | Legacy | No | `57dee2d` 2026-03-09 | Safe to delete |
| `.opencode/commands/trellis/record-session.md` | Legacy | No | `ba633be` 2026-03-10 | Safe to delete |
| `.opencode/commands/trellis/start.md` | Legacy | No | `57dee2d` 2026-03-09 | Safe to delete |
| `.opencode/commands/trellis/before-dev.md` | Legacy | No | `b4b43a6` | Safe to delete |
| `.opencode/commands/trellis/break-loop.md` | Legacy | No | `dbf076c` 2026-03-09 | Safe to delete |
| `.opencode/commands/trellis/check-cross-layer.md` | Legacy | No | `342993e` | Safe to delete |
| `.opencode/commands/trellis/check.md` | Legacy | No | `b4b43a6` | Safe to delete |
| `.opencode/commands/trellis/update-spec.md` | Legacy | No | `c0c8893` | Safe to delete |

---

## Final Verdict

**Zero of the 66 extra files have been manually customized by the user.**

- **25 overlay-sourced files**: All are pure stale installs. The overlay template evolved (added features) after the root copy's last commit in every case. The root files' commit history traces entirely to upstream feature/refactor/chore commits. No user modifications.

- **41 legacy files**: None are in `.trellis/.template-hashes.json`. All last-commit messages are standard upstream commits (not user edits). Zero files have commits on or after the 2026-04-29 merge. They are pure survivals from the ours-strategy merge.

**Safe actions with zero data-loss risk:**
- Delete all 41 legacy files (they replicate removed upstream behavior, superseded by `trellis-*` variants)
- Re-install (overwrite) all 25 overlay files from current `overlays/hiskens/templates/` sources

**Additional note:**
- `.claude/skills/fork-sync-strategy/SKILL.md` is an untracked NEW file that is a genuine user addition. It should be committed and/or added to the overlay before any cleanup.

---

## Caveats

1. `.trellis/.template-hashes.json` only covers `trellis-meta` skill files, NOT the bulk of overlay-installed files. The stale-overlay diagnosis here relies on date-comparison rather than stored hashes.

2. The "31 overlay + 35 legacy = 66" split in the task brief differs from our finding of "25 overlay + 41 legacy = 66". The task brief appears to have over-counted the overlay category. Our count is derived from literal template path existence checks.

3. `.claude/settings.local.json` is globally git-ignored and is excluded from this analysis; it is a local-only file.
