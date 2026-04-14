# Search Scripts API Configuration

> Required environment variables for `.trellis/scripts/search/` scripts.

---

## Environment Variables

| Variable | Required by | Description |
|----------|-------------|-------------|
| `GROK_API_URL` | `web_search.py` | Grok API base URL (e.g., `https://api.x.ai/v1`) |
| `GROK_API_KEY` | `web_search.py` | Grok API key |
| `JINA_API_KEY` | `web_fetch.py` (tier 2) | Jina Reader API key (optional, free tier: 20 RPM without key, 500 RPM with free key) |
| `CF_ACCOUNT_ID` | `web_fetch.py` (tier 3) | Cloudflare account ID |
| `CF_API_TOKEN` | `web_fetch.py` (tier 3) | Cloudflare Workers AI API token |
| `TAVILY_API_KEY` | `web_fetch.py` (tier 4), `web_map.py` | Tavily API key |
| `TAVILY_API_URL` | `web_map.py` | Tavily API URL (default: `https://api.tavily.com`) |
| `FIRECRAWL_API_KEY` | `web_fetch.py` (tier 4.5) | Firecrawl API key (fallback from Tavily) |
| `FIRECRAWL_API_URL` | `web_fetch.py` (tier 4.5) | Firecrawl API URL (default: `https://api.firecrawl.dev/v2`) |
| `MINERU_TOKEN` | `web_fetch.py` (tier 5) | MinerU API Bearer token |
| `MINERU_API_BASE` | `web_fetch.py` (tier 5) | MinerU API base URL (default: `https://mineru.net`) |

---

## How to Get API Keys

### Grok API (for web_search.py)

- URL: https://console.x.ai/
- Free tier available
- Provides web search via Grok models
- Default model: `grok-4.20-multi-agent`; endpoint: `/v1/responses` with native `web_search` tool

### Jina Reader (for web_fetch.py tier 2)

- URL: https://jina.ai/reader/
- Free: 20 RPM without key, 500 RPM with free key
- Provides URL-to-Markdown via headless Chrome + ReaderLM-v2

### Cloudflare Workers AI (for web_fetch.py tier 3)

- URL: https://dash.cloudflare.com
- Workers AI free tier available
- Provides HTML-to-Markdown conversion via `toMarkdown` API

### Tavily (for web_fetch.py tier 4 + web_map.py)

- URL: https://tavily.com
- 1000 free API credits per month
- Provides web content extraction and site mapping

### MinerU (for web_fetch.py tier 5)

- URL: https://mineru.net/apiManage/token
- 2000 pages/day highest priority quota
- Async task-based extraction, heavy but reliable last resort for anti-bot domains
- Note: GitHub/AWS URLs may timeout due to network restrictions (MinerU servers are in China)

---

## Configuration Methods

### Option A: Shell Profile

Add to `~/.bashrc` or `~/.zshrc`:

```bash
export GROK_API_URL="https://api.x.ai/v1"
export GROK_API_KEY="your-grok-api-key"
export JINA_API_KEY="your-jina-api-key"
export CF_ACCOUNT_ID="your-cloudflare-account-id"
export CF_API_TOKEN="your-cloudflare-api-token"
export TAVILY_API_KEY="your-tavily-api-key"
export MINERU_TOKEN="your-mineru-api-token"
```

### Option B: Claude Code Settings

Add to `.claude/settings.json` under the `env` section:

```json
{
  "env": {
    "GROK_API_URL": "https://api.x.ai/v1",
    "GROK_API_KEY": "your-grok-api-key",
    "JINA_API_KEY": "your-jina-api-key",
    "CF_ACCOUNT_ID": "your-cloudflare-account-id",
    "CF_API_TOKEN": "your-cloudflare-api-token",
    "TAVILY_API_KEY": "your-tavily-api-key",
    "MINERU_TOKEN": "your-mineru-api-token"
  }
}
```

---

## Verification

### Check Which APIs Are Configured

```bash
echo "GROK_API_URL:   ${GROK_API_URL:-(not set)}"
echo "GROK_API_KEY:   ${GROK_API_KEY:-(not set)}"
echo "JINA_API_KEY:   ${JINA_API_KEY:-(not set)}"
echo "CF_ACCOUNT_ID:  ${CF_ACCOUNT_ID:-(not set)}"
echo "CF_API_TOKEN:   ${CF_API_TOKEN:-(not set)}"
echo "TAVILY_API_KEY: ${TAVILY_API_KEY:-(not set)}"
echo "MINERU_TOKEN:   ${MINERU_TOKEN:-(not set)}"
```

### Test Each Script

```bash
python3 .trellis/scripts/search/web_search.py "test" 2>&1 | head -5
python3 .trellis/scripts/search/web_fetch.py "https://example.com" 2>&1 | head -5
python3 .trellis/scripts/search/web_fetch.py "https://example.com" --json 2>/dev/null | python3 -m json.tool
python3 .trellis/scripts/search/web_map.py "https://example.com" 2>&1 | head -5
```

Expected: If API keys are not configured, you will see API key errors (not import errors or crashes).

---

## Minimum Viable Setup

Just `TAVILY_API_KEY` enables `web_fetch.py` (tier 4) + `web_map.py` -- the most critical capabilities for URL content extraction and site structure discovery.

`web_fetch.py` tier 1 (Cloudflare Markdown content negotiation) and tier 2 (Jina Reader, 20 RPM) work without any API keys.

---

## Script Capabilities by API

| Script | No API keys | +JINA_API_KEY | +TAVILY_API_KEY | +FIRECRAWL_API_KEY | +CF keys | +MINERU_TOKEN | All keys |
|--------|:-----------:|:-------------:|:---------------:|:-------------------:|:--------:|:-------------:|:--------:|
| `web_fetch.py` | Tier 1-2 (Jina free 20 RPM) | Tier 1-2 (500 RPM) | +Tier 4 | +Tier 4.5 (fallback) | +Tier 3 | +Tier 5 | All 6 tiers |
| `web_search.py` | Not functional | — | — | — | — | — | Full search |
| `web_map.py` | Not functional | — | Full mapping | — | — | — | Full mapping |
