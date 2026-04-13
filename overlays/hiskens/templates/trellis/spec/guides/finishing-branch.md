# Finishing a Development Branch

> Structured options for completing work on a development branch.

## Flow

1. **Verify** -- Confirm all checks pass (ruff + pytest + review markers)
2. **Present** -- Show 4 structured options to the user
3. **Execute** -- Carry out the user's choice
4. **Cleanup** -- Clean up worktree if applicable

## Completion Options

| # | Option | Description |
|---|--------|-------------|
| 1 | Commit locally | Manual `git commit` (Mode 1 default) |
| 2 | Push and create Draft PR | Auto-push + `gh pr create --draft` |
| 3 | Keep as-is | Leave changes uncommitted, handle later |
| 4 | Discard changes | Abandon all uncommitted work (requires confirmation) |

## Option Matrix

| Option | Merge | Push | Keep Worktree | Cleanup Branch |
|--------|-------|------|---------------|----------------|
| 1. Commit locally | - | - | N/A | - |
| 2. Create PR | - | Yes | Yes | - |
| 3. Keep as-is | - | - | Yes | - |
| 4. Discard | - | - | - | Yes (confirmed) |

## Safety Rules

- Option 4 MUST require user to type "discard" before executing
- Never auto-execute force-push
- Never auto-delete branches
- Always show `git status` before executing any option
- If uncommitted changes exist and user picks Option 1, remind them to stage files

## Commands

```bash
# Option 1: User runs manually
git add <files> && git commit -m "type(scope): description"

# Option 2: Automated
python3 ./.trellis/scripts/multi_agent/create_pr.py

# Option 3: No action needed
echo "Changes preserved. Resume with: python3 ./.trellis/scripts/task.py start <dir>"

# Option 4: After user confirms "discard"
git restore . && git clean -fd
```

## When to Use Each Option

- **Option 1**: Most common for Mode 1 development
- **Option 2**: When work is ready for review by others
- **Option 3**: When you need to context-switch but want to return later
- **Option 4**: When the approach was wrong and you want a clean slate
