# PRD: Overlay Cleanup + Upstream v0.6.2 Sync

## Background

The hiskens Trellis fork has accumulated overlay customizations since v0.6.0-beta. Several have been superseded (ccline replaced statusline.py), proven low-value (channel agents architect/plan/research never adopted by downstream), or become unnecessary (codegraph ToolSearch preload, subagent-audit). This task removes dead overlay code, updates the `trellis-overlay` skill to reflect the slimmed-down fork, and merges upstream v0.6.2 (14 commits).

## Requirements

### R1: Remove dead overlay code from CLI templates

| Item | Files | Reason |
|---|---|---|
| statusline.py | `shared-hooks/statusline.py`, `shared-hooks/index.ts` | Replaced by ccline |
| Channel agents (architect/plan/research) | `trellis/agents/{architect,plan,research}.md`, `trellis/index.ts` | Upstream doesn't distribute; never adopted downstream |
| Codegraph ToolSearch preload | `claude/agents/trellis-{check,implement,research}.md` | No longer needed; codegraph loads on demand |
| sync-trellis-to-nocturne.py | `.trellis/scripts/sync-trellis-to-nocturne.py` | Nocturne no longer used |
| subagent-audit toolkit | `subagent-audit/` directory | MCP tools now universally available; audit toolkit obsolete |

### R2: Retain CCR model routing overlay

The inject-subagent-context.py CCR functions (`_load_features`, `_ccr_model_keys`, `get_ccr_model_tag`) and config.yaml Feature Flags section MUST survive the merge.

### R3: Merge upstream v0.6.2

Merge 14 upstream commits (merge base `29b5141b..upstream/main`). Key upstream changes:
- Phase 3.1 folded into 2.2 + 3.4
- AGENTS.md / CLAUDE.md GitNexus sections slimmed
- `/continue` routing fix
- Version bump to 0.6.2
- Migration manifests 0.6.1 + 0.6.2

### R4: Update trellis-overlay skill

Update `.claude/skills/trellis-overlay/SKILL.md` to remove references to deleted customization points (statusline, channel agents) and reflect the current minimal overlay surface.

### R5: Update trellis-publish skill if needed

Check if trellis-publish references any deleted items; update if so.

## Constraints

- No `git push` — local commit only
- CCR routing must remain functional after merge
- Version format: `0.6.2-hiskens`

## Acceptance Criteria

1. `statusline.py` not in `shared-hooks/index.ts` SharedHookName type or platform arrays
2. `statusline.py` file deleted from `shared-hooks/`
3. `architect.md`, `plan.md`, `research.md` deleted from `trellis/agents/`
4. `trellis/index.ts` has no references to architect/plan/research
5. Codegraph ToolSearch preload blocks removed from claude agent templates (check/implement/research)
6. `subagent-audit/` directory deleted
7. `.trellis/scripts/sync-trellis-to-nocturne.py` deleted
8. `get_ccr_model_tag` present in `inject-subagent-context.py` after merge
9. `features.ccr_routing: true` present in `templates/trellis/config.yaml`
10. `packages/cli/package.json` version = `0.6.2-hiskens`
11. `.upstream-version` updated to upstream HEAD hash
12. `trellis-overlay` skill no longer mentions statusline or channel agents
13. Upstream workflow.md Phase 3.1 changes reflected
