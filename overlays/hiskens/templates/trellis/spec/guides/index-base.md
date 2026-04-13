# Thinking Guides

> **Base document** -- universal thinking guides index. Project-specific extensions (if any) are loaded via `{project}-topo.md` files and appended after this content by the hook.

> **Purpose**: Expand your thinking to catch things you might not have considered.

## Why Thinking Guides?

**Most bugs and tech debt come from "didn't think of that"**, not from lack of skill:

- Didn't think about Python↔MATLAB data format at boundary → cross-layer bugs
- Didn't think about code patterns repeating → duplicated code everywhere
- Didn't think about edge cases → runtime errors
- Didn't think about future maintainers → unreadable code

These guides help you **ask the right questions before coding**.

## Available Guides

| Guide | Purpose | When to Use |
|-------|---------|-------------|
| [Codebase Search Guide](./codebase-search-guide.md) | Choose the right search tool (semantic vs exact) | When searching for code or understanding features |
| [External Search Strategy Guide](./search-guide.md) | Unified three-layer routing for external search (Context7, Grok Scripts) | When needing external info (library docs, APIs, news, fact-checking, deep research) |
| [GitHub Analysis Guide](./github-analysis-guide.md) | Analyze GitHub repos comprehensively (architecture, health, community, competitors) | When evaluating dependencies, researching implementations, or doing competitive analysis |
| [Agent Large File Strategy](./agent-large-file-strategy.md) | Handle agent Write failures on large files (>300 lines) | When agent loops on Write tool or generating large files |
| [Spec Integration Checklist](./spec-integration-checklist.md) | Ensure new specs are wired into agents, hooks, and jsonl | When adding or modifying any spec |
| [Code Reuse Thinking Guide](./code-reuse-thinking-guide.md) | Identify patterns and reduce duplication | When you notice repeated patterns |
| [Cross-Layer Thinking Guide](./cross-layer-thinking-guide.md) | Think through Python↔MATLAB data flow | Features spanning both languages |
| [Excel Reading Strategy](./excel-reading-strategy.md) | Read/compare Excel files via markitdown, openpyxl, polars | When agent needs to inspect or diff .xlsx files |
| [New Agent Wiring](./new-agent-wiring.md) | 7-step checklist for adding a new Trellis agent | When creating a new agent type |
| [Agent Design Principles](./agent-design-principles.md) | Programmatic vs semantic separation, anti-patterns | When designing or splitting agents |
| [Cross-Platform Thinking Guide](./cross-platform-thinking-guide.md) | WSL↔Windows path, encoding, line endings, SQLite cross-access | When code touches WSL/Windows boundary or multiple runtimes |
| [Codex Assist Guide](./codex-assist.md) | Route agents to Codex CLI for cross-model review, debugging, feasibility analysis | When needing a second model's opinion on scientific code, subtle bugs, or requirement feasibility |
| [Verification Before Completion](./verification-before-completion.md) | Enforce fresh verification evidence before any completion claim | When claiming lint/test/feature passes -- always re-run, never trust previous output |
| [Receiving Review](./receiving-review.md) | Protocol for handling feedback from check/review agents | When debug/implement agent receives review feedback |
| [TDD Guide](./tdd-guide.md) | Red-Green-Refactor cycle for Python scientific computing | When task.json has tdd=true; pure functions, algorithms, data transforms |
| [Finishing Branch](./finishing-branch.md) | Structured completion options after all checks pass | When finishing work and choosing commit/PR/keep/discard |

## Quick Reference: Thinking Triggers

### When to Think About Codebase Search

- [ ] You need to find code but don't know the exact file/function name
- [ ] You want to understand how a feature works across multiple files
- [ ] You're exploring unfamiliar parts of the codebase
- [ ] You need to find all code related to a concept (not just exact matches)

→ Read [Codebase Search Guide](./codebase-search-guide.md)

**Quick Rule**: Use `warpgrep` (preferred) or `codebase-retrieval` (fallback) for "what/how/where" questions. Use Grep for exact identifier lookups. If morph-mcp unavailable, `codebase-retrieval` covers all semantic search needs.

### When to Think About External Search

- [ ] You need library/framework documentation (API usage, code examples)
- [ ] You need to fact-check or verify technical claims
- [ ] You need the latest information beyond knowledge cutoff
- [ ] You need to fetch content from a specific URL
- [ ] You're researching best practices or comparing solutions
- [ ] You're making an architecture decision that needs evidence

→ Read [External Search Strategy Guide](./search-guide.md)

**Quick Rule**: Library docs → Context7 (Layer 0). Quick facts → web_search.py (Layer 1). Multi-source comparison → web_search.py + web_fetch (Layer 2). Deep research → web_search.py + web_fetch multi-round (Layer 3). URL content → web_fetch.py. Code search → Augment/Grep.

### When to Think About GitHub Analysis

- [ ] You're evaluating whether to use a library as a dependency
- [ ] You need to understand how a project implements a feature
- [ ] You're doing competitive analysis of similar projects
- [ ] You want to assess project health and maintenance status
- [ ] You need to find quality signals beyond the README

→ Read [GitHub Analysis Guide](./github-analysis-guide.md)

**Quick Rule**: Don't just read README. Check Issues (quality signals), Commits (activity), and community discussions (real feedback). Always include links for competitors and community references.

### When to Think About Cross-Layer Issues

- [ ] Feature involves both Python and MATLAB
- [ ] Data format changes between languages (CSV, Excel, MAT)
- [ ] Index convention matters (0-based vs 1-based)
- [ ] File paths involve Chinese characters or WSL paths

→ Read [Cross-Layer Thinking Guide](./cross-layer-thinking-guide.md)

### When to Think About Code Reuse

