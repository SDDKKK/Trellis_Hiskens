# Spec Integration Checklist

> **Purpose**: Ensure new specs are properly wired into the entire workflow, not just placed in the spec folder.

---

## The Problem

**Dropping a file into `.trellis/spec/` does not mean it gets used.**

For a spec to actually take effect, it must be referenced at multiple levels:

```
spec file → agent tools frontmatter → agent body text guidance → hook injection → default jsonl entries → guide index
```

Missing any link in this chain means agents may never see the spec.

---

## Checklist

After adding or modifying a spec, verify each item:

### 1. Agent Frontmatter Tools

If the spec introduces new MCP tools:

- [ ] Determine which agents need the tool (see decision table below)
- [ ] Update the `tools:` frontmatter line in each relevant agent
- [ ] Do NOT add tools to agents that don't need them (least privilege)

| Agent | Suitable Tool Types |
|-------|-------------------|
| research | All search tools (core search role) |
| implement | Code search + doc search on demand |
| check | Code search only (no web needed) |
| debug | Code search + error lookup on demand |
| dispatch | Basic code awareness only |
| plan | Code search (for requirement evaluation) |

### 2. Agent Body Text

Adding a tool to frontmatter is not enough — agents need to know **when and how** to use it:

- [ ] Add a brief routing note in the agent's Workflow or Search section
- [ ] Explain division of labor between new tool and existing tools
- [ ] Keep it short — one or two lines is sufficient

### 3. Hook Context Injection

Check `.claude/hooks/inject-subagent-context.py`:

- [ ] If the hook has hardcoded tool lists or search tips, ensure the new tool is included
- [ ] Check functions like `get_research_context()` for updates needed
- [ ] Check `build_research_prompt()` Search Tools table

### 4. Default JSONL Entries

Check default generator functions in `.trellis/scripts/task.py`:

- [ ] `get_implement_base()` — does it need the new spec injected?
- [ ] `get_check_context()` — does it need the new spec injected?
- [ ] `get_debug_context()` — does it need the new spec injected?
- [ ] For guide-type specs, confirm `guides/index.md` is already in default entries

### 5. Guide Index

If the new spec is a guide:

- [ ] Add entry to the Available Guides table in `guides/index.md`
- [ ] Add corresponding trigger conditions in the Thinking Triggers section
- [ ] Ensure the Quick Rule description is accurate

### 6. Global Hook Sync

If the change introduces a new `PreToolUse`/`PostToolUse`/`Stop` hook that must work in ALL projects:

- [ ] Hook is added to `~/.trellis/shared/.claude/settings.json` (shared base), not just `~/.claude/settings.json` (global)
- [ ] Run `trellis-link.py settings-merge <project>` for all active projects
- [ ] Verify generated `settings.json` contains the new hook matcher

> **Why**: Project-level `hooks.<event>` **overrides** (not merges with) global `hooks.<event>`. A hook only in global settings will be invisible to any project that defines its own hooks for the same event type.

### 7. Cross-Reference Consistency

- [ ] All files/directories referenced in the new spec actually exist (no ghost references)
- [ ] Agent configuration descriptions in the spec match actual frontmatter
- [ ] Related descriptions in older specs are updated to stay consistent

---

## Quick Decision: Where Should a New Spec Be Injected?

```
Spec type?
|
+-- Development standards (code-style, quality)
|   → Add to language-specific implement/check/debug jsonl
|
+-- Search/tool guides (search guide, tool routing)
|   → Add to guides/index.md (already in default jsonl)
|   → Update relevant agent body text
|   → Check hook hardcoded references
|
+-- Architecture/design docs (architecture, design)
|   → Add to implement jsonl as needed
|   → plan agent may need reference
|
+-- Process/checklists (checklist, process)
    → Add to check jsonl
    → May need to add to finish-work command
```

---

## Anti-Patterns

| Wrong | Right |
|-------|-------|
| Create spec file without updating any references | Follow checklist item by item |
| Add tool to agent frontmatter but no usage guidance | Update body text at the same time |
| Write "recommend adding" in spec but never execute | Integrate immediately after writing the spec |
| Reference non-existent directories or files | Verify paths before writing references |
| Update one agent, forget other related agents | Systematically scan all agents |
| Add tool to agents but not update this inventory | Update inventory table below every time |
| Add global hook only to `~/.claude/settings.json` | Add to shared base settings + `settings-merge` all projects |

---

## Current Tool Inventory (Single Source of Truth)

**Update this table every time a tool is added or removed from any agent.**

Also update: `search-guide.md` Agent Tool Configuration table (with layer recommendations), `inject-subagent-context.py` Search Tools table.

### MCP Tools × Agent Matrix

| MCP Tool | research | implement | check | review | debug | dispatch | plan |
|----------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `augment..codebase-retrieval` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `morph..warpgrep_codebase_search` | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ |
| `morph..edit_file` | — | ✅ | ✅ | ✅ | ✅ | — | — |
| `context7..resolve-library-id` | ✅ | ✅ | — | — | ✅ | — | ✅ |
| `context7..query-docs` | ✅ | ✅ | — | — | ✅ | — | ✅ |
| `ide..getDiagnostics` | — | ✅ | ✅ | ✅ | ✅ | — | — |

### Bash Scripts × Agent Matrix

Grok search scripts (`.trellis/scripts/search/`) are called via Bash, not MCP. Any agent with Bash tool can use them.

| Script | research | implement | check | review | debug | dispatch | plan |
|--------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `web_search.py` | ✅ | ✅ | — | — | ✅ | — | — |
| `web_fetch.py` | ✅ | ✅ | — | — | ✅ | — | — |
| `web_map.py` | ✅ | — | — | — | — | — | — |
| `codex_bridge.py` | ✅ | — | — | ✅ | ✅ | — | ✅ |

### Built-in Tools × Agent Matrix

| Built-in Tool | research | implement | check | review | debug | dispatch | plan |
|---------------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Read | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Write | — | ✅ | ✅ | ✅ | ✅ | — | — |
| Edit | — | ✅ | ✅ | ✅ | ✅ | — | — |
| Bash | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Glob | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ |
| Grep | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ |
| Task | — | — | — | — | — | — | ✅ |

### Tools NOT Assigned to Agents (by design)

| Tool | Reason |
|------|--------|
| Skill (built-in) | Replaced by Bash-based codex_bridge.py to avoid skill pollution |
| `grok..get_config_info`, `switch_model`, `toggle_builtin_tools` | Admin/config MCP tools, main session only |
| `ide..executeCode` | Risk of uncontrolled code execution |
| `sequential-thinking..sequentialthinking` | Meta-reasoning, main session only |
| WebSearch, WebFetch (built-in) | Denied in settings.json, replaced by .trellis/scripts/search/ |

### Injection Points Checklist

When adding a new MCP tool, update ALL of these:

1. **Agent frontmatter** — `.claude/agents/<name>.md` `tools:` line
2. **Agent body text** — brief routing guidance in Workflow section
3. **Hook Search Tools table** — `inject-subagent-context.py` `build_research_prompt()`
4. **Hook Search Tips** — `inject-subagent-context.py` `get_research_context()`
5. **This inventory** — the tables above
6. **search-guide.md** — Agent Tool Configuration table (with layer recommendations)

---

## Core Principle

> **A spec's value is not in what it says, but in who reads it.**
>
> For every new spec, ask: which agent reads it, at what phase? If the answer is "not sure", it's a dead document.
