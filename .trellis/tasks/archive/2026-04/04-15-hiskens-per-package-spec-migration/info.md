# Implementation Prep Research

## Purpose

This document is the implementation-prep companion to `prd.md`.

`prd.md` defines the task contract:

- goal
- scope
- requirements
- acceptance criteria

This file is for execution prep:

- exact entry files
- call relationships
- current breakpoints
- migration strategy
- validation plan

The target is to make the Hiskens scientific workflow truly follow the upstream `per-package spec` model without losing Hiskens-specific scientific and memory workflows.

## Baseline

### What is already true

- Upstream monorepo infrastructure is already present in this fork.
- `config.yaml` already supports:
  - `packages`
  - `default_package`
  - `session.spec_scope`
- `task.json` already persists `package`.
- `get_context.py --mode packages` already exposes:
  - single-repo vs monorepo mode
  - package metadata
  - default package
  - active task package
  - spec scope

### What is still split

- Infrastructure already thinks in:
  - `.trellis/spec/<package>/<layer>/...`
- Hiskens workflow still often thinks in:
  - `.trellis/spec/python/...`
  - `.trellis/spec/matlab/...`
  - `python | matlab | both` as the primary routing model

### Current task scope

- Active task package: `cli`
- Immediate migration goal: make Hiskens scientific workflow package-aware under `cli`
- Compatibility goal: preserve single-repo fallback behavior

### Design references

- Prior package-spec adaptation history:
  - `.trellis/tasks/archive/2026-03/03-09-monorepo-spec-adapt/prd.md`
- Prior monorepo compatibility work:
  - `.trellis/tasks/archive/2026-03/03-10-monorepo-compat/prd.md`
- Hook size and platform behavior:
  - `.trellis/spec/cli/backend/platform-integration.md`
- Overlay rebase discipline:
  - `.trellis/spec/guides/fork-sync-guide.md`
- Script and hook conventions:
  - `.trellis/spec/cli/backend/script-conventions.md`

## Phase 1: Runtime Context Generation

### Entry files

- `overlays/hiskens/templates/trellis/scripts/task.py`
- `overlays/hiskens/templates/trellis/scripts/common/task_context.py`
- `overlays/hiskens/templates/trellis/scripts/common/task_store.py`
- `overlays/hiskens/templates/trellis/scripts/common/config.py`
- `overlays/hiskens/templates/trellis/scripts/common/packages_context.py`
- Hidden dependency:
  - `overlays/hiskens/templates/trellis/scripts/common/context_assembly.py`

### Call chain

Primary runtime chain:

1. `task.py init-context <task> <dev_type> [--package ...]`
2. `common.task_context.cmd_init_context()`
3. package resolution through:
   - CLI `--package`
   - `task.json.package`
   - `config.yaml.default_package`
4. JSONL generation through:
   - `get_implement_base()`
   - `get_implement_python()`
   - `get_implement_matlab()`
   - `get_implement_trellis()`
   - `get_check_context()`
   - `get_review_context()`
   - `get_debug_context()`
5. `task.json.dev_type` and `task.json.package` sync back to disk

Supporting chain:

1. `task.py create ... --package <pkg>`
2. `common.task_store.cmd_create()`
3. `task.json.package` persisted at task creation time

Discovery chain used by hooks and prompts:

1. `get_context.py --mode packages`
2. `common.packages_context.get_context_packages_json()`
3. `common.config.get_packages()` / `resolve_package()`

Hidden planning dependency:

1. plan flows call `common.context_assembly.get_plan_context()`
2. that function still scans `.trellis/spec/*` as a flat global category tree
3. if package migration changes the mental model but this function stays old, the plan agent will be primed with the wrong spec layout

### Current breakpoints

- Boundary-level package resolution already works in `cmd_init_context()`.
- The generated context still points to the old global spec tree.

Behavior-critical breakpoints:

- `get_implement_python(package)` hardcodes:
  - `.trellis/spec/python/index.md`
  - `.trellis/spec/python/code-style.md`
  - `.trellis/spec/python/quality-guidelines.md`
- `get_implement_matlab(package)` hardcodes:
  - `.trellis/spec/matlab/index.md`
  - `.trellis/spec/matlab/code-style.md`
- `get_review_context()` still hardcodes:
  - `.trellis/spec/python/code-style.md`
