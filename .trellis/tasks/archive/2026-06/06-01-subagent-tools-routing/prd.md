# PRD: Subagent Tools Routing Overlay

## Problem

310 subagent transcripts across 5 downstream projects show that trellis
sub-agents (research / implement / check) overwhelmingly rely on `bash grep`,
`ls/find`, and `cat/head/tail` for code understanding — while `augment` is
used in only 0.4% of tool calls, `codegraph` in 0%, and `smart-search` in
0.03%.  Root causes:

1. **`mcp__codegraph__*` is not in the `tools:` allowlist** — sub-agents
   physically cannot call it (Claude Code `tools:` is restrictive).
2. **No prompt guidance** tells sub-agents *when* to prefer augment / codegraph
   over bash grep, or when to use smart-search for external research.

## Solution

Add codegraph to the tools allowlist and append a per-agent "Tool Routing"
guidance section to the three trellis agent templates, distributed via the
hiskens fork's `@hiskens/trellis` npm package.

## Scope

### In scope

- Modify **6 template files** (3 Claude Code `.md` + 3 Codex `.toml`):
  - `packages/cli/src/templates/claude/agents/trellis-research.md`
  - `packages/cli/src/templates/claude/agents/trellis-implement.md`
  - `packages/cli/src/templates/claude/agents/trellis-check.md`
  - `packages/cli/src/templates/codex/agents/trellis-research.toml`
  - `packages/cli/src/templates/codex/agents/trellis-implement.toml`
  - `packages/cli/src/templates/codex/agents/trellis-check.toml`

- For Claude Code agents:
  - Add `mcp__codegraph__*` to `tools:` frontmatter
  - Append tool routing guidance block at end of file

- For Codex agents:
  - Append tool routing guidance at end of `developer_instructions`

- All guidance in **English** (distributed package).

### Out of scope

- Other platforms (OpenCode, Cursor, Pi, Gemini, etc.) — no usage data yet.
- Overlay directory mechanism (`overlays/hiskens/templates/`) — not used;
  templates are edited in-place per fork convention.
- Automated verification tooling — manual verification via extract.py.

## Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| `tools:` field behavior | Restrictive allowlist | Verified: omitting a tool blocks it; wildcard `mcp__codegraph__*` works (augment precedent: 55 calls) |
| Guidance placement | File end, inside `<!-- hiskens:tools-routing:start/end -->` markers | Minimal merge conflict with upstream; machine-readable boundary |
| Guidance granularity | Per-agent, 10-15 lines each | Different agents have different tool-use anti-patterns (data-driven) |
| Platform scope | Claude Code + Codex | These have subagent transcript data; others don't |
| Template edit location | `packages/cli/src/templates/` directly | hiskens fork publishes its own npm; no overlay dir exists |
| smart-search access | Via existing Bash permission | CLI tool, no `tools:` change needed |
| codegraph tool names | Wildcard `mcp__codegraph__*` | Consistent with `mcp__augment-context-engine__*`; verified functional |

## Per-Agent Guidance Summary

### trellis-research

1. Code understanding → augment / codegraph first; grep only for exact string matches.
2. Directory exploration → `codegraph_files`, not `ls`/`find`.
3. External research → `smart-search` CLI; include community forums, X discussions, and consensus opinions.
4. File reading → `Read` tool, not `cat`/`head`/`tail`.

### trellis-implement

1. Before modifying → `codegraph_impact` to check blast radius.
2. Code location → `augment codebase-retrieval` for context, not grep.
3. Verification → use project's defined lint/test commands when available.

### trellis-check

1. Dependency verification → `codegraph_callers` + `codegraph_impact`.
2. Consistency checks → `augment` semantic search over grep for references.

## Acceptance Criteria

1. All 6 template files updated with tool routing guidance.
2. Claude Code agents have `mcp__codegraph__*` in `tools:` frontmatter.
3. `trellis update` on a downstream project produces agent files containing
   the new guidance block.
4. A real task dispatching trellis-research + trellis-implement on a
   downstream project shows improved augment/codegraph usage in the
   subagent transcript (verified via `subagent-audit/extract.py`).

## Data Backing

Source: `subagent-audit/report-micro.md` (310 subagent transcripts, 10,112 tool calls).

| Metric | research | implement | check |
|---|---|---|---|
| grep-via-bash | 985 (29%) | 236 (20%) | 352 (25%) |
| ls/find-via-bash | 890 (26%) | 212 (18%) | 190 (14%) |
| augment | 23 (0.4%) | 10 (0.4%) | 7 (0.3%) |
| codegraph | 0 | 0 | 0 |
| smart-search | 1 | 0 | 0 |
