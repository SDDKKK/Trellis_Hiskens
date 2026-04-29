---
name: grok-search
description: Prefer grok-search MCP for live web search and source inspection; keep local Grok scripts as fallback for search and as the primary local route for fetch and site mapping. Use when needing to search the web, fetch URL content as clean markdown, or map a website's link structure.
---

# Grok Search

Standalone web research toolkit — search, fetch, site mapping.

Use this inside a Trellis project so the local `.trellis/scripts/search/` helpers are available.

Default routing:
- Live web search: prefer `mcp__grok-search__web_search`
- Source inspection / citation verification: `mcp__grok-search__get_sources`
- URL content extraction: `.trellis/scripts/search/web_fetch.py`
- Site structure discovery: `.trellis/scripts/search/web_map.py`
- Fallback search when MCP is unavailable: `.trellis/scripts/search/web_search.py`

The local scripts read API keys from environment variables. The MCP server is configured separately in the Claude CLI.

## Environment Variables

The variables below apply to the local fallback scripts:

| Variable | Used by | Description |
|----------|---------|-------------|
| `GROK_API_URL` | web_search (fallback) | Grok API base URL |
| `GROK_API_KEY` | web_search (fallback) | Grok API key |
| `TAVILY_API_KEY` | web_fetch (tier 3), web_map | Tavily API key |
| `TAVILY_API_URL` | web_map | Tavily URL (default: `https://api.tavily.com`) |
| `CF_ACCOUNT_ID` | web_fetch (tier 2) | Cloudflare account ID |
| `CF_API_TOKEN` | web_fetch (tier 2) | Cloudflare API token |

## Capabilities

### 1. Live Web Search — `grok-search` MCP

Preferred for real-time search, platform-targeted search, and multi-source discovery.

- Search: `mcp__grok-search__web_search`
- Inspect source list: `mcp__grok-search__get_sources`

Use this route first when you need current information or want inspectable citations.

### 2. Web Fetch — `.trellis/scripts/search/web_fetch.py`

Fetches a URL → returns clean markdown. 3-tier fallback:

1. `Accept: text/markdown` content negotiation (Cloudflare Markdown for Agents, free)
2. Cloudflare Workers AI `toMarkdown` REST API (if CF credentials set)
3. Tavily Extract (fallback)

```bash
python3 .trellis/scripts/search/web_fetch.py "https://example.com/page"
```

### 3. Fallback Web Search — `.trellis/scripts/search/web_search.py`

Fallback Grok API search when the MCP server is unavailable or not installed.

```bash
python3 .trellis/scripts/search/web_search.py "query"
python3 .trellis/scripts/search/web_search.py "query" --platform github
```

### 4. Web Map — `.trellis/scripts/search/web_map.py`

Tavily Map API — discover site link structure.

```bash
python3 .trellis/scripts/search/web_map.py "https://docs.example.com"
python3 .trellis/scripts/search/web_map.py "https://docs.example.com" --depth 2 --limit 100
```

## Usage Policy

Use this order by default:

1. For live search: `mcp__grok-search__web_search`
2. If you need to audit or cite the result set: `mcp__grok-search__get_sources`
3. If you need full page content: `python3 .trellis/scripts/search/web_fetch.py "<url>"`
4. If MCP is unavailable: `python3 .trellis/scripts/search/web_search.py "<query>"`
5. If you need site structure: `python3 .trellis/scripts/search/web_map.py "<url>"`

Treat `.trellis/scripts/search/web_search.py` as fallback, not the default entrypoint.
