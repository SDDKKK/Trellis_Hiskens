# RTK Integration — Hiskens Overlay

This document describes the RTK integration used by the Hiskens overlay after the Trellis v0.5 rebuild.

RTK is used to reduce noisy developer-tool output before it enters the LLM context. In Hiskens projects, the important paths are Python/MATLAB scientific-computing checks, ruff, pytest, git output, and shell inspection commands.

## Current wiring

The Hiskens overlay uses the current RTK Claude hook form:

```bash
rtk hook claude
```

That command is wired through the Claude Code `PreToolUse` settings overlay in:

```text
overlays/hiskens/templates/claude/settings.overlay.json
```

The overlay no longer ships old v0.4 agent frontmatter overrides, so there is no separate list of agent markdown files that must each be patched for RTK. Upstream v0.5 `trellis-*` agents remain in control, and the settings overlay provides the shared hook behavior.

## Preferred command forms

Use RTK-native command shapes where practical:

| Tooling need | Preferred command | Notes |
|---|---|---|
| Python tests | `rtk pytest` | Preferred over `uv run pytest -q` in Hiskens instructions/templates. |
| Ruff lint | `rtk ruff check .` | Keeps ruff output compact for LLM loops. |
| Ruff format check | `rtk ruff format --check .` | Use for verification blocks and CI-like checks. |
| Python scripts | `python3 ...` or `python ...` | Prefer direct interpreter calls for repository scripts where possible. |
| Git/shell inspection | plain `git diff`, `grep`, `ls`, etc. | The Claude `PreToolUse` hook can rewrite/compress supported calls transparently. |

Do not reintroduce `uv run` recommendations into generated Hiskens templates unless a future Trellis/RTK decision explicitly changes this policy.

## Why not use the old wrapper

Older Hiskens templates referenced wrapper-style hook commands such as `$HOME/.claude/hooks/rtk-rewrite.sh`. That wrapper is not part of the current Hiskens v0.5 overlay. The supported integration point is `rtk hook claude`.

## No default worktree verification block

The v0.5 overlay does not ship a default `templates/trellis/worktree.yaml` verification block.

Reasons:

- Hiskens supports multiple project flavors: Python, MATLAB, both, Trellis internals, tests, and docs.
- A single default verification block would be too opinionated for MATLAB-only or docs-only projects.
- Upstream Trellis v0.5 owns the primary workflow shape; Hiskens keeps RTK guidance in docs/specs instead of forcing a generated worktree config.

Project maintainers can still add project-local verification commands such as:

```bash
rtk ruff check .
rtk ruff format --check .
rtk pytest
```

## Maintainer checklist

When changing RTK wiring:

1. Inspect `overlays/hiskens/templates/claude/settings.overlay.json` and confirm the Claude `PreToolUse` hook still calls `rtk hook claude`.
2. Confirm generated templates do not reintroduce stale forms:

```bash
rg 'rtk-rewrite|uv run|worktree.yaml|SubagentStop' overlays/hiskens/templates
```

3. Run targeted overlay tests, including the initialized-project overlay-only regression:

```bash
pnpm --filter @mindfoldhq/trellis exec vitest run \
  test/utils/overlay.test.ts \
  test/configurators/index.test.ts \
  test/commands/init-joiner.integration.test.ts \
  test/commands/update-internals.test.ts
```

4. Run fresh-project and existing-project smoke checks with the built CLI. The existing-project check should start with `.trellis/` and `.claude/settings.json`, then run `init --overlay hiskens -y` and confirm `rtk hook claude` is merged while existing settings remain.
5. Trigger a Bash tool call in Claude Code if possible.
6. Use `rtk gain` or equivalent RTK diagnostics to confirm RTK is seeing tool calls in the target environment.

## Watch list

Monitor RTK release notes for changes to:

- `rtk hook claude` stdin/stdout contract.
- Supported command wrappers and passthrough behavior.
- pytest/ruff output compaction behavior.

If RTK changes its Claude hook API, update `settings.overlay.json`, this document, and the smoke-test checklist together.
