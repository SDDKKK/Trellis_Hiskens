# Trellis_Hiskens — Hiskens small-patch overlay

**Fork source**: https://github.com/mindfold-ai/Trellis  
**Hiskens fork**: https://github.com/SDDKKK/Trellis_Hiskens  
**Upstream base**: `v0.5.0-beta.15` (`854fb455e9261f4f84f18351183f550e0fae7016`)  
**Maintainer**: Hiskens / SDDKKK

## Purpose

`Trellis_Hiskens` is a small-patch rebuild of the Hiskens customization layer on top of upstream Trellis v0.5.

The fork intentionally keeps upstream Trellis v0.5 as the source of truth for the base CLI, templates, and `trellis-*` agent workflow, then layers Hiskens-specific scientific-computing behavior through `overlays/hiskens/` and a small amount of CLI overlay-loader support.

This migration is **not** a full replay/rebase of the old v0.4 fork history. The v0.4 custom layer was reviewed, trimmed, and rebuilt against the v0.5 architecture.

## What Hiskens adds

- `--overlay hiskens` support for:
  - `trellis init --overlay hiskens`
  - `trellis update --overlay hiskens`
- Hiskens scientific-computing specs and guides, including Python/MATLAB guidance and `review-checklist.md`.
- CCR-compatible Claude Code hook/settings overlay for local model routing metadata injection.
- RTK integration for compact tool output:
  - `rtk hook claude`
  - `rtk pytest`
  - `rtk ruff check ...`
  - `rtk ruff format --check ...`
- Codex/Claude platform overlay compatibility without replacing upstream v0.5 agents.

## What was intentionally removed from the old custom layer

The v0.4-era overlay carried a larger custom workflow. In v0.5 this fork deliberately does **not** ship those defaults:

- No standalone Hiskens `review` subagent override.
- No Ralph loop / `ralph-loop` hooks.
- No default `multi_agent` workflow configuration.
- No default `worktree.yaml` overlay.
- No `uv run` command recommendations in generated Hiskens templates.

Use upstream v0.5 `trellis-check` as the primary check/review path. Hiskens scientific correctness and data-integrity expectations live as specs/guides rather than a separate default review agent.

## Repository layout

- `overlays/hiskens/` — Hiskens overlay metadata, templates, hooks, specs, and maintenance docs.
- `packages/cli/src/utils/overlay.ts` — built-in/custom overlay resolution and config loading.
- `packages/cli/src/configurators/index.ts` — overlay-aware template collection, settings merge, safe path handling, and install/update logic.
- `scripts/upstream-diff.sh` — manual helper for comparing future upstream Trellis tags.
- `.upstream-version` — currently tracked upstream tag.

## Typical usage

From a consumer project:

```bash
trellis init --claude --codex --overlay hiskens -y
trellis update --overlay hiskens
```

For a dry-run update:

```bash
trellis update --overlay hiskens --dry-run
```

## Upstream maintenance model

Future upstream updates should be reviewed, not auto-merged blindly:

```bash
git fetch upstream --tags
scripts/upstream-diff.sh v0.5.0-beta.15 <new-upstream-tag>
```

When updating to a new upstream tag:

1. Compare upstream changes that touch CLI commands, configurators, hooks, and templates.
2. Keep Hiskens behavior in `overlays/hiskens/` unless a small CLI loader change is required.
3. Preserve upstream v0.5 agent names and workflow conventions.
4. Update `.upstream-version` only after validation passes.
5. Do not record or commit real API keys, tokens, or connection strings.

## Validation commands

Run these from the repository root before cutting a Hiskens release branch/PR:

```bash
python3 -m py_compile overlays/hiskens/templates/claude/hooks/*.py
pnpm --filter @mindfoldhq/trellis exec vitest run \
  test/configurators/index.test.ts \
  test/commands/init-joiner.integration.test.ts
pnpm typecheck
pnpm --filter @mindfoldhq/trellis run lint:all
pnpm build
pnpm test
```

Recommended smoke checks after build:

```bash
CLI="/path/to/Trellis_Hiskens/packages/cli/dist/cli/index.js"
TMP="$(mktemp -d)"

# Fresh project: install workflow + Claude/Codex platform overlays.
mkdir -p "$TMP/fresh"
cd "$TMP/fresh"
node "$CLI" init --claude --codex --overlay hiskens -y --no-monorepo
node "$CLI" update --overlay hiskens --dry-run

# Existing project: overlay-only reinit must merge configured platform settings too.
mkdir -p "$TMP/reinit/.trellis" "$TMP/reinit/.claude"
printf '{"env":{"EXISTING_SETTING":"kept"}}\n' > "$TMP/reinit/.claude/settings.json"
cd "$TMP/reinit"
node "$CLI" init --overlay hiskens -y
```

See `overlays/hiskens/MAINTENANCE.md` for the detailed maintenance checklist and `overlays/hiskens/RTK-INTEGRATION.md` for RTK-specific guidance.