- `context_assembly.get_plan_context()` still describes the spec tree as global top-level categories instead of package-scoped spec roots

Important non-breakpoints that must survive:

- single-repo mode currently ignores `--package`
- monorepo mode currently rejects missing package when neither task nor default package can resolve one
- Hiskens-specific JSONL additions already present in this overlay must stay:
  - decisions memory
  - known issues memory
  - verification-before-completion guide
  - `review.jsonl`
  - `check-python` and `check-matlab`
  - review checklist
  - Trellis self-modification context

### Migration strategy

1. Add a package-aware spec path helper inside the Hiskens runtime layer.
2. Keep Hiskens dev types:
   - `python`
   - `matlab`
   - `both`
   - `trellis`
   - `test`
   - `docs`
3. Map `python` and `matlab` to:
   - monorepo: `.trellis/spec/<package>/python/...` and `.trellis/spec/<package>/matlab/...`
   - single-repo: existing `.trellis/spec/python/...` and `.trellis/spec/matlab/...`
4. Update all JSONL generators that emit spec file paths, not just implement context.
5. Update `context_assembly.get_plan_context()` in the same migration branch so plan-time context matches runtime context.
6. Do not wholesale replace Hiskens `task_context.py` with upstream:
   - the upstream file is structurally useful
   - but Hiskens workflow-specific additions must be re-carried intentionally

### Validation points

- `uv run python ./.trellis/scripts/task.py init-context <task> python --package cli`
  - `implement.jsonl` should point to `.trellis/spec/cli/python/...`
  - `review.jsonl` should stop pointing to global `.trellis/spec/python/...`
- `uv run python ./.trellis/scripts/task.py init-context <task> matlab --package cli`
  - `implement.jsonl` should point to `.trellis/spec/cli/matlab/...`
- monorepo negative case:
  - omit `--package` with no task/default package
  - command should still fail fast with available packages
- single-repo fallback:
  - package should be ignored rather than breaking the flow
- Hiskens-specific files must still be present after generation:
  - `review.jsonl`
  - `debug.jsonl`
  - review/check command references

### Implementation backfill (2026-04-15)

Status:

- completed in the overlay runtime layer

What changed:

- `common/task_context.py`
  - added `_get_scientific_spec_path()`
  - switched scientific spec references from global roots to package-aware roots via `get_spec_base()`
  - updated `get_implement_python()`
  - updated `get_implement_matlab()`
  - updated `get_review_context()` and its call site so review context can consume package
- `common/context_assembly.py`
  - rewrote `get_plan_context()` to describe:
    - monorepo package layout
    - per-package spec layers
    - shared guides
    - legacy flat roots separately when they still exist

Validation rerun in this round:

- `uv run python -m py_compile overlays/hiskens/templates/trellis/scripts/common/task_context.py overlays/hiskens/templates/trellis/scripts/common/context_assembly.py`
- helper smoke checks:
  - `impl_python=.trellis/spec/cli/python/index.md`
  - `impl_matlab=.trellis/spec/cli/matlab/index.md`
  - `review_has_cli_python_style=True`
- plan-context smoke:
  - `Mode: monorepo`
  - `cli (default): .trellis/spec/cli/backend/, .trellis/spec/cli/unit-test/`
  - `docs-site: .trellis/spec/docs-site/docs/`

Residual note:

- this repo validated the overlay logic at import/helper level
- a generated downstream project was not re-instantiated in this round just to exercise `task.py init-context` end-to-end

## Phase 2: SessionStart / Hook Injection

### Entry files

- `overlays/hiskens/templates/claude/hooks/session-start.py`
- `overlays/hiskens/templates/codex/hooks/session-start.py`
- Upstream baselines:
  - `packages/cli/src/templates/claude/hooks/session-start.py`
  - `packages/cli/src/templates/codex/hooks/session-start.py`
- Supporting runtime inputs:
  - `.trellis/scripts/get_context.py`
  - `common.packages_context`
  - `common.config`
  - active task `task.json`

### Call chain

Claude path:

1. Claude startup fires `claude/hooks/session-start.py`
2. hook calls `.trellis/scripts/get_context.py`
3. hook reads workflow and spec indexes from disk
4. hook adds Hiskens-only memory sections:
   - stale-session warning
   - memory summary
   - Nocturne context
   - thinking framework
