# Research: Root-Level Platform Directory Audit

- **Query**: Audit root-level platform dirs (.claude/, .agents/, .codex/, .cursor/, .opencode/, .pi/) against upstream v0.5.0-beta.18
- **Scope**: internal
- **Date**: 2026-04-29

---

## Method

- Upstream reference: tag `v0.5.0-beta.18`
- HEAD reference: `migrate/hiskens-beta18` (committed state; uncommitted working-tree changes are in `overlays/` not platform dirs)
- File set obtained via `git ls-tree -r --name-only`
- Diff check via `git diff v0.5.0-beta.18..HEAD --name-only -- <shared-files>`
- Extra-file categorization: strip leading `.` from path and match against `overlays/hiskens/templates/` relative paths

---

## Part 1: Shared File Content Parity

**Result: ZERO differences.**

All 261 files that exist in both upstream beta.18 and HEAD are byte-identical (committed state). The `git diff` against the tag produces no output for shared files.

| Platform Dir | Shared Files (in both) | Content Differences |
|---|---|---|
| `.agents/` | 59 | **0** |
| `.claude/` | 138 | **0** |
| `.codex/` | 7 | **0** |
| `.cursor/` | 40 | **0** |
| `.opencode/` | 14 | **0** |
| `.pi/` | 11 | **0** |
| **Total** | **261** | **0** |

No upstream files are missing from HEAD either (0 deletions).

---

## Part 2: Extra Files (in fork HEAD but not in upstream beta.18)

Total extra files: **66**

### .agents/skills/ — 13 extra files

| File | Overlay Source? | Classification |
|---|---|---|
| `.agents/skills/brainstorm/SKILL.md` | YES (`agents/skills/brainstorm/SKILL.md`) | Overlay-injected |
| `.agents/skills/finish-work/SKILL.md` | YES (`agents/skills/finish-work/SKILL.md`) | Overlay-injected |
| `.agents/skills/improve-ut/SKILL.md` | YES (`agents/skills/improve-ut/SKILL.md`) | Overlay-injected |
| `.agents/skills/record-session/SKILL.md` | YES (`agents/skills/record-session/SKILL.md`) | Overlay-injected |
| `.agents/skills/before-dev/SKILL.md` | NO | Legacy — was in upstream v0.3.7–v0.5.0-beta.3; removed in beta.4 |
| `.agents/skills/break-loop/SKILL.md` | NO | Legacy — was in upstream v0.3.0–v0.5.0-beta.3; removed in beta.4 |
| `.agents/skills/check-cross-layer/SKILL.md` | NO | Legacy — was in upstream v0.3.0–v0.5.0-beta.3; removed in beta.4 |
| `.agents/skills/check/SKILL.md` | NO | Legacy — was in upstream v0.3.7–v0.5.0-beta.3; removed in beta.4 |
| `.agents/skills/create-command/SKILL.md` | NO | Legacy — was in upstream v0.3.0–v0.5.0-beta.3; removed in beta.4 |
| `.agents/skills/integrate-skill/SKILL.md` | NO | Legacy — was in upstream v0.3.0–v0.5.0-beta.3; removed in beta.4 |
| `.agents/skills/onboard/SKILL.md` | NO | Legacy — was in upstream v0.3.0–v0.5.0-beta.3; removed in beta.4 |
| `.agents/skills/start/SKILL.md` | NO | Legacy — was in upstream v0.3.0–v0.5.0-beta.3; removed in beta.4 |
| `.agents/skills/update-spec/SKILL.md` | NO | Legacy — was in upstream v0.3.0–v0.5.0-beta.3; removed in beta.4 |

### .claude/ — 21 extra files

#### agents/ — 6 extra

| File | Overlay Source? | Classification |
|---|---|---|
| `.claude/agents/check.md` | YES (`claude/agents/check.md`) | Overlay-injected (old name; upstream used it ≤ beta.5, renamed to trellis-check.md in beta.6) |
| `.claude/agents/debug.md` | YES (`claude/agents/debug.md`) | Overlay-injected (upstream had it beta.1–beta.3, removed beta.4) |
| `.claude/agents/dispatch.md` | YES (`claude/agents/dispatch.md`) | Overlay-injected (upstream had it beta.1–beta.3, removed beta.4) |
| `.claude/agents/implement.md` | YES (`claude/agents/implement.md`) | Overlay-injected (old name; upstream renamed to trellis-implement.md in beta.6) |
| `.claude/agents/plan.md` | YES (`claude/agents/plan.md`) | Overlay-injected (upstream had it beta.1–beta.3, removed beta.4) |
| `.claude/agents/research.md` | YES (`claude/agents/research.md`) | Overlay-injected (old name; upstream renamed to trellis-research.md in beta.6) |

