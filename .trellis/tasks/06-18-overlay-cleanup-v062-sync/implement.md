# Implementation Plan

## Execution Order

### Phase A: Remove dead overlay code (before merge, to reduce conflicts)

- [ ] A1. Delete `packages/cli/src/templates/shared-hooks/statusline.py`
- [ ] A2. Revert `packages/cli/src/templates/shared-hooks/index.ts` to upstream version (remove `"statusline.py"` from SharedHookName type and claude platform array)
- [ ] A3. Delete `packages/cli/src/templates/trellis/agents/{architect.md, plan.md, research.md}`
- [ ] A4. Revert `packages/cli/src/templates/trellis/index.ts` — remove architect/plan/research exports and `agents.set()` calls
- [ ] A5. Remove codegraph ToolSearch preload blocks from claude agent templates:
  - `templates/claude/agents/trellis-check.md` — remove ToolSearch preload instruction + codegraph tool table
  - `templates/claude/agents/trellis-implement.md` — same
  - `templates/claude/agents/trellis-research.md` — same
  - Keep `mcp__codegraph__*` in tools frontmatter (it's a valid tool wildcard), only remove the inline ToolSearch instruction blocks
- [ ] A6. Delete `.trellis/scripts/sync-trellis-to-nocturne.py`
- [ ] A7. Delete `subagent-audit/` directory (extract.py + reports)
- [ ] A8. Commit: `refactor(overlay): remove dead customizations — statusline, channel agents, codegraph preload, nocturne sync, subagent-audit`

### Phase B: Merge upstream v0.6.2

- [ ] B1. `git merge upstream/main --no-edit`
- [ ] B2. Resolve conflicts:
  - `packages/cli/package.json` → name=`@hiskens/trellis`, version=`0.6.2-hiskens`
  - `packages/cli/src/templates/shared-hooks/index.ts` → should be clean (we reverted to upstream in A2)
  - `packages/cli/src/templates/shared-hooks/inject-subagent-context.py` → keep CCR overlay (our version with `_load_features`, `_ccr_model_keys`, `get_ccr_model_tag`)
  - `packages/cli/src/templates/trellis/config.yaml` → take upstream new sections, preserve Feature Flags section
  - `packages/cli/src/templates/trellis/index.ts` → should be clean (reverted in A4)
  - `.trellis/workflow.md` → take upstream (Phase 3.1 removal)
  - `AGENTS.md` / `CLAUDE.md` → take upstream (GitNexus slimming)
  - workspace journals → `git checkout --ours`
- [ ] B3. Update `.upstream-version` to upstream HEAD hash
- [ ] B4. Update `packages/core/package.json` version if needed (should come from upstream as 0.6.2)

### Phase C: Update skills

- [ ] C1. Update `.claude/skills/trellis-overlay/SKILL.md`:
  - Remove Section 3 (StatusLine Hook) entirely
  - Remove channel agents from Section 2 agent tool wildcards (keep only check/implement/research for platforms that distribute them)
  - Update Section 1 version format to `0.6.2-hiskens`
  - Update upstream branch reference from `feat/v0.6.0-rc` to `main`
  - Remove statusline from pitfalls table
  - Update verification commands
- [ ] C2. Check `.claude/skills/trellis-publish/SKILL.md` for deleted references; update if needed

### Phase D: Verify & commit

- [ ] D1. Run verification checks:
  ```bash
  # No statusline references in distributed templates
  grep -rn "statusline" packages/cli/src/templates/shared-hooks/
  # No architect/plan/research in channel agents
  ls packages/cli/src/templates/trellis/agents/
  # CCR routing intact
  grep "get_ccr_model_tag" packages/cli/src/templates/shared-hooks/inject-subagent-context.py
  # Feature flags intact
  grep "ccr_routing" packages/cli/src/templates/trellis/config.yaml
  # Version correct
  grep '"version"' packages/cli/package.json
  ```
- [ ] D2. Final commit: `feat: @hiskens/trellis v0.6.2-hiskens — sync upstream v0.6.2 + overlay cleanup`

## Rollback

If merge conflicts are unresolvable: `git merge --abort` and retry with manual cherry-picks.