5. hook writes final startup context to stdout

Current upstream Claude path:

1. load monorepo config and spec-scope settings
2. resolve allowed packages from:
   - monorepo status
   - `session.spec_scope`
   - active task package
   - default package
3. inject only relevant spec indexes
4. emit legacy spec migration warnings when `spec/<package>/...` is missing
5. emit structured `<task-status>`

Codex path:

1. Codex SessionStart hook reads stdin JSON
2. resolves `cwd`
3. runs `get_context.py`
4. injects workflow TOC and spec index content
5. emits JSON payload with `additionalContext`

### Current breakpoints

Claude overlay is the main blocker in this phase.

Behavior-critical drift:

- it injects global `Python / MATLAB / Guides` indexes directly
- it bypasses package filtering
- it ignores `session.spec_scope`
- it has no legacy migration warning for missing `spec/<package>/...`
- it does not emit `<task-status>`
- it is much larger than the upstream compact structure because Hiskens additions were layered on top of an older baseline

Hiskens-specific behavior that must survive:

- `get_stale_session_warning()`
- `get_memory_summary()`
- `get_nocturne_context()`
- `<thinking-framework>`

Codex nuance:

- the overlay Codex hook is close to upstream
- it already uses the compact JSON `additionalContext` envelope
- it already emits `<task-status>`
- it still injects all visible spec indexes rather than applying package scope filtering
- this is not an overlay-only problem; current upstream Codex behavior is also broader than the current Claude package filter model

### Migration strategy

Claude hook:

1. Rebase onto the current upstream Claude hook structure.
2. Reintroduce Hiskens-only sections one by one:
   - stale session warning
   - memory summary
   - Nocturne
   - thinking framework
3. Preserve compact workflow injection.
4. Preserve package-aware spec injection logic from upstream.
5. Re-measure total payload after each Hiskens-only section is restored.

Codex hook:

1. Treat the current overlay as mostly aligned with upstream compact behavior.
2. Decide explicitly whether Codex should stay broader than Claude or adopt package-scope filtering too.
3. If parity is desired, port the same package filter logic into Codex in a separate small patch.

### Validation points

- run the Claude overlay hook locally and inspect output for:
  - `<current-state>`
  - package-scoped spec sections only
  - Hiskens-only memory sections still present
  - `<task-status>`
  - legacy migration warning when appropriate
- measure output size after each edit
  - especially for the Claude path
  - keep the payload comfortably below the truncation budget described in `platform-integration.md`
- run the Codex overlay hook locally and confirm:
  - valid JSON output
  - `hookSpecificOutput.additionalContext` still present
  - `<task-status>` still present
  - no encoding regressions

### Implementation backfill (2026-04-15)

Status:

- completed for both Claude and Codex overlay hooks

What changed:

- `claude/hooks/session-start.py`
  - rebased onto the current compact JSON hook structure
  - added config/spec-scope loading
  - added legacy migration warnings
  - restored Hiskens-only sections:
    - stale session warning
    - memory summary
    - Nocturne context
    - thinking framework
  - emits `<task-status>` and package-scoped spec injection
- `codex/hooks/session-start.py`
  - added config/spec-scope loading
  - added package filter parity with Claude for visible spec indexes
  - added migration warning support
  - extended task-status detection to include `review.jsonl`

Validation rerun in this round:

- `uv run python -m py_compile overlays/hiskens/templates/claude/hooks/session-start.py overlays/hiskens/templates/codex/hooks/session-start.py`
- direct Claude hook smoke:
  - `claude_rc=0`
  - `claude_len=18531`
  - `claude_has_task_status=True`
  - `claude_has_packages_block=True`
  - `claude_has_backend_heading=True`
  - `claude_has_global_python_header=False`
- direct Codex hook smoke:
  - `codex_rc=0`
  - `codex_len=14708`
  - `codex_has_task_status=True`
  - `codex_has_packages_block=True`
  - `codex_has_backend_heading=True`
  - `codex_has_global_python_header=False`

Residual note:

- Claude payload is now below the rough truncation ceiling discussed in `platform-integration.md`, but much closer to it than vanilla
- explicit matrix testing for non-default `session.spec_scope` values was not rerun in this round

## Phase 3: Task Lifecycle Scripts

### Entry files

