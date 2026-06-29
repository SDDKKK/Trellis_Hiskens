# Implementation Plan — Sync upstream v0.6.5

## Ordered Steps

### 1. Merge upstream/main
```bash
git merge upstream/main --no-edit
```
Resolve conflicts — expected in:
- `packages/cli/src/templates/trellis/workflow.md` (platform lists, JSONL gate)
- `packages/cli/src/configurators/shared.ts` (resolveCodexTrellisStartSkill deletion)
- `packages/cli/src/configurators/index.ts` (Trae import + structural changes)
- `packages/cli/package.json` / `packages/core/package.json` (version)

**Verify**: `git diff --check` shows no conflict markers

### 2. CCR overlay verification
```bash
grep "get_ccr_model_tag" packages/cli/src/templates/shared-hooks/inject-subagent-context.py
```
If missing, restore from pre-merge state. This is the #1 regression risk per [[ccr-routing-overlay-guard]].

### 3. Version bump
Set version to `0.6.5-hiskens` in:
- `packages/cli/package.json`
- `packages/core/package.json`

### 4. Update `.upstream-version`
```bash
git rev-parse upstream/main > .upstream-version
```

### 5. Build validation
```bash
cd packages/cli && npm run build
```
**Verify**: exit code 0, no TypeScript errors

### 6. Dogfood
```bash
trellis self-update && trellis update
```
**Verify**: `trellis update` exits cleanly, templates reflect v0.6.5 changes

### 7. Commit
```bash
git add -A
git commit -m "feat: @hiskens/trellis v0.6.5-hiskens — sync upstream v0.6.5 + overlay cleanup"
```

## Rollback

```bash
git reset --hard HEAD~1  # if committed
git merge --abort         # if mid-merge
```
