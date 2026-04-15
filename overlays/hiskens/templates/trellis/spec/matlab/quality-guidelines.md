# MATLAB Quality Guidelines

## Required Checks

Run `checkcode` on every edited `.m` file.

```bash
matlab -batch "checkcode('filename.m')"
```

## Validation Rules

- Do not finish with unresolved `checkcode` L1 or L2 issues.
- Report line numbers and fix direction when `checkcode` finds problems.
- Use command-line MATLAB validation instead of manual GUI-only checks.
- When MATLAB and Python interact, verify both sides of the boundary.
