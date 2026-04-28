# Research: Upstream v0.5.0-beta Sync Plan

## Goal
Investigate how to sync the **`overlays/hiskens/`** customization layer of `Trellis_Hiskens` (currently pinned to upstream `v0.4.0-beta.10`) onto the upstream `feat/v0.5.0-beta` branch (latest tag `v0.5.0-beta.14`). Produce a concrete, executable migration plan that the maintainer can drive after returning.

## Context Snapshot
- Fork repo: `/home/hcx/github/Trellis_Hiskens` (branch `main`, clean)
- Fork base commit (current `.upstream-version`): `737f7508` = `v0.4.0-beta.10`
- Upstream tip (`upstream/feat/v0.5.0-beta`): `f433ce5e`
- Upstream latest tag: `v0.5.0-beta.14` = `943a6087`
- 179 commits between `v0.4.0-beta.10` and `v0.5.0-beta.14`
- 625 files changed (43.5k +, 57.7k -). Net code reduction: refactor-heavy release.
- 282 files in overlay-relevant paths (templates/, commands/, configurators/, utils/overlay.ts)
- Fork HEAD: `7dd3795`
- **Hard blocker**: `overlays/hiskens/overlay.yaml` declares `compatible_upstream: ">=0.4.0-beta.10 <0.5.0"` → must be relaxed before 0.5 is allowed.

## Overlay Asset Footprint
- `overlays/hiskens/templates/claude/{agents,hooks,commands,skills}/`
- `overlays/hiskens/templates/codex/`
- `overlays/hiskens/templates/trellis/{config.yaml,worktree.yaml,scripts/,spec/}`
- `overlays/hiskens/templates/trellis/spec/{python,matlab,guides}/` (largest hand-written content body)
- `overlays/hiskens/templates/trellis/scripts/multi_agent/` (overlay-owned multi-agent pipeline — high-conflict zone)
- `overlays/hiskens/exclude.yaml` (currently excludes 4 files: `before-dev`, `check`)

## Research Tasks (Parallel Agents)
1. **Topic Map** — categorize the 179 commits into behavior-level themes (task lifecycle, hooks, configurators, migration system, codex, etc.). Output: `findings/01-topic-map.md`
2. **Critical Override Diff** — deep diff of the 4 high-risk paths from `MAINTENANCE.md`:
   - `packages/cli/src/templates/claude/hooks/*.py`
   - `packages/cli/src/commands/*`
   - `packages/cli/src/configurators/*`
   - `packages/cli/src/utils/overlay.ts`
   Plus `packages/cli/src/migrations/manifests/0.5.0-beta.*.json` (new migration manifests — directly governs upgrade semantics).
   Output: `findings/02-critical-overrides.md`
3. **Overlay Asset Conflict Map** — for every file under `overlays/hiskens/templates/`, classify BASELINE / APPEND / EXCLUDE and risk level (HIGH/MEDIUM/LOW) of conflicting with 0.5.0 upstream. Output: `findings/03-overlay-conflict-map.md`
4. **Existing Playbook Adaptation** — read `.trellis/spec/guides/fork-sync-guide.md` end-to-end and lay out a 0.4 → 0.5 specialization with concrete commands, branch names, and decision rules. Output: `findings/04-playbook-adaptation.md`

## Acceptance
- All four findings files exist under `.trellis/tasks/04-26-research-v0-5-0-beta-sync/findings/`
- Final integrated plan written to `final-plan.md` in the task directory (synthesized by the dispatcher after agents return)
- Plan must answer:
  - Which sync target (tag vs branch tip) and why
  - Concrete Phase A safe-merge commands
  - Phase B drift-detection greps tailored to *this* diff
  - Phase C must-keep / must-port lists
  - `overlay.yaml` `compatible_upstream` update value
  - Risk register + rollback plan
  - Estimated time + checkpoints
- No code modification. Research only.

## Out of Scope
- Actually executing the merge (requires user confirmation when they're back)
- Downstream consumer propagation (round-5 follow-up, separate task)
