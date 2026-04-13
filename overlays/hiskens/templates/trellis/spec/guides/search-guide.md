# External Search Strategy Guide

> **Purpose**: Unified routing for all external information retrieval -- Context7 (library docs), Grok Scripts (web search/fetch/map). Three-layer architecture from free/fast to comprehensive.

---

## The Problem

**AI agents sometimes need information beyond the codebase** - latest docs, API references, best practices, or fact-checking.

Without a clear tool routing policy:
- Agents may try to use disabled built-in WebSearch/WebFetch (will fail)
- Agents may use code search tools (Augment) for general web queries (wrong tool)
- Search results lack source attribution
- Failed searches get abandoned instead of retried

The project provides two complementary external search toolsets:

- **Context7 MCP** (`resolve-library-id` / `query-docs`): Library documentation and code examples (free, fastest)
- **Grok Scripts** (`.trellis/scripts/search/`): Web search, URL content extraction, site mapping (via Bash)

---

## Module Activation

This module activates automatically in these scenarios:

- Library/framework documentation lookup (API usage, code examples)
- Web search / information retrieval / fact-checking
- Fetching web content / URL parsing / document extraction
- Querying latest information / bypassing knowledge cutoff
- Deep technical research / architecture decision support

---

## Tool Routing Policy

### Mandatory Replacement Rules

Built-in WebSearch/WebFetch are disabled in `settings.json`. All web searches are done via MCP tools or Bash calls to project scripts.

| Scenario | Disabled (Built-in) | Usage |
|----------|---------------------|-------|
| Library docs | N/A | `mcp__context7__resolve-library-id` → `mcp__context7__query-docs` |
| Quick answer | `WebSearch` | `Bash("uv run .trellis/scripts/search/web_search.py '<query>'")` |
| Structured search | `WebSearch` | `Bash("uv run .trellis/scripts/search/web_search.py '<query>'")` |
| Deep research | `WebSearch` | Multiple `web_search.py` + `web_fetch.py` rounds |
| Web fetch | `WebFetch` | `Bash("uv run .trellis/scripts/search/web_fetch.py '<url>'")` |
| Site map | N/A | `Bash("uv run .trellis/scripts/search/web_map.py '<url>'")` |

### Tool Capability Matrix

| Tool | Parameters | Output | Use Case |
|------|------------|--------|----------|
| `context7..resolve-library-id` | `libraryName`, `query` | Library ID | Resolve library name to Context7 ID |
| `context7..query-docs` | `libraryId`, `query` | Docs + code examples | Query library documentation |
| `web_search.py` | `<query>` (required), `--platform <p>`, `--model <m>` (optional) | Structured text | Platform-targeted search, code search |
| `web_fetch.py` | `<url>` (required) | Structured Markdown | Full content extraction / deep analysis |
| `web_map.py` | `<url>` (required), `--depth N`, `--breadth N`, `--limit N` (optional) | JSON site map | Site structure discovery |

---

## Environment Variables

Scripts use the following environment variables:

| Variable | Used by | Description |
|----------|---------|-------------|
| `GROK_API_URL` | web_search.py | Grok API base URL |
| `GROK_API_KEY` | web_search.py | Grok API key |
| `JINA_API_KEY` | web_fetch (tier 2) | Jina Reader API key (optional, free tier: 20 RPM without key, 500 RPM with free key) |
| `TAVILY_API_KEY` | web_fetch (tier 4), web_map | Tavily API key |
| `TAVILY_API_URL` | web_map | Tavily URL (default: `https://api.tavily.com`) |
| `CF_ACCOUNT_ID` | web_fetch (tier 3) | Cloudflare account ID |
| `CF_API_TOKEN` | web_fetch (tier 3) | Cloudflare API token |
| `MINERU_TOKEN` | web_fetch (tier 5) | MinerU API Bearer token (from mineru.net/apiManage/token) |
| `MINERU_API_BASE` | web_fetch (tier 5) | MinerU API base URL (default: `https://mineru.net`) |

---

## Tool Selection Decision Tree

