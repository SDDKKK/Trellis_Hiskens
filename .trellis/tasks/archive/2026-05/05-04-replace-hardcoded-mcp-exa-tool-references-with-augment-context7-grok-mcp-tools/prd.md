# Replace hardcoded mcp__exa__ with augment/context7/grok MCP tools

## Goal

Remove all hardcoded `mcp__exa__web_search_exa` and `mcp__exa__get_code_context_exa` references across the codebase, replacing them with the hiskens overlay's MCP stack: `mcp__augment-context-engine__*`, `mcp__context7__*`, `mcp__grok-search__*`.

The `.claude/agents/` files are already updated and serve as the reference pattern.

## What I already know

- `.claude/agents/trellis-{research,implement,check}.md` already use new tools (reference)
- research agent tools: `Read, Write, Glob, Grep, Bash, Skill, mcp__augment-context-engine__*, mcp__context7__*, mcp__grok-search__*`
- implement/check agent tools: `Read, Write, Edit, Bash, Glob, Grep, mcp__augment-context-engine__*, mcp__grok-search__*`
- The old exa tools exist in 3 layers: source templates, hook scripts, live runtime files
- `packages/cli/src/configurators/shared.ts:601-623` has a `mapLegacyToolToCopilot()` that maps exa → `["web", "exa/*"]`
- `regression.test.ts:4002` already guards against `mcp__exa__` in Copilot frontmatter

## Requirements

### Layer 1: Source templates (packages/cli/src/templates/)

Replace `mcp__exa__web_search_exa, mcp__exa__get_code_context_exa` in tools frontmatter:

| Platform | Files (3 per platform) |
|----------|----------------------|
| cursor | `cursor/agents/trellis-{research,implement,check}.md` |
| codebuddy | `codebuddy/agents/trellis-{research,implement,check}.md` |
| droid | `droid/droids/trellis-{research,implement,check}.md` |
| qoder | `qoder/agents/trellis-{research,implement,check}.md` |

Per-agent mapping (match `.claude/agents/` reference):
- **research**: `mcp__augment-context-engine__*, mcp__context7__*, mcp__grok-search__*`
- **implement**: `mcp__augment-context-engine__*, mcp__grok-search__*`
- **check**: `mcp__augment-context-engine__*, mcp__grok-search__*`

### Layer 2: Hook scripts

**`shared-hooks/inject-subagent-context.py`** (line 555, 600-601):
- Line 555: search tips text → update tool names
- Lines 600-601: tool table → replace exa rows with new tools

**`opencode/plugins/inject-subagent-context.js`** (line 121):
- Same search tips text → update tool names

### Layer 3: TypeScript logic

**`configurators/shared.ts`** (lines 613-615):
- `mapLegacyToolToCopilot()` switch cases for exa → add new cases for augment/context7/grok

### Layer 4: Live runtime files (this project)

- `.claude/hooks/inject-subagent-context.py` (lines 555, 600-601)
- `.cursor/hooks/inject-subagent-context.py` (lines 555, 600-601)
- `.cursor/agents/trellis-{research,implement,check}.md` (line 5)
- `.opencode/plugins/inject-subagent-context.js` (line 121)

### NOT in scope

- `packages/cli/dist/` — rebuild handles it
- `.trellis/.backup-*/` — historical snapshots
- `.trellis/tasks/archive/` — research docs
- `.claude/agents/` — already done

## Decision (ADR-lite)

**Context**: `mapLegacyToolToCopilot()` maps Claude Code MCP tool names to Copilot-native capability labels. augment/context7/grok are hiskens-overlay MCP servers that don't exist in Copilot's ecosystem.

**Decision**: Map each tool to its semantic capability:
- `mcp__augment-context-engine__*` → `["search"]` (code semantic search)
- `mcp__context7__*` → `["web"]` (doc retrieval)
- `mcp__grok-search__*` → `["web"]` (web search)

**Consequences**: Copilot agents get correct capability categories without dead server-specific wildcards.

## Acceptance Criteria

- [ ] `grep -r "mcp__exa__" packages/cli/src/` returns 0 results
- [ ] `grep -r "mcp__exa__" .claude/ .cursor/ .opencode/` returns 0 results (excluding backup)
- [ ] `npm test` in packages/cli passes (including regression.test.ts)
- [ ] New Copilot mapping covers augment/context7/grok tools
- [ ] Live runtime files match their template sources

## Definition of Done

- All source templates updated
- Hook scripts updated
- TypeScript logic updated
- Live files updated
- Tests pass

## Technical Notes

- Reference pattern: `.claude/agents/trellis-{research,implement,check}.md`
- The hook `build_research_prompt()` injects a tool availability table into the research subagent — this is the user-visible symptom
- `mcp__chrome-devtools__*` references are separate concern, not in scope
