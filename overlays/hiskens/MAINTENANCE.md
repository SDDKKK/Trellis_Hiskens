# Hiskens Overlay Maintenance Guide

This guide describes how to maintain the Hiskens overlay after the Trellis v0.5 small-patch rebuild.

## Core principles

1. Keep upstream Trellis v0.5 as the default architecture.
2. Keep Hiskens behavior small and explicit under `overlays/hiskens/` whenever possible.
3. Treat upstream updates as manual review events, not automatic merge events.
4. Use upstream `trellis-*` agents and workflows; do not reintroduce legacy v0.4 custom reviewer, loop, or worktree orchestration defaults.
5. Validate both the CLI package and a fresh generated project before release.
6. Never commit or document real API keys, tokens, passwords, or connection strings.

## Current overlay scope

The Hiskens overlay may own:

- Scientific-computing specs and guides under `templates/trellis/spec/`.
- Python/MATLAB/project-review checklist documentation.
- Claude Code settings overlay for Hiskens hooks and environment-variable names.
- CCR model-routing hook behavior through `templates/claude/hooks/inject-subagent-context.py`.
- RTK hook wiring through Claude `PreToolUse` settings.
- Codex/Claude compatible supplemental templates that do not override upstream v0.5 agents.

The Hiskens overlay should not own by default:

- Standalone `review`, `debug`, `dispatch`, or other v0.4-era agent overrides.
- Ralph loop hooks or `SubagentStop` review loops.
- Legacy default routing files that bypass upstream Trellis v0.5.
- Default `worktree.yaml` verification blocks.
- `uv run`-based verification recommendations.

## File ownership

| Path | Owner / rule |
|---|---|
| `packages/cli/src/templates/**` | Upstream Trellis unless a core bug must be fixed. |
| `packages/cli/src/configurators/**` | Upstream plus minimal overlay-loader support. Keep changes generic. |
| `packages/cli/src/utils/overlay.ts` | Generic overlay resolution/loading utilities. Do not hard-code Hiskens-only behavior beyond built-in overlay lookup. |
| `overlays/hiskens/**` | Hiskens customization layer. Prefer adding here instead of patching upstream templates. |
| `.upstream-version` | The upstream Trellis tag currently used as the Hiskens base. |
| `scripts/upstream-diff.sh` | Manual upstream-review helper. |

## Updating overlay content

1. Identify whether the change is generic Trellis behavior or Hiskens behavior.
2. If generic, prefer an upstream-compatible CLI/template change with tests.
3. If Hiskens-specific, place it under `overlays/hiskens/templates/...`, mirroring the upstream target path.
4. For Claude settings, prefer `settings_merge` in `overlays/hiskens/overlay.yaml` rather than replacing the full upstream settings file.
5. Keep `overlays/hiskens/exclude.yaml` empty unless there is a documented reason to suppress a base template.
6. Search the overlay before release for removed v0.4 concepts:

```bash
python3 scripts/upstream-diff.sh  # then run the stale-template guard documented in the migration report
```

A clean v0.5 Hiskens overlay should have no matches for that release-blocking pattern.

## Upstream review workflow

When a new upstream Trellis tag is available:

```bash
git fetch upstream --tags
scripts/upstream-diff.sh "$(cat .upstream-version)" <new-upstream-tag>
```

Review any changes involving:

- `packages/cli/src/commands/*`
- `packages/cli/src/configurators/*`
- `packages/cli/src/utils/overlay.ts`
- `packages/cli/src/templates/claude/hooks/*`
- `packages/cli/src/templates/**/agents/*`
- shared hooks and settings templates

For each affected area:

1. Compare upstream behavior with the current fork.
2. Decide whether Hiskens needs no change, a small overlay change, or a generic CLI-loader change.
3. Preserve upstream v0.5 agent naming and generated project layout unless there is a documented reason not to.
4. Update `.upstream-version` only after tests and smoke checks pass.

## Validation matrix

Run from the repository root:

```bash
python3 -m py_compile overlays/hiskens/templates/claude/hooks/*.py
pnpm --filter @mindfoldhq/trellis exec vitest run \
  test/utils/overlay.test.ts \
  test/configurators/index.test.ts \
  test/commands/init-joiner.integration.test.ts \
  test/commands/update-internals.test.ts

pnpm typecheck
pnpm --filter @mindfoldhq/trellis run lint:all
pnpm build
pnpm test
```

The `init-joiner.integration.test.ts` coverage must include the initialized-project overlay-only path: existing `.trellis/` + configured `.claude/` + `init --overlay hiskens -y` should merge RTK/CCR settings without dropping existing Claude settings.

## Fresh/existing-project smoke checks

After build, test both a new generated project and an existing initialized project:

```bash
CLI="/path/to/Trellis_Hiskens/packages/cli/dist/cli/index.js"
TMP="$(mktemp -d)"

# Fresh project.
mkdir -p "$TMP/fresh"
cd "$TMP/fresh"
node "$CLI" init \
  --claude --codex --overlay hiskens -y --no-monorepo
node "$CLI" update \
  --overlay hiskens --dry-run

# Existing project with configured Claude.
mkdir -p "$TMP/reinit/.trellis" "$TMP/reinit/.claude"
printf '{"env":{"EXISTING_SETTING":"kept"}}\n' > "$TMP/reinit/.claude/settings.json"
cd "$TMP/reinit"
node "$CLI" init --overlay hiskens -y
```

Check that the generated/existing project includes:

- `.trellis/spec/guides/review-checklist.md`
- Hiskens Python/MATLAB/spec guidance
- Claude settings overlay with RTK/CCR hooks
- Existing Claude settings preserved during overlay-only reinit
- No legacy v0.4 custom reviewer/loop/worktree defaults
- No Hiskens template recommendation to use `uv run` for verification

## CCR checks

The CCR hook should be treated as routing metadata injection only. It should reference environment-variable names/mechanisms, not real secret values.

When editing `templates/claude/hooks/inject-subagent-context.py`:

```bash
python3 -m py_compile overlays/hiskens/templates/claude/hooks/inject-subagent-context.py
```

Then smoke-test a `trellis-check`-style prompt and verify that a `<CCR-SUBAGENT-MODEL>...</CCR-SUBAGENT-MODEL>` tag can be injected without printing or requiring any credential value.

## Release checklist

- [ ] `.upstream-version` matches the intended upstream tag.
- [ ] Hiskens overlay metadata compatibility range is correct.
- [ ] v0.4 release-blocking patterns are absent from `overlays/hiskens/templates`.
- [ ] Python hooks compile.
- [ ] Targeted overlay tests pass.
- [ ] Full CLI tests pass.
- [ ] `lint:all` passes.
- [ ] `build` passes.
- [ ] Fresh-project `init --overlay hiskens` and `update --overlay hiskens --dry-run` pass.
- [ ] Final report lists retained customizations, removed legacy behavior, risks, and follow-up items.