```text
Need information?
|
+-- Is it about PROJECT CODE? (functions, patterns, architecture)
|   |
|   +-- Know exact identifier? --> Grep
|   +-- Broad semantic search? --> warpgrep (preferred) or codebase-retrieval (fallback)
|   +-- Deep code understanding? --> codebase-retrieval
|   +-- Need code examples from web? --> web_search.py --platform github
|
+-- Is it about a LIBRARY/FRAMEWORK? (API usage, version-specific behavior)
|   |
|   +-- Known library name? --> Context7 (Layer 0: resolve-library-id → query-docs)
|   +-- Context7 has no results? --> web_search.py (Layer 1 fallback)
|
+-- Is it a SIMPLE QUESTION? (fact, concept, quick lookup)
|   |
|   +-- --> web_search.py (Layer 1)
|
+-- Need MULTIPLE SOURCES / COMPARISON? (alternatives, best practices)
|   |
|   +-- --> web_search.py → web_fetch.py for key URLs (Layer 2 pipeline)
|
+-- Need DEEP RESEARCH? (architecture decisions, complex trade-offs)
|   |
|   +-- --> Multiple web_search.py + web_fetch.py rounds (Layer 2 iterative)
|
+-- Have a SPECIFIC URL to read? --> web_fetch.py (irreplaceable)
+-- Need SITE STRUCTURE?         --> web_map.py (irreplaceable)
```

### Tool Selection by Scenario (Local Codebase)

| Scenario | Primary Tool | Fallback if Unavailable |
|----------|-------------|------------------------|
| Find exact identifier (e.g., `calculate_saidi`) | Grep | — |
| Broad semantic search (e.g., "SAIDI calculation flow") | warpgrep | codebase-retrieval |
| Deep code understanding (complex relationships) | codebase-retrieval | Grep + Read |
| Find file by name pattern | Glob | — |

### Quick Reference: Tool Selection by Scenario (All Layers)

| Scenario | Tool | Layer |
|----------|------|-------|
| Library API usage / code examples | Context7 (`resolve-library-id` → `query-docs`) | 0 |
| Simple fact / concept explanation | `web_search.py` | 1 |
| Find multiple sources / compare options | `web_search.py` + `web_fetch.py` | 2 |
| Architecture decision / deep research | Multiple `web_search.py` + `web_fetch.py` rounds | 2 |
| Platform-targeted search (GitHub, etc.) | `web_search.py --platform github` | 1 |
| Fetch full content from a URL | `web_fetch.py` | — |
| Discover site link structure | `web_map.py` | — |
| Broad semantic code search | `warpgrep` (preferred) or `codebase-retrieval` | Local |
| Find exact identifier references | Grep | Local |
| Find code in local codebase | Augment (`codebase-retrieval`) | Local |

---

## Search Workflow

### Phase 0: Intent Classification

Before selecting a layer, classify the query intent. Intent determines layer and query expansion strategy.

**7 Intent Types**:

| Intent | Signal Words | Recommended Layer |
|--------|-------------|-------------------|
| **Factual** | "what is X", "X definition", "什么是X", "X的定义" | Layer 1 (web_search) |
| **Status** | "latest X", "X最新进展", "X update", time-implying words | Layer 1 (web_search) |
| **Comparison** | "X vs Y", "X和Y区别", "X or Y", "compare" | Layer 2 (web_search + web_fetch) |
| **Tutorial** | "how to X", "怎么做X", "X教程", "X tutorial" | Layer 0 (Context7) → Layer 1 |
| **Exploratory** | "深入了解X", "X生态", "about X", "X ecosystem" | Layer 2 (multiple rounds) |
| **News** | "X新闻", "本周X", "X this week", "X announcement" | Layer 1 (web_search) |
| **Resource** | "X官网", "X GitHub", "X文档", "X docs", "X repo" | Layer 0 (Context7) / Layer 1 |

**Intent Priority** (when multiple match): Resource > News > Status > Comparison > Tutorial > Factual > Exploratory

**Default**: When intent is unclear, treat as Exploratory.

### Phase 1: Query Expansion and Layer Selection

#### Query Expansion Rules

Before executing the search, expand the query for better coverage:

1. **Technical synonym expansion**: Automatically expand common abbreviations
   - k8s → Kubernetes, JS → JavaScript, Go → Golang, Postgres → PostgreSQL
   - tf → TensorFlow, torch → PyTorch, np → NumPy, pd → pandas, pl → polars

2. **Chinese-English bilingual expansion**: For Chinese technical queries, also generate an English variant
   - "Rust 异步编程" → also search "Rust async programming"
   - "配网可靠性指标" → also search "distribution network reliability indices"

3. **Intent-specific sub-query splitting**:
   - **Comparison**: Split into "X vs Y" + "X advantages" + "Y advantages"
   - **Exploratory**: Split into "X overview" + "X ecosystem" + "X use cases"
   - **Status**: Append current year + "latest" + "update"

#### Layer Selection

Determine the appropriate layer based on intent classification:

| Query Type | Layer | Primary Tool |
|------------|-------|-------------|
| "How to use polars `group_by`?" | 0 | Context7 |
| "What is WAL mode in SQLite?" | 1 | web_search.py |
| "Compare SQLite vs DuckDB for analytics" | 2 | web_search.py + web_fetch.py |
| "Best architecture for real-time reliability monitoring" | 2 | Multiple web_search.py + web_fetch.py rounds |

