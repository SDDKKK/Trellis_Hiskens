---
name: with-codex
description: Delegates coding tasks to Codex CLI for prototyping, debugging, and code review. Use when needing algorithm implementation, bug analysis, or code quality feedback. Supports three modes (exec/resume/review) and multi-turn sessions via SESSION_ID.
---

## Routing: This Skill vs Official /codex Commands

| Scenario | Use This Skill (codex_bridge.py) | Use Official Plugin |
|----------|-----------------------------------|---------------------|
| Trellis subagent (codex-implement) | Yes (`--context-file`) | No |
| Agent second opinion (`--inject-context`) | Yes | No |
| Ad-hoc user request in main session | No | `/codex:rescue` |
| User wants code review | No | `/codex:review` |
| Checking job status | No | `/codex:status` |
| Oracle/consultant mode | Yes (`--query-type`) | No |

> **Rule**: Subagents cannot access `/codex:*` slash commands.
> In subagent context, `codex_bridge.py` is the only option.

## Quick Start

```bash
# Exec mode (default)
python scripts/codex_bridge.py --cd "/path/to/project" --PROMPT "Your task"

# Review mode
python scripts/codex_bridge.py --mode review --cd "/project" --uncommitted --PROMPT "Review for quality"

# Resume session
python scripts/codex_bridge.py --mode resume --SESSION_ID "uuid" --PROMPT "Continue"
```

**Output:** JSON with `success`, `SESSION_ID`, `agent_messages`, `usage`, and optional `error`.

## Modes

| Mode | Command | Use Case |
|------|---------|----------|
| `exec` | `codex exec` | General tasks: prototyping, debugging, analysis |
| `resume` | `codex exec resume` | Continue a previous session |
| `review` | `codex exec review` | Code review with diff awareness |

## Parameters

### Common
| Param | Required | Default | Description |
|-------|----------|---------|-------------|
| `--PROMPT` | exec/resume | - | Task instruction (optional for review with target) |
| `--cd` | No | `.` | Workspace root directory (exec: `-C` flag; review/resume: subprocess cwd) |
| `--mode` | No | `exec` | `exec`, `resume`, or `review` |
| `--model` | No | config | Model override (only when user specifies) |
| `--full-auto` | No | false | Sandboxed auto-execution (workspace-write + auto-approve) |
| `--sandbox` | No | `read-only` | `read-only`, `workspace-write`, `danger-full-access` (exec only) |
| `--ephemeral` | No | false | Don't persist session files |
| `--config` | No | - | Inline config override (repeatable, e.g. `--config model=o4-mini`) |
| `--image` | No | - | Attach image files (repeatable) |
| `--skip-git-repo-check` | No | true | Allow running outside git repos |
| `--return-all-messages` | No | false | Include full JSONL trace in output |
| `--output-schema` | No | - | JSON Schema file for structured output (exec only) |
| `--timeout` | No | 300 | Subprocess timeout in seconds |
| `--dry-run` | No | false | Print command without executing |

### Resume-specific
| Param | Required | Description |
|-------|----------|-------------|
| `--SESSION_ID` | Yes | Session UUID from previous response |

### Review-specific
| Param | Required | Description |
|-------|----------|-------------|
| `--uncommitted` | No | Review staged/unstaged/untracked changes |
| `--base` | No | Review changes against a branch |
| `--commit` | No | Review a specific commit SHA |
| `--title` | No | Commit title for review context |

## Multi-turn Sessions

**Always capture `SESSION_ID`** from the first response:

```bash
# Start
python scripts/codex_bridge.py --cd "/project" --PROMPT "Analyze auth in login.py"
# Response: {"SESSION_ID": "uuid-123", ...}

# Continue
python scripts/codex_bridge.py --mode resume --SESSION_ID "uuid-123" --PROMPT "Write fixes"
```

## Trellis Integration Patterns

> These patterns are for **subagent pipeline usage** where `/codex:*` commands are unavailable.

### implement agent: Prototyping
```bash
python scripts/codex_bridge.py --mode exec --cd "/project" --full-auto \
  --PROMPT "Implement algorithm X, return unified diff"
```

### review agent: Cross-model Review
```bash
# --base/--commit/--uncommitted and PROMPT are mutually exclusive
python scripts/codex_bridge.py --mode review --cd "/project" \
  --base main --full-auto --timeout 180
```

### debug agent: Bug Analysis
```bash
python scripts/codex_bridge.py --mode exec --cd "/project" \
  --PROMPT "Analyze this error: ..." --return-all-messages
```

### Fine-grained control via --config
```bash
# Override approval policy for CI-style execution
python scripts/codex_bridge.py --mode exec --cd "/project" \
  --config permissions.approval_policy=never \
  --config permissions.sandbox_mode=workspace-write \
  --PROMPT "task"
```

## Codex MCP Capabilities

Codex loads `~/.codex/config.toml` on every invocation. All configured MCP servers
(perplexity, context7, sequential-thinking, augment-context-engine, etc.) are available
to Codex during execution. This means Codex called via this skill has full agent
capabilities including web search, documentation lookup, and codebase retrieval.

## Output Format

```json
{
  "success": true,
  "SESSION_ID": "uuid",
  "agent_messages": "Codex response text",
  "usage": {"input_tokens": 24763, "cached_input_tokens": 24448, "output_tokens": 122}
}
```

On failure:
```json
{
  "success": false,
  "error": "Error description"
}
```