- `overlays/hiskens/templates/trellis/scripts/add_session.py`
- `overlays/hiskens/templates/trellis/scripts/create_bootstrap.py`
- `overlays/hiskens/templates/trellis/scripts/multi_agent/plan.py`
- `overlays/hiskens/templates/claude/agents/plan.md`
- `overlays/hiskens/templates/codex/agents/plan.toml`
- Hidden dependency:
  - `overlays/hiskens/templates/trellis/scripts/common/context_assembly.py`

### Call chain

`add_session.py`:

1. user or workflow calls `add_session.py`
2. script resolves developer workspace and journal target
3. script appends a journal session
4. Hiskens overlay optionally promotes learnings into Nocturne

`create_bootstrap.py`:

1. user or init flow calls `create_bootstrap.py [project-type]`
2. script creates `00-bootstrap-guidelines`
3. script writes `task.json`
4. script writes bootstrap `prd.md`
5. script sets the task as current

`multi_agent/plan.py`:

1. launcher parses task slug, dev type, requirement, platform
2. launcher creates task directory
3. launcher exports environment to the plan agent
4. launcher starts plan agent process
5. plan agent prompt runs `task.py init-context`
6. prompt writes `prd.md` and related task materials

### Current breakpoints

`add_session.py`:

- Hiskens file is still on the old branch
- no `--package`
- no package inference from active task or default package
- journal flow therefore cannot tag or route package-local session context cleanly
- Hiskens learning promotion logic is overlay-specific and must be preserved

`create_bootstrap.py`:

- generated bootstrap PRD still teaches only:
  - `.trellis/spec/python/...`
  - `.trellis/spec/matlab/...`
- generated `relatedFiles` still use global spec roots
- bootstrap task therefore teaches the old mental model to new projects

`multi_agent/plan.py`:

- still validates only `python | matlab | both`
- no `--package`
- no `PLAN_PACKAGE`
- cannot explicitly choose a package in multi-package repos

Plan prompt definitions:

- `claude/agents/plan.md`
- `codex/agents/plan.toml`

still assume the old launcher contract:

- environment variables do not mention package
- `task.py init-context` examples do not pass `--package`
- accepted planning output does not explicitly describe package routing

Hidden planning drift:

- `context_assembly.get_plan_context()` still describes a global spec tree
- if `plan.py` is upgraded but plan context stays old, the agent can still plan against the wrong structure

### Migration strategy

`add_session.py`:

1. Rebase onto upstream package-aware `add_session.py`.
2. Preserve Hiskens-specific learning append and Nocturne promotion behavior.
3. Add package resolution order consistent with runtime scripts:
   - CLI `--package`
   - active task package
   - default package
4. Keep behavior graceful in single-repo mode.

`create_bootstrap.py`:

1. Keep the scientific domain classification if desired:
   - `python`
   - `matlab`
   - `both`
2. Compute spec base dynamically:
   - monorepo: `.trellis/spec/<package>/...`
   - single-repo: `.trellis/spec/...`
3. Rewrite bootstrap PRD examples and `relatedFiles`.
4. Ensure the bootstrap task teaches package discovery first, not global roots first.

`multi_agent/plan.py` and plan prompts:

1. Add `--package` to launcher CLI.
2. Pass `--package` into `task.py create`.
3. Export `PLAN_PACKAGE`.
4. Update `claude/agents/plan.md` and `codex/agents/plan.toml` together.
5. Update plan-time context assembly in the same phase.

### Validation points

- `uv run python ./.trellis/scripts/add_session.py --help`
  - should expose package-aware usage if this phase is edited
- smoke path for `add_session.py`
  - active task package should be inferable without extra manual input
- run bootstrap generation and inspect:
  - generated `prd.md`
  - `task.json.relatedFiles`
  - no global-only spec roots in monorepo mode
- run `uv run python ./.trellis/scripts/multi_agent/plan.py --help`
  - should expose `--package`
- inspect plan agent env contract:
  - launcher exports `PLAN_PACKAGE`
  - plan prompts consume it consistently

### Implementation backfill (2026-04-15)

Status:

- completed for the active lifecycle/planning chain

What changed:

- `add_session.py`
  - added `--package`
  - added `--branch`
  - resolves package from:
    - explicit CLI arg
    - active task package
    - default package
  - writes package/branch into the journal body
  - preserves Hiskens learning + Nocturne promotion logic