### Phase 2: Search Execution

1. **Start at the lowest sufficient layer** -- don't jump to Layer 2 for a simple API question
2. **Escalate if needed** -- if Layer 0 returns nothing, try Layer 1; if Layer 1 is too shallow, escalate to Layer 2
3. **Combine tools within a layer** -- Layer 2 uses web_search for discovery + web_fetch for full content
4. **Iterative retrieval** -- if first-round results don't meet needs, adjust query terms and retry (never abandon)

### Phase 3: Result Synthesis

#### Result Size Tiers

Adapt output format based on result volume:

- **Small (<=5 results)**: List each result individually with source label
- **Medium (5-15 results)**: Cluster by topic/theme, provide per-cluster summary
- **Large (15+ results)**: High-level overview + Top 5 most relevant + "dig deeper" pointers

#### Confidence Expression

Match confidence level to source quality:

- **Multi-source consistent + fresh** → State directly as fact
- **Single source or older** → Attribute explicitly: "According to [source], ..."
- **Conflicting or uncertain** → Flag explicitly: "There are differing views: A states ..., while B states ..."

#### Standing Rules

1. **Timeliness annotation**: For time-sensitive information, always note source and date
2. **Citation format**: Output must include source URLs in `[title](URL)` format

---

## Combination Patterns (Layer 2 Pipelines)

### Pattern A: Search-then-Fetch

Use when you need multiple sources with full content from key URLs.

```text
Step 1: web_search.py "<query>"
        → Returns structured results: titles, URLs, snippets

Step 2: Identify 2-3 most relevant URLs from results

Step 3: web_fetch.py "<url1>"
        web_fetch.py "<url2>"
        → Full Markdown content for deep reading

Step 4: Synthesize findings, cite all sources
```

### Pattern B: Multi-Round Research

Use for architecture decisions or complex trade-offs requiring comprehensive analysis.

```text
Step 1: web_search.py "<broad query>"
        → Returns initial results with URLs

Step 2: web_fetch.py on key URLs for full content

Step 3: web_search.py "<refined follow-up query>"
        → Fills gaps from initial round

Step 4: web_fetch.py on additional URLs

Step 5: Synthesize into decision recommendation with evidence
```

### Pattern C: Platform-Targeted Code Search

Use when searching for code examples on specific platforms.

```text
Step 1: web_search.py "<query>" --platform github
        → Returns code-focused results from GitHub

Step 2: web_fetch.py "<repo-url>" for full implementation details

Step 3: Adapt patterns to project context
```

---

## Fallback Degradation

### Degradation Matrix

| Layer | Primary Tool | Fallback | When to Degrade |
|-------|-------------|----------|-----------------|
| 0 | Context7 | web_search.py | Library not in Context7 index, or no relevant results |
| 1 | web_search.py | Agent's own knowledge (with caveat) | GROK_API_KEY not configured |
| 2 | web_search.py + web_fetch.py | Context7 + agent knowledge | Both API keys missing |
| — | web_fetch.py | (no equivalent) | Try all 5 tiers; anti-bot domains skip tier 1-2; MinerU as last resort; if all fail, ask user to provide content |

### Degradation Rules

1. **Grok API key not configured** (GROK_API_KEY missing):
   - `web_search.py` → fall back to Context7 for library queries, or agent knowledge with explicit caveat
   - `web_fetch.py` still works (uses Jina/Cloudflare/Tavily/MinerU, not Grok API)
   - `web_map.py` still works (uses Tavily API)

2. **Context7 library not found**:
   - `resolve-library-id` returns no match → `web_search.py` with library name + question
   - Or target official docs site directly with `web_fetch.py`

3. **All external tools unavailable**:
   - Fall back to agent's own knowledge (with explicit caveat about knowledge cutoff)
   - Ask user to provide the needed information

---

## Error Handling

| Error Type | Affected Tool | Diagnosis | Recovery |
|------------|--------------|-----------|----------|
| Connection failure | Grok Scripts | Check if GROK_API_URL / GROK_API_KEY are set | Fall back to Context7 or agent knowledge |
| Library not found | Context7 | `resolve-library-id` returns no match | Use web_search.py |
| No search results | Any | Query too specific or niche | Broaden search terms, try different layer |
| Web fetch timeout | web_fetch.py | URL inaccessible or slow | Try alternative sources or ask user |
| Anti-bot domain | web_fetch.py | Known anti-bot site (zhihu, weixin, etc.) | Tier 1-2 auto-skipped; MinerU (tier 5) as last resort; if all fail, ask user to provide content |
| Content truncated | web_fetch.py | Target page too large | Fetch in segments or direct user to visit |

