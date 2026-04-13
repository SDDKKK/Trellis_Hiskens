# Agent Design Principles

> Architectural guidelines for designing and splitting Trellis agents.

## Principle: Programmatic vs Semantic Separation

An agent should use ONE verification mechanism, not mix both:

| Type | Verification | Control | Example |
|------|-------------|---------|---------|
| Programmatic | `worktree.yaml` verify commands | Exit code (0 = pass) | check agent: `ruff check`, `ruff format` |
| Semantic | Fixed completion markers | AI judgment + Ralph Loop | review agent: SCIENTIFIC_FINISH, etc. |

**When to split**: If an agent needs both `ruff check` (programmatic) AND "is this scientifically correct?" (semantic), split into two agents.

**Why**: Mixing causes control flow conflicts — verify commands short-circuit marker checking, or markers never match because they're generated from the wrong source.

## Anti-Pattern: Dual-Purpose Field

Never use a single field for both human-readable descriptions AND machine-matched identifiers.

**Bad**: `check.jsonl` reason field = `"Finish work checklist"` → Ralph Loop generates `FINISH_WORK_CHECKLIST_FINISH` → never matches hardcoded `SCIENTIFIC_FINISH` in agent prompt.

**Fix**: Use separate fields, or separate agents with their own control mechanisms.

## Pattern: Two-Hook Bridge (Cross-Hook Data Sharing)

Some data is only available in specific hook types. For example, `context_window.remaining_percentage` is only available in `Statusline` hook stdin — `PostToolUse` hooks do not receive it.

**Solution**: Write data to a bridge file in one hook, read it in another.

```
Hook A (has data)  →  writes /tmp/bridge-{session_id}.json
Hook B (needs data) →  reads bridge file → acts on data
```

**Implementation in Trellis**:
- `statusline-bridge.py` (Statusline hook) → writes `/tmp/claude-ctx-{session_id}.json`
- `context-monitor.py` (PostToolUse hook) → reads bridge file → injects `additionalContext` warnings

**Key Design Decisions**:
- Bridge file uses `session_id` to isolate concurrent sessions
- Staleness guard: ignore bridge file older than 120 seconds
- Debounce via `last_warned_pct` field to prevent warning spam
- Transparent proxy: statusline-bridge delegates display to existing inner command (e.g., CCR)

**When to use**: When data from one hook type is needed in another hook type, and direct parameter passing is not supported by Claude Code's hook API.

## Pattern: Agent Behavioral Guards

Cross-cutting behavioral rules embedded in agent prompts to prevent common failure modes. These are NOT verification commands — they are prompt-level behavioral constraints.

| Guard | Agent(s) | Trigger | Action |
|-------|----------|---------|--------|
| Deviation Rules | implement | Unexpected situation during implementation | 4-tier: auto-fix bugs → auto-add critical → auto-fix blockers → ASK architectural. 3 fix attempts max. |
| Analysis Paralysis Guard | implement, debug | 5+ consecutive Read/Grep/Glob without Edit/Write/Bash | STOP exploring, start implementing with what you have |
| Self-Check Protocol | implement | Before reporting completion | Verify files exist (`ls`), syntax valid (`ruff check`), no TODO/pass stubs |
| Goal-Backward Verification | review | D0 verification dimension | 3-level: Truth (goals met?) → Artifact (files exist?) → Link (goals ↔ artifacts connected?) |
| Stub Detection | review | D0 verification dimension | Detect `pass`, `return None`, `TODO`, `NotImplementedError` in new code |
| Mandatory Tool Routing | implement, research, debug | Any code search/exploration | NEVER Bash find/ls for project code. Priority: Grep → Glob → codebase-retrieval → Bash (last resort) |

**Design principle**: These guards are part of agent prompts, not hooks. They rely on AI judgment to detect and respond to the condition. Hooks handle programmatic enforcement (Ralph Loop).

**When to add a new guard**: If a failure mode occurs across multiple sessions and cannot be caught by a shell command, add it as a behavioral guard in the relevant agent prompt.

## Pattern: Mandatory Tool Routing (Anti-Degradation)

Sonnet-class models degrade to `Bash find/ls` for code exploration when tool routing is phrased as suggestions. This wastes tokens on repeated blind traversal and misses semantic context.

**Problem**:
```
# Bad — suggestion language, Sonnet ignores it
"Code search: warpgrep (broad semantic) or codebase-retrieval (deep understanding) or Grep (exact match)"
```

**Fix**: Use prohibition + priority table:
```
# Good — NEVER + numbered priority
"NEVER use Bash find/ls to explore project code. Use these instead:
1. Know exact identifier → Grep
2. Know file pattern → Glob
3. Call relationships, data flow → codebase-retrieval
4. Broad semantic search → codebase-retrieval
5. Paths outside project or tools 1-4 return nothing → Bash (last resort)"
```

**Why**: "NEVER X, use Y instead" is a much stronger signal than "prefer Y over X". The numbered priority list removes ambiguity about which tool to pick.

**Exception**: Paths outside the project directory (e.g., `/tmp/`) are not indexed by semantic search tools — Bash `find/ls` is the correct fallback there.

**Affected agents**: Any agent with `Bash` + semantic search tools (implement, research, debug).

## Pattern: Hook Skeleton + On-Demand Detail (Progressive Disclosure)

When a spec file is large (>100 lines) but needed by the main agent (not subagents), inject a lightweight skeleton via hook and let the agent `cat` the full file when needed.

**Problem**:
- Pure Hook injection: wastes tokens on every session (~246 lines)
- Pure slash-command trigger: unreliable — users skip commands, agent never sees the spec

**Solution**: Inject 30-line skeleton via `session-start.py`, reference full file:
```
Hook injects:    <thinking-framework> (30 lines: triggers + key steps)
Agent reads:     cat .trellis/spec/guides/thinking-framework.md (246 lines, on demand)
```

**When to use**: Specs that target the main agent (not subagents), are too large for full injection, but too important to be optional. Currently used for: `thinking-framework.md`.

**When NOT to use**: Subagent specs — use JSONL injection via `inject-subagent-context.py` instead (subagents don't persist across sessions, so they need full content every time).

## Decision Flowchart

```
New check needed?
├── Can it be a shell command with exit code? → Add to worktree.yaml verify
├── Requires AI judgment? → Add dimension to review agent
├── Cross-hook data sharing? → Two-hook bridge pattern
├── Prevent agent behavioral failure? → Add guard to agent prompt
├── Agent using wrong tools? → Mandatory tool routing (NEVER + priority table)
├── Large spec for main agent? → Hook skeleton + on-demand detail
└── Both programmatic + semantic? → Split: programmatic → check, semantic → review
```