- `create_bootstrap.py`
  - moved to argparse
  - added `--package`
  - computes `spec_base`
  - rewrote generated PRD examples and `task.json` related files to use package-aware spec roots
  - persists `package` into generated `task.json`
- `multi_agent/plan.py`
  - added `--package`
  - passes package into task creation
  - exports `PLAN_PACKAGE`
  - reports resolved package in launcher output
- plan prompts
  - `claude/agents/plan.md` and `codex/agents/plan.toml` now consume `PLAN_PACKAGE`
  - `init-context` examples pass `--package` when package is available

Validation rerun in this round:

- `uv run python -m py_compile overlays/hiskens/templates/trellis/scripts/add_session.py overlays/hiskens/templates/trellis/scripts/create_bootstrap.py overlays/hiskens/templates/trellis/scripts/multi_agent/plan.py`
- `uv run python overlays/hiskens/templates/trellis/scripts/multi_agent/plan.py --help`
  - shows `--package PACKAGE`
- `add_session.py` smoke:
  - `has_package=True`
  - `has_branch=True`
- `create_bootstrap.py` smoke:
  - `python_spec_ok=True`
  - `matlab_spec_ok=True`
- prompt contract grep:
  - `PLAN_PACKAGE` is present in both plan prompts
  - both prompts pass `--package "$PLAN_PACKAGE"` into `task.py init-context`

Important compatibility note:

- the Hiskens overlay template task CLI still supports:
  - `task.py complete`
  - `task.py set-status`
- the current repo runtime copy under `.trellis/scripts/task.py` does not
- prompt cleanup in this task must follow overlay template semantics, not assume the current dogfood runtime is already synced

## Phase 4: Prompt / Skill Drift Cleanup

### Entry files

Severity A: behavior-adjacent prompts and agents

- `overlays/hiskens/templates/claude/commands/trellis/start.md`
- `overlays/hiskens/templates/claude/commands/trellis/parallel.md`
- `overlays/hiskens/templates/claude/commands/trellis/finish-work.md`
- `overlays/hiskens/templates/claude/agents/implement.md`
- `overlays/hiskens/templates/claude/agents/plan.md`
- `overlays/hiskens/templates/codex/agents/plan.toml`
- `overlays/hiskens/templates/agents/skills/parallel/SKILL.md`
- `overlays/hiskens/templates/agents/skills/finish-work/SKILL.md`

Severity B: operator-facing command and skill drift

- `overlays/hiskens/templates/claude/commands/trellis/before-python-dev.md`
- `overlays/hiskens/templates/claude/commands/trellis/before-matlab-dev.md`
- `overlays/hiskens/templates/claude/commands/trellis/check-python.md`
- `overlays/hiskens/templates/claude/commands/trellis/check-matlab.md`
- `overlays/hiskens/templates/claude/commands/trellis/break-loop.md`
- `overlays/hiskens/templates/claude/commands/trellis/break-loop-base.md`
- `overlays/hiskens/templates/claude/commands/trellis/create-command.md`
- `overlays/hiskens/templates/claude/commands/trellis/integrate-skill.md`
- `overlays/hiskens/templates/claude/commands/trellis/onboard.md`
- `overlays/hiskens/templates/agents/skills/before-python-dev/SKILL.md`
- `overlays/hiskens/templates/agents/skills/before-matlab-dev/SKILL.md`
- `overlays/hiskens/templates/agents/skills/check-python/SKILL.md`
- `overlays/hiskens/templates/agents/skills/check-matlab/SKILL.md`

Severity C: reference and example drift

- `overlays/hiskens/templates/agents/skills/trellis-meta/references/claude-code/multi-session.md`
- `overlays/hiskens/templates/agents/skills/trellis-meta/references/claude-code/scripts.md`
- any remaining template examples that still teach `.trellis/spec/python/...` or `.trellis/spec/matlab/...` as defaults

### Call chain

These files do not change runtime logic directly, but they shape what the human or agent does next:

1. startup command or skill tells the agent what to read
2. planning/implementation prompt decides which spec roots to inspect
3. check / finish-work prompts decide which paths are validated
4. bootstrap / onboarding prompts teach the project mental model

If these prompts stay old while runtime scripts move to package scope, the system will still drift in practice.

