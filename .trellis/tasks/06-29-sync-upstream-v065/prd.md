# Sync upstream Trellis v0.6.5 + overlay cleanup

## Goal

Merge upstream `mindfold-ai/Trellis` main branch (v0.6.5, commit `01ec8d65`) into the hiskens fork, resolve conflicts, verify all overlay customizations survive, bump the local version, and dogfood via `trellis update`.

## Background

- Current merge base: `ba2288aa` (v0.6.3)
- Upstream ahead: **37 commits** spanning v0.6.4 and v0.6.5
- Local ahead: 300 commits (hiskens-specific)
- Upstream changes: 112 files, +3538 / −266 lines

### Key upstream changes to absorb

| Change | Impact on overlay |
|---|---|
| New Trae IDE platform (configurator + templates + tests) | Additive; no conflict expected |
| JSONL gate enforcement (`task.py start` requires real curated entries) | Semantic upgrade; our workflow.md must match |
| PRD convergence pass in brainstorm SKILL.md | Additive; enhances brainstorm quality |
| Class-2 pull-based routing refactor (2.1 platform groupings) | workflow.md conflict likely |
| `filterCommands` dual-flag rule (`agentCapable && hasHooks`) | Configurator structural change |
| Deletion of `resolveCodexTrellisStartSkill()` | shared.ts structural change |
| Hook stdin blocking fix (#360) | Patch in shared.ts |
| Kiro `getIdeHooks` addition | Additive |
| Pi tools frontmatter + session context injection | Additive |

## Requirements

- REQ-1: Merge upstream/main into local main, resolving all conflicts
- REQ-2: Verify CCR routing overlay survives (`get_ccr_model_tag` in `inject-subagent-context.py`)
- REQ-3: Bump version to `0.6.5-hiskens` in `packages/cli/package.json` and `packages/core/package.json`
- REQ-4: Update `.upstream-version` to upstream HEAD commit hash
- REQ-5: Validate build passes (`npm run build` in packages/cli)
- REQ-6: Run `trellis update` on this project to dogfood the new templates

## Acceptance Criteria

- [ ] AC-1: `git merge upstream/main` completes without unresolved conflicts
- [ ] AC-2: `grep "get_ccr_model_tag" packages/cli/src/templates/shared-hooks/inject-subagent-context.py` returns matches
- [ ] AC-3: `packages/cli/package.json` version is `0.6.5-hiskens`
- [ ] AC-4: `npm run build` in `packages/cli` exits 0
- [ ] AC-5: `trellis update` in this project exits cleanly
- [ ] AC-6: `.upstream-version` matches upstream/main HEAD hash (`01ec8d65...`)