#### commands/trellis/ — 13 extra

| File | Overlay Source? | Classification |
|---|---|---|
| `.claude/commands/trellis/brainstorm.md` | YES | Overlay-injected |
| `.claude/commands/trellis/break-loop.md` | YES | Overlay-injected |
| `.claude/commands/trellis/check-cross-layer.md` | YES | Overlay-injected |
| `.claude/commands/trellis/create-command.md` | YES | Overlay-injected |
| `.claude/commands/trellis/integrate-skill.md` | YES | Overlay-injected |
| `.claude/commands/trellis/onboard.md` | YES | Overlay-injected |
| `.claude/commands/trellis/parallel.md` | YES | Overlay-injected |
| `.claude/commands/trellis/record-session.md` | YES | Overlay-injected |
| `.claude/commands/trellis/start.md` | YES | Overlay-injected |
| `.claude/commands/trellis/update-spec.md` | YES | Overlay-injected |
| `.claude/commands/trellis/before-dev.md` | NO | Legacy — was in upstream v0.3.7–v0.5.0-beta.3; removed in beta.4 |
| `.claude/commands/trellis/check.md` | NO | Legacy — was in upstream v0.3.7–v0.5.0-beta.3; removed in beta.4 |
| `.claude/commands/trellis/commit.md` | NO | Legacy — was in upstream v0.3.7–v0.5.0-beta.0; removed in beta.1 |

#### hooks/ — 2 extra

| File | Overlay Source? | Classification |
|---|---|---|
| `.claude/hooks/ralph-loop.py` | YES (`claude/hooks/ralph-loop.py`) | Overlay-injected |
| `.claude/hooks/statusline.py` | YES (`claude/hooks/statusline.py`) | Overlay-injected |

### .codex/ — 4 extra files

| File | Overlay Source? | Classification |
|---|---|---|
| `.codex/agents/check.toml` | YES (`codex/agents/check.toml`) | Overlay-injected |
| `.codex/agents/implement.toml` | YES (`codex/agents/implement.toml`) | Overlay-injected |
| `.codex/agents/research.toml` | YES (`codex/agents/research.toml`) | Overlay-injected |
| `.codex/skills/parallel/SKILL.md` | NO | Legacy — was in upstream v0.4.0–v0.5.0-beta.3; removed in beta.4 |

### .cursor/ — 11 extra files

All 11 extra cursor commands are **NOT in overlay** and are **legacy files** removed from upstream in beta.4 or beta.15:

| File | Removed in Upstream | Classification |
|---|---|---|
| `.cursor/commands/trellis-brainstorm.md` | beta.4 | Legacy |
| `.cursor/commands/trellis-break-loop.md` | beta.4 | Legacy |
| `.cursor/commands/trellis-check-cross-layer.md` | beta.4 | Legacy |
| `.cursor/commands/trellis-check.md` | beta.4 | Legacy |
| `.cursor/commands/trellis-update-spec.md` | beta.4 | Legacy |
| `.cursor/commands/trellis-before-dev.md` | beta.4 | Legacy |
| `.cursor/commands/trellis-create-command.md` | beta.15 | Legacy |
| `.cursor/commands/trellis-integrate-skill.md` | beta.15 | Legacy |
| `.cursor/commands/trellis-onboard.md` | beta.15 | Legacy |
| `.cursor/commands/trellis-record-session.md` | beta.15 | Legacy |
| `.cursor/commands/trellis-start.md` | beta.15 | Legacy |

### .opencode/ — 17 extra files

All 17 extra opencode files are **NOT in overlay** and are legacy:

| File | Removed in Upstream | Classification |
|---|---|---|
| `.opencode/agents/check.md` | beta.6 | Legacy |
| `.opencode/agents/implement.md` | beta.6 | Legacy |
| `.opencode/agents/research.md` | beta.6 | Legacy |
| `.opencode/agents/debug.md` | beta.4 | Legacy |
| `.opencode/agents/dispatch.md` | beta.4 | Legacy |
| `.opencode/agents/trellis-plan.md` | beta.4 | Legacy |
| `.opencode/commands/trellis/create-command.md` | beta.15 | Legacy |
| `.opencode/commands/trellis/integrate-skill.md` | beta.15 | Legacy |
| `.opencode/commands/trellis/onboard.md` | beta.15 | Legacy |
| `.opencode/commands/trellis/parallel.md` | beta.15 | Legacy |
| `.opencode/commands/trellis/record-session.md` | beta.15 | Legacy |
| `.opencode/commands/trellis/start.md` | beta.15 | Legacy |
| `.opencode/commands/trellis/before-dev.md` | beta.4 | Legacy |
| `.opencode/commands/trellis/break-loop.md` | beta.4 | Legacy |
| `.opencode/commands/trellis/check-cross-layer.md` | beta.4 | Legacy |
| `.opencode/commands/trellis/check.md` | beta.4 | Legacy |
| `.opencode/commands/trellis/update-spec.md` | beta.4 | Legacy |

### .pi/ — 0 extra files

No extra files. Fully matches upstream.

---

## Part 3: Overlay Root Copy vs Overlay Template Source — Content Parity

The overlay-injected files in root dirs are **NOT byte-identical** to the current overlay template sources. Spot checks show significant divergence:

| Root File | Overlay Template | Status |
|---|---|---|
| `.agents/skills/brainstorm/SKILL.md` | `overlays/hiskens/templates/agents/skills/brainstorm/SKILL.md` | **DIFFER** — template has Step 7b (Engineering Depth Check), updated command refs (`$trellis:start` vs `$start`), updated lint commands |
| `.agents/skills/finish-work/SKILL.md` | `overlays/hiskens/templates/agents/skills/finish-work/SKILL.md` | **DIFFER** — template has Fresh Verification Gate, Steps 7/8/9 (task status, session reflection), Python-specific lint commands |
| `.agents/skills/record-session/SKILL.md` | `overlays/hiskens/templates/agents/skills/record-session/SKILL.md` | **DIFFER** — template has `--learning` flag, Nocturne memory step, simplified Step 1 |
| `.agents/skills/trellis-meta/SKILL.md` | `overlays/hiskens/templates/agents/skills/trellis-meta/SKILL.md` | **DIFFER** — template has multi-line description with Mindfold branding and trellis-local separation policy |

This means the root-level overlay files were installed from an **older version** of the overlay template source. The overlay template source has evolved since the last `trellis init`/sync was run on this repo.

---

## Summary Table: Extra File Categories

| Category | Count | Files |
|---|---|---|
| Overlay-injected (in `overlays/hiskens/templates/`) | **31** | .agents×4, .claude/agents×6, .claude/commands×10, .claude/hooks×2, .codex/agents×3 + check.toml×3 |
| Legacy (was in upstream, removed before beta.18) | **32** | See per-dir breakdowns above |
| **Pi has extras** | **0** | — |

Legacy files by the version they were removed:
- Removed in **beta.1**: `.claude/commands/trellis/commit.md` (1 file)
- Removed in **beta.4**: 24 files across .agents/, .claude/, .codex/, .cursor/, .opencode/
- Removed in **beta.6**: 3 .opencode/agents files
- Removed in **beta.15**: 7 files across .cursor/, .opencode/

---

## Caveats

1. **Uncommitted working-tree change**: `overlays/hiskens/templates/claude/skills/trellis-meta` has a working-tree modification (shown in `git status`). This has NOT been installed to the root `.claude/skills/trellis-meta/` yet.

2. **Overlay root copies are stale**: The 31 overlay-injected files present in root dirs are older versions of the overlay templates. They are functional but do not reflect current overlay template content. This is expected if the repo has not been re-initialized or synced since the overlay templates were updated.

3. **Legacy files are not from overlay**: The 32 legacy files were never in the overlay system — they are direct survivals from older upstream versions that predated the beta.4/beta.6/beta.15 cleanups. They exist because the ours-strategy merge preserved them from pre-fork history.

---

## Recommendation (per task description)

**Principle**: "non-overlay root content = upstream"

Based on that principle:

| Action | Files |
|---|---|
| **Delete** (legacy, not in overlay, not in upstream) | 32 legacy files across .agents/, .claude/, .codex/, .cursor/, .opencode/ |
| **Refresh** (re-install from current overlay template source) | 31 overlay-injected files that are stale relative to `overlays/hiskens/templates/` |
| **Keep as-is** (shared files, identical to upstream) | 261 files — no action needed |
| **Stage overlay working-tree change** | `overlays/hiskens/templates/claude/skills/trellis-meta` (1 dir with uncommitted changes) |