### Current breakpoints

Common old-model markers still present across the overlay:

- hardcoded `.trellis/spec/python/...`
- hardcoded `.trellis/spec/matlab/...`
- `python | matlab | both` used as the main spec-root routing model
- mixed instructions like:
  - first call `get_context.py --mode packages`
  - later fall back to global python/matlab roots

Representative partial drift:

- `start.md` is partially modernized at the top, then reverts later to global roots
- `parallel.md` mentions package discovery but keeps old planning examples
- `finish-work.md` still points spec sync and validation toward global roots
- `before-*` and `check-*` skills still teach global `.trellis/spec/python|matlab/...` as the first step
- `onboard.md` and bootstrap-oriented material still teach the old setup path to new users

### Migration strategy

1. Rewrite behavior-adjacent prompts first.
2. Then rewrite operator-facing skills and onboarding material.
3. Leave archive history untouched unless it is used as live reference material.
4. Normalize all forward-facing instructions around:
   - `uv run python ./.trellis/scripts/get_context.py --mode packages`
   - `.trellis/spec/<package>/<layer>/index.md`
   - `.trellis/spec/guides/index.md`
5. Keep Python and MATLAB as domain layers where useful, but stop treating them as mandatory global roots.

### Validation points

- rerun an old-marker scan after edits
- confirm Severity A files no longer default to global python/matlab roots
- confirm `start`, `parallel`, and `finish-work` all tell the same story as runtime scripts
- confirm bootstrap and onboarding docs no longer teach the old mental model first

### Implementation backfill (2026-04-15)

Status:

- completed for the active overlay prompts and skills in this task scope

What changed:

- Severity A behavior-adjacent files updated:
  - `start.md`
  - `parallel.md`
  - `finish-work.md`
  - `implement.md`
  - `claude/agents/plan.md`
  - `codex/agents/plan.toml`
  - `agents/skills/parallel/SKILL.md`
  - `agents/skills/finish-work/SKILL.md`
- Severity B operator-facing files updated:
  - `before-python-dev.md`
  - `before-matlab-dev.md`
  - `check-python.md`
  - `check-matlab.md`
  - `improve-ut.md`
  - `break-loop.md`
  - `break-loop-base.md`
  - `create-command.md`
  - `integrate-skill.md`
  - `onboard.md`
  - matching Codex/skill files for `before-*`, `check-*`, and `improve-ut`

Normalized forward-facing behavior:

- discover package/layer layout first via `uv run python ./.trellis/scripts/get_context.py --mode packages`
- read `.trellis/spec/<package>/<layer>/index.md` instead of global scientific roots
- always include `.trellis/spec/guides/index.md`
- keep Hiskens `python | matlab | both` as user-facing dev-type vocabulary, but treat Python/MATLAB as package-local layers
- normalize touched prompt examples to `uv run python`
- keep `finish-work` on overlay-valid `task.py complete`

Validation rerun in this round:

- full overlay scan:
  - `rg -n "\\.trellis/spec/(python|matlab|unit-test)" overlays/hiskens/templates`
  - returns no matches after this edit batch
- active-file spot checks confirm:
  - `start`, `parallel`, `finish-work` are aligned with package discovery
  - `before-*` and `check-*` now read package-scoped spec indexes first
  - onboarding no longer teaches global scientific roots as the primary model

Residual note:

- untouched reference material outside this batch still contains older `python3` command examples in places
- that is a separate consistency cleanup from the per-package spec migration itself

## Phase 5: Verification And Rollout Order

### Entry files

Runtime verification targets:

- `overlays/hiskens/templates/trellis/scripts/common/task_context.py`
- `overlays/hiskens/templates/trellis/scripts/common/context_assembly.py`
- `overlays/hiskens/templates/trellis/scripts/add_session.py`
- `overlays/hiskens/templates/trellis/scripts/create_bootstrap.py`
- `overlays/hiskens/templates/trellis/scripts/multi_agent/plan.py`

Hook verification targets:

- `overlays/hiskens/templates/claude/hooks/session-start.py`
- `overlays/hiskens/templates/codex/hooks/session-start.py`

Prompt verification targets:

- the Severity A and Severity B files from Phase 4

### Call chain

Verification should follow the same rollout chain as the implementation:

1. fix runtime context generation first
2. fix SessionStart injection second
3. fix lifecycle scripts and planning contract third
4. clean prompts and skills fourth
5. rerun scans and smoke tests after the whole chain is consistent

This order matters because later phases consume the outputs of earlier phases.

### Current breakpoints

- current task docs now identify the correct edit set
- runtime logic and prompt guidance are still out of sync
- validation commands in older docs still often use `python3` instead of repo-standard `uv run python`
- without a staged verification order, it is too easy to check the prompt layer while runtime files are still wrong

### Migration strategy

Recommended edit order:

1. `common/task_context.py`
2. `common/context_assembly.py`
3. `claude/hooks/session-start.py`
4. `add_session.py`
5. `create_bootstrap.py`
6. `multi_agent/plan.py`
7. `claude/agents/plan.md`
8. `codex/agents/plan.toml`
9. prompt / skill cleanup batch

Recommended verification order:

1. syntax-level verification for edited Python files
2. `init-context` smoke tests
3. hook output inspection and size measurement
4. lifecycle script smoke tests
5. final prompt drift scan

### Validation points

Syntax and basic execution:

- `uv run python -m py_compile <edited-python-files>`

Runtime smoke tests:

- `uv run python ./.trellis/scripts/task.py init-context <task> python --package cli`
- `uv run python ./.trellis/scripts/task.py init-context <task> matlab --package cli`
- monorepo missing-package negative path
- single-repo fallback path when feasible

Hook smoke tests:

- run overlay Claude SessionStart hook directly
- run overlay Codex SessionStart hook directly
- capture output size for both

Prompt drift scan:

- rerun search for:
  - `.trellis/spec/python/`
  - `.trellis/spec/matlab/`
  - stale `python | matlab | both` routing language in active prompt files

Test expectation boundary:

- pure prompt-text edits do not require automated tests
- script logic edits do require smoke coverage
- add targeted regression tests only if the modified code already participates in tested CLI flows

### Implementation backfill (2026-04-15)

Status:

- completed for this round

Verification chain actually executed:

1. syntax / import verification
   - `uv run python -m py_compile` across all edited overlay Python files
2. runtime helper smoke
   - package-aware path generation in `task_context.py`
   - plan-context rendering in `context_assembly.py`
3. hook smoke
   - direct Claude SessionStart execution
   - direct Codex SessionStart execution
   - payload length capture for both
4. lifecycle/planning smoke
   - `multi_agent/plan.py --help`
   - `add_session.py` package/branch body checks
   - bootstrap PRD path checks
   - `PLAN_PACKAGE` prompt contract grep
5. final drift scan
   - no remaining global `.trellis/spec/python|matlab|unit-test` markers under `overlays/hiskens/templates`

Outcome of this round:

- runtime context generation is package-aware
- SessionStart injection is package-aware
- lifecycle scripts and plan contract propagate package
- active prompt/skill layer now teaches the same package model as runtime code

Remaining rollout boundaries:

- this round edits overlay templates, not every dogfood runtime copy under `.trellis/` and `.claude/`
- task metadata was not manually advanced from `planning` / phase `0`
  - current repo runtime task CLI and overlay template task CLI are not fully identical
  - manual mutation would create a misleading record in this repo
- downstream generated-project smoke remains a separate final confidence step if we want end-to-end release validation

## Resolved Decisions After This Round

1. Keep `python | matlab | both` as the Hiskens user-facing dev-type taxonomy, but map those dev types onto package-local spec roots internally.
2. Bring Codex SessionStart to package-filter parity with Claude in the overlay implementation.
3. Limit this migration branch to overlay templates and task-internal documentation; dogfood runtime copies remain a separate sync concern.

## Downstream Release Smoke Backfill (2026-04-15)

### Entry files

- `packages/cli/src/commands/init.ts`
- `packages/cli/src/configurators/workflow.ts`
- `packages/cli/test/commands/init.integration.test.ts`
- `overlays/hiskens/templates/trellis/config.yaml`
- `overlays/hiskens/templates/trellis/spec/python/*`
- `overlays/hiskens/templates/trellis/spec/matlab/*`

### Actual downstream path exercised

Generated fresh throwaway monorepo consumer projects under `/tmp/` and ran:

- `node /home/hcx/github/Trellis_Hiskens/packages/cli/bin/trellis.js init --yes --user hcx --claude --codex --overlay hiskens`
- `uv run python ./.trellis/scripts/task.py create ... --package solver`
- `uv run python ./.trellis/scripts/task.py init-context ... both --package solver`
- `uv run python ./.trellis/scripts/task.py start ...`
- `uv run python ./.trellis/scripts/task.py set-status ... active`
- `uv run python ./.trellis/scripts/task.py complete ...`
- `uv run python ./.trellis/scripts/task.py archive ...`
- direct Claude / Codex SessionStart hook execution with inline payload inspection

### Breakpoints found and fixed

1. `default_package` was written with unsanitized package names while `packages:` keys were sanitized.
   - fixed in `init.ts`
2. overlay monorepo bootstrap did not reliably use overlay `create_bootstrap.py`.
   - fixed in `init.ts`
3. overlay monorepo init still scaffolded old global / per-package `backend|frontend` spec trees while runtime prompts expected package-scoped `python|matlab`.
   - fixed by:
     - adding guides-only monorepo branch in `workflow.ts`
     - detecting overlay scientific spec layers in `init.ts`
     - materializing those layers into every `spec/<package>/...`
4. Hiskens overlay spec payload itself was incomplete.
   - added missing `python/index.md`, `directory-structure.md`, `data-processing.md`, `quality-guidelines.md`
   - added missing `matlab/index.md`, `code-style.md`, `quality-guidelines.md`
5. Claude SessionStart payload was still slightly above the rough 20 KB ceiling when all packages were injected.
   - fixed by changing overlay default `session.spec_scope` to `active_task`
   - monorepo now falls back to active task package, then default package

### Validation points actually confirmed

Downstream init result:

- generated project has only:
  - `.trellis/spec/guides/`
  - `.trellis/spec/solver/python/`
  - `.trellis/spec/solver/matlab/`
  - `.trellis/spec/viz/python/`
  - `.trellis/spec/viz/matlab/`
- generated project no longer has global:
  - `.trellis/spec/backend/`
  - `.trellis/spec/frontend/`
  - `.trellis/spec/python/`
  - `.trellis/spec/matlab/`
- bootstrap task points to `solver` package and package-local spec files

Lifecycle smoke:

- `create` stores `package: solver`
- `init-context` injects only `.trellis/spec/solver/python/*` and `.trellis/spec/solver/matlab/*`
- `start` sets `.trellis/.current-task`
- `complete` clears current task and resets scratchpad
- `archive` moves the task into `.trellis/tasks/archive/2026-04/`

SessionStart smoke:

- Claude `additionalContext` length: `19778`
- Codex `additionalContext` length: `17902`
- both include `## PACKAGES`
- both inject only the scoped package (`solver` in the smoke run)
- both no longer mention global `spec/python` or `spec/frontend`

### Important nuance preserved in the record

- `task.py complete` exists in the Hiskens overlay runtime, but the state machine still requires status `active` or `review`
- direct `start` from fresh `planning` is not enough to allow `complete`
- for smoke purposes we advanced with `set-status ... active` before `complete`

## Legacy SessionStart Blocker Backfill (2026-04-15)

### What this patch closed

- Hiskens Claude/Codex SessionStart now treats root `.trellis/spec/python/` and `.trellis/spec/matlab/` as legacy monorepo roots, alongside upstream-style `backend/frontend`.
- In monorepo mode, root scientific indexes are no longer silently injected; SessionStart only injects package-scoped `spec/<package>/python|matlab` layers.
- `finish-work` guidance now matches the real task state machine: `task.py complete` only works from `active` or `review`, so `planning` tasks must be promoted first.
- user-facing command hints in this patch set now use `uv run python` for Hiskens workflow scripts.

### Focused verification

- `uv run python -m py_compile overlays/hiskens/templates/claude/hooks/session-start.py overlays/hiskens/templates/codex/hooks/session-start.py overlays/hiskens/templates/trellis/scripts/create_bootstrap.py overlays/hiskens/templates/trellis/scripts/multi_agent/plan.py`
- inline Claude/Codex hook smoke on a synthetic monorepo:
  - migration warning present for legacy root `spec/python|matlab`
  - root `## python` / `## matlab` sections absent
  - scoped `## solver/python` present
  - out-of-scope `## viz/python` absent under `session.spec_scope: active_task`
