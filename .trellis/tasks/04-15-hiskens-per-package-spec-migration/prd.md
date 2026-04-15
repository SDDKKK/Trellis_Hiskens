# Complete per-package spec migration for Hiskens scientific workflow

## Goal

Make the Hiskens scientific-computing workflow truly package-aware on top of the upstream monorepo infrastructure, so the overlay no longer falls back to the old global `.trellis/spec/python/` and `.trellis/spec/matlab/` mental model.

## Problem

The fork already contains upstream monorepo plumbing:

- `config.yaml` supports `packages`, `default_package`, and `session.spec_scope`
- `task.json` stores `package`
- `get_context.py --mode packages` exposes package-scoped spec metadata

But the Hiskens overlay still has partial drift:

- Some runtime scripts still build context from global `spec/python` or `spec/matlab`
- Some hooks still inject global spec indexes instead of package-scoped indexes
- Some plan/bootstrap/session scripts still assume `python|matlab|both` without a package entry point
- Many commands and skills still instruct agents to read global spec paths directly

This creates a split mental model:

- Infra says: `spec/<package>/<layer>/...`
- Hiskens workflow says: `spec/python/...` and `spec/matlab/...`

The migration must remove that split.

## Requirements

- Preserve the Hiskens scientific workflow.
  - Keep Python / MATLAB domain guidance where still useful.
  - Do not force a blind rewrite into upstream `backend|frontend|fullstack` semantics.
- Make runtime context generation package-aware.
  - `task_context.py` must resolve package-scoped spec paths when monorepo mode is active.
  - Default context generation must stop hardcoding global `spec/python` and `spec/matlab`.
- Make SessionStart package-aware.
  - Claude hook must adopt the current upstream package-scope / spec-scope behavior.
  - Hiskens-only additions such as stale-session warning, Nocturne, and thinking framework must be preserved.
- Make supporting scripts package-aware.
  - `add_session.py` must support `--package` plus inferred package resolution.
  - `create_bootstrap.py` must generate package-aware spec references.
  - `multi_agent/plan.py` must accept and pass package context through task creation.
  - hidden planning dependencies such as `common/context_assembly.py` and plan agent definitions must stay in sync with the launcher and package model.
- Remove old global-spec assumptions from Hiskens prompts and skills.
  - `start`, `parallel`, `finish-work`, `before-*`, `check-*`, `implement`, `plan`, `onboard`, `integrate-skill`, `break-loop`, and related skills/commands must stop telling agents to read only `.trellis/spec/python/` or `.trellis/spec/matlab/`.
  - Prompts must route through `get_context.py --mode packages` and package-scoped spec indexes.
- Keep single-repo compatibility.
  - Non-monorepo projects must continue to work without requiring `--package`.

## Scope

### In Scope

- Overlay runtime scripts under `overlays/hiskens/templates/trellis/scripts/`
- Overlay hooks under `overlays/hiskens/templates/claude/hooks/`
- Overlay commands / agents / skills that still encode the old global-spec model
- Task setup and package propagation across the Hiskens workflow

### Out of Scope

- Removing Python / MATLAB guidance from the Hiskens workflow entirely
- Replacing the Hiskens scientific workflow with pure upstream frontend/backend/fullstack semantics
- Downstream project updates in other repositories

## Target Areas

### Behavior-critical

- `overlays/hiskens/templates/trellis/scripts/common/task_context.py`
- `overlays/hiskens/templates/trellis/scripts/common/context_assembly.py`
- `overlays/hiskens/templates/claude/hooks/session-start.py`
- `overlays/hiskens/templates/trellis/scripts/add_session.py`
- `overlays/hiskens/templates/trellis/scripts/create_bootstrap.py`
- `overlays/hiskens/templates/trellis/scripts/multi_agent/plan.py`

### Prompt / skill drift cleanup

- `overlays/hiskens/templates/claude/commands/trellis/start.md`
- `overlays/hiskens/templates/claude/commands/trellis/parallel.md`
- `overlays/hiskens/templates/claude/commands/trellis/finish-work.md`
- `overlays/hiskens/templates/claude/commands/trellis/before-python-dev.md`
- `overlays/hiskens/templates/claude/commands/trellis/before-matlab-dev.md`
- `overlays/hiskens/templates/claude/commands/trellis/check-python.md`
- `overlays/hiskens/templates/claude/commands/trellis/check-matlab.md`
- `overlays/hiskens/templates/claude/agents/implement.md`
- `overlays/hiskens/templates/claude/agents/plan.md`
- `overlays/hiskens/templates/codex/agents/plan.toml`
- Matching files under `overlays/hiskens/templates/agents/skills/`

## Acceptance Criteria

- [ ] `task_context.py` no longer hardcodes global `spec/python` / `spec/matlab` paths for monorepo runtime context
- [ ] Claude `session-start.py` reads package-scoped spec indexes and preserves Hiskens-only injected sections
- [ ] `add_session.py` supports package-aware tagging and inference
- [ ] `create_bootstrap.py` references package-aware spec paths
- [ ] `multi_agent/plan.py` can carry package context into created tasks
- [ ] Overlay prompts and skills no longer instruct agents to use the old global-spec model as the default path
- [ ] Single-repo fallback still works
- [ ] Verification covers at least one monorepo package-scoped path and one single-repo fallback path

## Technical Notes

- Prefer rebasing Hiskens overrides onto the current upstream template versions instead of patching old overlay files in place.
- For prompt/skill files, normalize guidance around:
  - `python3 ./.trellis/scripts/get_context.py --mode packages`
  - `.trellis/spec/<package>/<layer>/index.md`
  - `.trellis/spec/guides/index.md`
- For scientific guidance, keep Python / MATLAB as domain layers inside package-scoped spec trees rather than as global root-level trees.
- Treat this as a fork-sync + workflow-contract task, not a cosmetic documentation cleanup.