---

## Anti-Patterns

| Wrong | Right |
|-------|-------|
| No source citation after search | Output must include `[source](URL)` references |
| Abandon after single search failure | Retry at least once with adjusted parameters or different layer |
| Assume web content without fetching | Must call `web_fetch.py` to verify critical information |
| Ignore timeliness of search results | Time-sensitive information must include dates |
| Use external search tools for project code | Use Grep / codebase-retrieval for project code |
| Use Augment to search general web information | Use Grok Scripts for general web info |
| Jump to Layer 2 for a simple API question | Start at lowest sufficient layer (Layer 0 for library docs) |
| Ignore Context7 for known library queries | Always try Context7 first for library/framework docs (free, fast) |

---

## Real Project Examples

### Example 1: Library API Lookup (Layer 0)

**Need**: "What is the new `group_by` syntax in polars 0.20?"

**Workflow**:
```text
1. mcp__context7__resolve-library-id(libraryName="polars", query="group_by syntax")
2. mcp__context7__query-docs(libraryId="<id>", query="group_by new syntax 0.20")
3. If Context7 has no results → web_search.py "polars 0.20 group_by new syntax"
```

### Example 2: Quick Fact Check (Layer 1)

**Need**: "Are there known issues with SQLite WAL mode on WSL?"

**Workflow**:
```text
1. web_search.py "SQLite WAL mode WSL known issues"
2. If results reference specific discussions → web_fetch.py on key URLs for full content
3. Output conclusion + source links
```

### Example 3: Multi-Source Comparison (Layer 2)

**Need**: "Compare polars vs pandas for large CSV processing performance"

**Workflow**:
```text
1. web_search.py "polars vs pandas large CSV processing performance benchmarks"
2. Pick 2-3 most relevant URLs from results (benchmark blog, official docs)
3. web_fetch.py on each for full content
4. Synthesize comparison table with citations
```

### Example 4: Architecture Decision (Layer 2 Multi-Round)

**Need**: "Should we use SQLite or DuckDB for analytical queries on reliability data with 10M+ rows?"

**Workflow**:
```text
1. web_search.py "SQLite vs DuckDB analytical queries 10M rows benchmarks"
2. web_fetch.py on cited benchmark URLs for verification
3. web_search.py "DuckDB Python polars integration" (follow-up)
4. Synthesize into decision recommendation
```

### Example 5: Platform-Targeted Code Search

**Need**: "Find open-source FMEA calculation implementations in Python"

**Workflow**:
```text
1. web_search.py "FMEA failure mode effects analysis Python implementation" --platform github
2. web_fetch.py on promising repository URLs
3. Analyze code patterns for adaptation
```

---

## Agent Tool Configuration (Current State)

| Agent | Augment | Morph | Context7 | Grok Scripts | IDE | Recommended Layers |
|-------|:---:|:---:|:---:|:---:|:---:|-----|
| research | ✅ (fallback) | ✅ (warpgrep) | ✅ | ✅ (all) | — | All layers (0-2) |
| implement | ✅ (fallback) | ✅ (warpgrep, edit_file) | ✅ | ✅ (search, fetch) | ✅ | Layer 0, Grok only |
| check | ✅ (fallback) | ✅ (warpgrep, edit_file) | — | — | ✅ | Local only |
| debug | ✅ (fallback) | ✅ (warpgrep, edit_file) | ✅ | ✅ (search, fetch) | ✅ | Layer 0, Grok only |
| dispatch | ✅ | — | — | — | — | Local only |
| plan | ✅ (fallback) | ✅ (warpgrep) | ✅ | — | — | Layer 0 only |

> **Tool Notes:**
> - **Augment** (`codebase-retrieval`): Deep semantic understanding, use when `warpgrep` unavailable
> - **Morph** (`warpgrep_codebase_search`): Broad semantic search, multi-turn parallel, preferred for large codebases
> - **Morph** (`edit_file`): Fast partial file edits, preferred over Edit/Write
> - Grok Scripts are called via the Bash tool; no MCP tool declaration needed. Any agent with Bash permission can use them.
> - Only the research agent has access to all layers. Other agents should escalate to research agent for Layer 1-2 needs when possible.

---

## Three-Layer External Search Architecture