- [ ] You're writing similar code to something that exists
- [ ] You see the same pattern repeated 3+ times
- [ ] You're adding a new field to multiple places
- [ ] **You're modifying any constant or config**
- [ ] **You're creating a new utility/helper function** ← Search first!

→ Read [Code Reuse Thinking Guide](./code-reuse-thinking-guide.md)

### When to Think About Database Changes

- [ ] 修改表结构（列、约束、索引）
- [ ] 添加或删除索引 → 遵循 `idx_{缩写}_{列名}` 规范
- [ ] 大量 DELETE 后是否需要 VACUUM
- [ ] 重建表时是否有 FK CASCADE 风险
- [ ] IO 密集操作是否应先拷贝到 WSL 本地

→ Read [Database Index 规范](../python/database-index.md) + [Quality Guidelines WSL 章节](../python/quality-guidelines.md)

### When to Think About Spec Integration

- [ ] You just created a new spec file
- [ ] You introduced a new MCP tool or skill
- [ ] You modified tool references in an existing spec
- [ ] You noticed an agent is unaware of an existing spec
- [ ] You are modifying agents, hooks, or specs themselves (meta-task)

→ Read [Spec Integration Checklist](./spec-integration-checklist.md)

**Quick Rule**: Placing a spec in the folder ≠ it being used. Every new spec must be checked against 4 injection points: agent tools, body text, hook, jsonl. For meta-tasks (modifying Trellis infrastructure), use `task.py init-context <dir> trellis` to get proper context injection.

### When to Think About Codex Assist

- [ ] You're reviewing scientifically critical code (formulas, algorithms)
- [ ] You're stuck on a non-obvious bug and want a second opinion
- [ ] You need to evaluate whether a complex requirement is feasible
- [ ] You want cross-model validation on a complex diff

→ Read [Codex Assist Guide](./codex-assist.md)

**Quick Rule**: Codex is slow (300s timeout) and optional. Only use when cross-model validation adds real value. Skip for routine tasks. review uses `--mode review`; others use `--mode exec --ephemeral`.

### When to Think About Cross-Platform Issues (WSL)

- [ ] Code passes file paths between Python (WSL) and MATLAB/Java (Windows)
- [ ] Reading/writing files with Chinese characters in path or content
- [ ] SQLite accessed from multiple languages or environments
- [ ] Shell scripts or batch files need to work across boundaries
- [ ] Environment variables needed by both WSL and Windows processes

→ Read [Cross-Platform Thinking Guide](./cross-platform-thinking-guide.md)

**Quick Rule**: Always use `wslpath` for path conversion. Always specify UTF-8 encoding explicitly. Use `COALESCE()` for MATLAB SQLite queries. Copy DB to `/tmp/` for write-heavy operations.

### When to Think About Agent Design

- [ ] You're creating a new agent type
- [ ] An existing agent mixes programmatic checks and AI judgment
- [ ] Ralph Loop markers don't match agent output

→ Read [Agent Design Principles](./agent-design-principles.md) + [New Agent Wiring](./new-agent-wiring.md)

**Quick Rule**: Programmatic (exit code) → check agent + verify commands. Semantic (AI judgment) → review agent + fixed markers. Never mix both in one agent.

### When to Think About Verification Before Completion

- [ ] You're about to claim "lint passes" or "tests pass"
- [ ] You're outputting completion markers (review agent)
- [ ] You're running finish-work checklist
- [ ] You're tempted to say "should work" without running the command

→ Read [Verification Before Completion](./verification-before-completion.md)

**Quick Rule**: NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE. Run the command, read the output, then claim.

### When to Think About Receiving Review Feedback

- [ ] Debug agent received issues from check/review
- [ ] Implement agent received feedback to address
- [ ] You're about to fix something a reviewer flagged

→ Read [Receiving Review](./receiving-review.md)

**Quick Rule**: Read → Understand → Verify → Evaluate → Implement. Never skip steps. Push back if the fix would break functionality.

### When to Think About TDD

- [ ] Task has `tdd: true` in task.json
- [ ] You're implementing pure functions or algorithms
- [ ] You're writing data transformation logic
- [ ] You want higher confidence in correctness

→ Read [TDD Guide](./tdd-guide.md)

**Quick Rule**: Write the failing test first. If you wrote code first, delete it and start with the test. Use `pytest.approx()` for floats.

### When to Think About Hook Architecture

- [ ] You need data in one hook type that's only available in another
- [ ] You're adding a new hook that needs to share state across invocations
- [ ] You're modifying the context budget monitor or statusline hooks
- [ ] You need cross-session or cross-hook communication via bridge files

→ Read [Agent Design Principles](./agent-design-principles.md) (Two-Hook Bridge + Behavioral Guards sections)

**Quick Rule**: If data isn't available in your hook's stdin, use a bridge file (`/tmp/{name}-{session_id}.json`). Always add staleness guards and debounce logic.

### When to Think About Finishing a Branch

- [ ] All checks pass and you're ready to wrap up
- [ ] You need to decide between commit, PR, keep, or discard
- [ ] You're running `/trellis:finish-work`

→ Read [Finishing Branch](./finishing-branch.md)

**Quick Rule**: Present 4 options after checklist passes. Option 4 (discard) requires user confirmation.

## Pre-Modification Rule (CRITICAL)

> **Before changing ANY value, ALWAYS search first!**

```bash
grep -r "value_to_change" src/ scripts/ config/
```

This single habit prevents most "forgot to update X" bugs.

## How to Use This Directory

1. **Before coding**: Skim the relevant thinking guide
2. **During coding**: If something feels repetitive or complex, check the guides
3. **After bugs**: Add new insights to the relevant guide (learn from mistakes)

**Core Principle**: 30 minutes of thinking saves 3 hours of debugging.
