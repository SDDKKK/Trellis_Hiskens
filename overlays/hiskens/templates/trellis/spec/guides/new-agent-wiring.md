# New Agent Wiring Checklist

> When adding a new Trellis agent, all 7 touch points must be updated.
> Missing any one causes silent failures (agent not found, no context injection, no loop control).

## Checklist

| # | File | Action | Purpose |
|---|------|--------|---------|
| 1 | `.claude/agents/{name}.md` | Create | Agent definition (frontmatter + prompt) |
| 2 | `.claude/hooks/inject-subagent-context.py` | Edit | Add constant, AGENTS lists, context/prompt functions, dispatch branch |
| 3 | `.claude/settings.json` | Edit | Add SubagentStop hook matcher (if Ralph Loop controlled) |
| 4 | `.trellis/scripts/task.py` | Edit | Add `{name}.jsonl` generation function + call in `cmd_init_context` |
| 5 | `.claude/agents/dispatch.md` | Edit | Add phase documentation (Mode 2) |
| 6 | `.claude/commands/trellis/start.md` | Edit | Add workflow step (Mode 1) |
| 7 | `.trellis/spec/guides/spec-integration-checklist.md` | Edit | Add column to tool matrices |

## inject-subagent-context.py Detail (Touch Point #2)

This file has 5 internal touch points:

1. **Constant**: `AGENT_{NAME} = "{name}"`
2. **AGENTS lists**: Add to `AGENTS_REQUIRE_TASK`, `AGENTS_ALL`, etc.
3. **Context function**: `get_{name}_context()` — reads `{name}.jsonl`, builds context
4. **Prompt function**: `build_{name}_prompt()` — wraps context into agent prompt
5. **Dispatch branch**: `elif subagent_type == AGENT_{NAME}:` in main()

## Gotchas

- `.claude/` is gitignored — use `git add -f` to commit agent files
- Claude Code caches agent list at session start — restart session after creating new agent
- Symlinks under `.claude/skills/` cannot be `git add -f` (reports "beyond a symbolic link")