```text
Layer 0: Library Docs (free, fastest)
  Tools: Context7 (resolve-library-id → query-docs)
  Trigger: Query targets a specific library/framework API or usage
  Fallback: web_search.py

Layer 1: Web Search (low cost)
  Tools: web_search.py
  Trigger: Simple fact, concept explanation, quick lookup, news
  Fallback: Agent knowledge (with caveat)

Layer 2: Deep Research (comprehensive)
  Tools: web_search.py + web_fetch.py (search→fetch pipeline, multi-round)
  Trigger: Multiple sources needed, comparison, architecture decisions, complex research
  Fallback: Context7 + agent knowledge

Irreplaceable Capabilities (Grok Scripts only):
  → web_fetch.py: URL content extraction (5-tier Markdown fallback + unified Result Contract)
  → web_map.py: Site structure discovery
  → web_search.py --platform github: Platform-targeted code search
```

### Local Codebase Search (Separate from External)

```text
Local Layer: Codebase Search
  Tools: Grep, Glob, Read, Morph (warpgrep, edit_file), Augment (codebase-retrieval)
  Scope: src/, MATLAB/, .trellis/spec/

  - Grep: Exact match (known identifiers)
  - warpgrep: Broad semantic search (multi-turn parallel, preferred)
  - codebase-retrieval: Deep semantic understanding (fallback if warpgrep unavailable)
  - edit_file: Fast partial file edits (preferred over Edit/Write)
  - Glob: Filename pattern search
  - Read: File content reading
```

**Fallback Strategy**: If `mcp__morph-mcp__warpgrep_codebase_search` is unavailable, use `mcp__augment-context-engine__codebase-retrieval`. If `mcp__morph-mcp__edit_file` is unavailable, use standard Edit or Write tools.

---

## Standalone Scripts

Project-local scripts are located in `.trellis/scripts/search/`, invoked via Bash:

### web_fetch.py — 5-tier Markdown Fetcher

Fetches URL content and converts to Markdown with 5-tier fallback, anti-bot domain awareness, and unified Result Contract output:

1. **Tier 1**: `Accept: text/markdown` content negotiation (Cloudflare Markdown for Agents, free)
2. **Tier 2**: Jina Reader `r.jina.ai` (free, JS rendering via headless Chrome, ReaderLM-v2; optional JINA_API_KEY for higher rate limit)
3. **Tier 3**: Cloudflare Workers AI `toMarkdown` REST API (requires CF_ACCOUNT_ID + CF_API_TOKEN)
4. **Tier 4**: Tavily Extract API (requires TAVILY_API_KEY)
5. **Tier 5**: MinerU API (requires MINERU_TOKEN) — async task-based extraction via `MinerU-HTML` model, heavy but reliable last resort

**Anti-bot domain awareness**: URLs matching a built-in whitelist (zhihu, weixin, xiaohongshu, linux.do, douban, bilibili) skip Tier 1-2 to avoid ~40s of guaranteed timeout. All tiers apply heuristic content validation (length check, block marker detection for CAPTCHA/403/challenge pages) — garbage content is never returned as success.

**Unified Result Contract** (`--json` mode): Returns a consistent JSON structure regardless of which tier succeeded: `{"ok", "source_url", "engine", "tier", "markdown", "notes"}`.

```bash
# Plain markdown (default)
uv run .trellis/scripts/search/web_fetch.py "https://example.com/page"

# Unified Result Contract (JSON)
uv run .trellis/scripts/search/web_fetch.py "https://example.com/page" --json

# JSON with markdown truncation
uv run .trellis/scripts/search/web_fetch.py "https://example.com/page" --json --max-chars 20000
```

### web_search.py — Grok API Search

Performs web search via Grok API, returns structured results.

```bash
uv run .trellis/scripts/search/web_search.py "query"
uv run .trellis/scripts/search/web_search.py "query" --platform github
```

### web_map.py — Site Structure Discovery

Discovers website link structure via Tavily Map API.

```bash
uv run .trellis/scripts/search/web_map.py "https://docs.example.com"
uv run .trellis/scripts/search/web_map.py "https://docs.example.com" --depth 2 --limit 100
```

---

## Summary: Quick Decision Guide

- **In the project** → Grep (exact) / warpgrep (semantic) / codebase-retrieval (fallback) / Read
- **Library/framework docs** → Context7 (Layer 0, free and fast)
- **Quick fact or concept** → web_search.py (Layer 1)
- **Multiple sources / comparison** → web_search.py + web_fetch.py (Layer 2)
- **Deep research** → Multiple web_search.py + web_fetch.py rounds (Layer 2)
- **Code examples from GitHub** → `web_search.py --platform github`
- **Full content from a URL** → `web_fetch.py`

**Default escalation**: Context7 → web_search.py → web_search.py + web_fetch.py (multi-round)

> **Always cite sources with `[title](URL)` format.**
