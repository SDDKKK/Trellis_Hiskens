# RTK Integration — Hiskens Overlay

This document captures how the Hiskens overlay hooks into [RTK (Rust Token
Killer)](https://github.com/rtk-ai/rtk), a CLI proxy that compresses common
developer-tool output before it reaches the LLM. Readers should skim
MAINTENANCE.md first for the overlay sync workflow.

## Why RTK

RTK reduces token usage by 60–90% on commands the LLM runs frequently
(`git diff`, `grep`, `ls`, `ruff`, `pytest`, ...). For science projects
running multi-agent pipelines, the ruff/pytest output compression alone
saves significant context per check loop. Install via `rtk init -g`;
verify with `rtk --version` and `rtk gain`.

## Hook wiring — API migration history

Two generations exist. The overlay currently ships the second.

| Era | Hook command | Status |
|---|---|---|
| Legacy | `$HOME/.claude/hooks/rtk-rewrite.sh` (shell wrapper that invoked `rtk rewrite`) | Removed in rtk 0.37.x — script no longer installed |
| Current | `rtk hook claude` (direct binary, reads PreToolUse JSON from stdin) | In use as of overlay v1.x |

The migration to `rtk hook claude` happened because the wrapper script was
no longer bundled with rtk binaries, causing PreToolUse hooks to fail
silently (measured at 0.2% RTK coverage across 12357 subagent Bash calls
via `rtk discover`). See commit history of
`overlays/hiskens/templates/claude/` for the rollout.

**If you ever reintroduce a wrapper script**: mirror the update across all
8 agent frontmatters (check/plan/debug/research/review/dispatch/implement/
codex-implement) **and** `settings.overlay.json`. A stale reference in any
one file will silently skip RTK for whichever subagent runs it.

## Preferred command shapes in Hiskens projects

These recommendations are baked into `templates/trellis/worktree.yaml`'s
commented `verify:` block.

### Python tooling

| Tool | Preferred form | Why |
|---|---|---|
| ruff | `rtk ruff check .` / `rtk ruff format --check .` | RTK compresses ruff output; ruff has a global binary so no uv wrapper needed. |
| pytest | `uv run pytest -q` (for now) | pytest lives inside the uv-managed env (no global binary). RTK 0.37.2 does **not** unwrap `uv run` prefixes, so `rtk rewrite 'uv run pytest'` returns empty. Migrate to `rtk uv run pytest` once [rtk-ai/rtk#1405](https://github.com/rtk-ai/rtk/pull/1405) merges and is released. |
| python (scripts) | `uv run python ...` | Same `uv run` gap as pytest; RTK passes through. |

### Shell / VCS (hook-rewritten transparently)

`git diff`, `grep`, `ls`, `find`, `cat`, `curl`, `wc`, `gh` → all
automatically rewritten by `rtk hook claude` when the hook fires. No
explicit `rtk` prefix required in agent docs.

## Verify-block rationale (`templates/trellis/worktree.yaml`)

The overlay ships `verify:` commented rather than active because Hiskens
`dev_types` includes non-Python flavors (matlab, both, trellis, test,
docs). Forcing `rtk ruff` active would break MATLAB-only or docs-only
projects that don't install ruff. Project maintainers uncomment the block
matching their dev_type at `trellis init` time.

The `# Fallback` block with raw `uv run ruff` exists for projects that
haven't installed RTK yet — they can still run the Ralph Loop by
swapping to the fallback lines.

## Upstream dependencies to watch

| Upstream | Impact | Action |
|---|---|---|
| [rtk-ai/rtk#1405](https://github.com/rtk-ai/rtk/pull/1405) "feat: add uv run support" | Unblocks `rtk uv run pytest`, kills the ~1200-call/30-day uv-run gap. | On merge + release: update this doc, migrate `uv run pytest` → `rtk uv run pytest` (or `rtk pytest` if `rtk uv` handles routing) in `templates/trellis/worktree.yaml`. |
| rtk `hook claude` API shape | Any stdin/stdout contract change would require updating all 9 hook references at once. | Subscribe to rtk-ai/rtk release notes; grep overlay for `rtk hook claude` to find all call sites. |

## Maintainer checklist when updating overlay hook wiring

1. Grep the overlay tree: `rg "rtk-rewrite|rtk hook" overlays/hiskens/`.
2. Confirm all 9 hook references (8 agents + `settings.overlay.json`) point
   to the same form.
3. Sanity-test in a fresh project: `trellis init --overlay hiskens` →
   trigger a subagent Bash call → `rtk gain` should show subagent-sourced
   counts climbing.
4. If coverage stays at ~0.2%, the hook is not firing; re-check the
   referenced command exists on PATH.
