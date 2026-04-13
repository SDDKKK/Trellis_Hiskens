#!/usr/bin/env python3
"""Web Fetch — 6-tier markdown fetcher with anti-bot domain awareness.

Usage:
  python3 web_fetch.py <url>              # plain markdown (default)
  python3 web_fetch.py <url> --json       # unified Result Contract (JSON)
  python3 web_fetch.py <url> --json --max-chars 20000  # truncate markdown

Tier 1: Accept: text/markdown content negotiation (Cloudflare Markdown for Agents)
Tier 2: Jina Reader r.jina.ai (free, JS rendering, ReaderLM-v2)
Tier 3: Cloudflare Workers AI toMarkdown REST API (if CF_ACCOUNT_ID + CF_API_TOKEN set)
Tier 4: Tavily Extract API (if TAVILY_API_KEY set)
Tier 4.5: Firecrawl Scrape API (if FIRECRAWL_API_KEY set) — fallback from Tavily
Tier 5: MinerU API (if MINERU_TOKEN set) — async task-based, heavy but reliable

Anti-bot domains (zhihu, weixin, xiaohongshu, linux.do, etc.) skip Tier 1-2
to avoid wasting ~40s on guaranteed failures.

Result Contract (--json mode, aligned with content-extract SKILL):
  {
    "ok": true/false,
    "source_url": "...",
    "engine": "content-negotiation|jina-reader|cloudflare-workers-ai|tavily|firecrawl|mineru",
    "tier": 1-5,
    "markdown": "...",
    "notes": ["..."]
  }
"""

import io
import json
import os
import sys
import time
import zipfile
from urllib.parse import urlparse

# Domains known to block automated fetchers (Cloudflare challenge, login wall, etc.)
_ANTIBOT_DOMAINS = {
    "zhihu.com",
    "zhuanlan.zhihu.com",
    "mp.weixin.qq.com",
    "weixin.qq.com",
    "xiaohongshu.com",
    "xhslink.com",
    "linux.do",
    "douban.com",
    "bilibili.com",
}

# Heuristic markers indicating a failed/blocked fetch (case-insensitive check)
_BLOCK_MARKERS = (
    "just a moment",
    "请在微信客户端打开",
    "环境异常",
    "验证码",
    "完成验证",
    "拖动下方滑块",
    "访问过于频繁",
    "captcha",
    "please verify",
    "access denied",
    "checking your browser",
)


def _is_antibot(url: str) -> bool:
    host = urlparse(url).hostname or ""
    return any(host == d or host.endswith(f".{d}") for d in _ANTIBOT_DOMAINS)


def _looks_blocked(text: str) -> bool:
    if len(text) < 200:
        return True
    low = text[:2000].lower()
    return any(m in low for m in _BLOCK_MARKERS) or "returned error" in text


def _ok(url: str, engine: str, tier: int, md: str) -> dict:
    """Build a successful Result Contract."""
    return {
        "ok": True,
        "source_url": url,
        "engine": engine,
        "tier": tier,
        "markdown": md,
        "notes": [],
    }


def _fail(url: str, notes: list[str]) -> dict:
    """Build a failed Result Contract."""
    return {
        "ok": False,
        "source_url": url,
        "engine": None,
        "tier": None,
        "markdown": "",
        "notes": notes,
    }


def fetch_result(url: str, *, quiet: bool = False) -> dict:
    """Fetch URL content as markdown, returning a unified Result Contract dict.

    Args:
        url: URL to fetch
        quiet: If True, suppress all diagnostic output to stderr (useful for --json mode)
    """
    import urllib.error
    import urllib.request

    antibot = _is_antibot(url)
    notes: list[str] = []
    if antibot:
        notes.append(
            f"anti-bot domain detected ({urlparse(url).hostname}), skipping tier 1-2"
        )
        if not quiet:
            print(
                f"[antibot-domain] skipping tier 1-2 for {urlparse(url).hostname}",
                file=sys.stderr,
            )

    # --- Tier 1: Content negotiation (skip for antibot domains) ---
    if not antibot:
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "Accept": "text/markdown, text/html;q=0.9",
                    "User-Agent": "GrokSearch-Skill/1.0",
                },
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                ct = resp.headers.get("Content-Type", "")
                if "text/markdown" in ct:
                    md = resp.read().decode("utf-8", errors="replace")
                    if not _looks_blocked(md):
                        if not quiet:
                            print(
                                f"[tier1: content-negotiation, tokens={resp.headers.get('x-markdown-tokens', '?')}]",
                                file=sys.stderr,
                            )
                        return _ok(url, "content-negotiation", 1, md)
        except Exception:
            pass

    # --- Tier 2: Jina Reader (skip for antibot domains) ---
    if not antibot:
        jina_url = f"https://r.jina.ai/{url}"
        jina_headers = {
            "Accept": "text/markdown",
            "User-Agent": "GrokSearch-Skill/1.0",
            "X-Remove-Images": "true",
            "X-Timeout": "25",
        }
        jina_key = os.environ.get("JINA_API_KEY")
        if jina_key:
            jina_headers["Authorization"] = f"Bearer {jina_key}"
        try:
            req = urllib.request.Request(jina_url, headers=jina_headers)
            with urllib.request.urlopen(req, timeout=35) as resp:
                md = resp.read().decode("utf-8", errors="replace")
                if md and not _looks_blocked(md):
                    if not quiet:
                        print("[tier2: jina-reader]", file=sys.stderr)
                    return _ok(url, "jina-reader", 2, md)
        except Exception:
            pass

    # --- Tier 3: Cloudflare Workers AI toMarkdown ---
    cf_account = os.environ.get("CF_ACCOUNT_ID")
    cf_token = os.environ.get("CF_API_TOKEN")
    if cf_account and cf_token:
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "GrokSearch-Skill/1.0"}
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                ct = resp.headers.get("Content-Type", "")
                if "text/html" in ct:
                    html_bytes = resp.read()
                    boundary = "----GrokSkillBoundary"
                    body = (
                        (
                            f"--{boundary}\r\n"
                            f'Content-Disposition: form-data; name="file"; filename="page.html"\r\n'
                            f"Content-Type: text/html\r\n\r\n"
                        ).encode()
                        + html_bytes
                        + f"\r\n--{boundary}--\r\n".encode()
                    )
                    api_url = f"https://api.cloudflare.com/client/v4/accounts/{cf_account}/ai/tomarkdown"
                    req2 = urllib.request.Request(
                        api_url,
                        data=body,
                        headers={
                            "Authorization": f"Bearer {cf_token}",
                            "Content-Type": f"multipart/form-data; boundary={boundary}",
                        },
                    )
                    with urllib.request.urlopen(req2, timeout=30) as resp2:
                        data = json.loads(resp2.read())
                        results = data.get("result", [])
                        if results and results[0].get("format") == "markdown":
                            md = results[0]["data"]
                            if not _looks_blocked(md):
                                if not quiet:
                                    print(
                                        "[tier3: cloudflare-workers-ai]",
                                        file=sys.stderr,
                                    )
                                return _ok(url, "cloudflare-workers-ai", 3, md)
        except Exception:
            pass

    # --- Tier 4: Tavily Extract ---
    tavily_key = os.environ.get("TAVILY_API_KEY")
    if tavily_key:
        try:
            tavily_url = os.environ.get("TAVILY_API_URL", "https://api.tavily.com")
            endpoint = f"{tavily_url.rstrip('/')}/extract"
            payload = json.dumps({"urls": [url], "format": "markdown"}).encode()
            req = urllib.request.Request(
                endpoint,
                data=payload,
                headers={
                    "Authorization": f"Bearer {tavily_key}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
                if data.get("results"):
                    md = data["results"][0].get("raw_content", "")
                    if md and not _looks_blocked(md):
                        if not quiet:
                            print("[tier4: tavily]", file=sys.stderr)
                        return _ok(url, "tavily", 4, md)
        except Exception:
            pass

    # --- Tier 4.5: Firecrawl Scrape (fallback from Tavily) ---
    firecrawl_key = os.environ.get("FIRECRAWL_API_KEY")
    if firecrawl_key:
        try:
            firecrawl_base = os.environ.get(
                "FIRECRAWL_API_URL", "https://api.firecrawl.dev/v2"
            ).rstrip("/")
            endpoint = f"{firecrawl_base}/scrape"
            payload = json.dumps(
                {
                    "url": url,
                    "formats": ["markdown"],
                    "timeout": 60000,
                }
            ).encode()
            req = urllib.request.Request(
                endpoint,
                data=payload,
                headers={
                    "Authorization": f"Bearer {firecrawl_key}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read())
                md = data.get("data", {}).get("markdown", "")
                if md and not _looks_blocked(md):
                    if not quiet:
                        print("[tier4.5: firecrawl]", file=sys.stderr)
                    return _ok(url, "firecrawl", 4, md)
        except Exception:
            pass

    # --- Tier 5: MinerU API (async task-based, heavy but reliable) ---
    mineru_token = os.environ.get("MINERU_TOKEN")
    if mineru_token:
        try:
            mineru_base = os.environ.get(
                "MINERU_API_BASE", "https://mineru.net"
            ).rstrip("/")
            task_payload = json.dumps(
                {
                    "url": url,
                    "model_version": "MinerU-HTML",
                    "language": "ch",
                    "is_ocr": False,
                }
            ).encode()
            req = urllib.request.Request(
                f"{mineru_base}/api/v4/extract/task",
                data=task_payload,
                headers={
                    "Authorization": f"Bearer {mineru_token}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                res = json.loads(resp.read())
            if res.get("code") != 0:
                raise RuntimeError(f"create_task: {res}")
            task_id = (res.get("data") or {}).get("task_id")
            if not task_id:
                raise RuntimeError(f"no task_id: {res}")

            # Poll until done (max 120s for a single page)
            poll_url = f"{mineru_base}/api/v4/extract/task/{task_id}"
            deadline = time.time() + 120
            while True:
                req = urllib.request.Request(
                    poll_url, headers={"Authorization": f"Bearer {mineru_token}"}
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read())
                state = (data.get("data") or {}).get("state")
                if state == "done":
                    break
                if state == "failed":
                    raise RuntimeError(
                        f"task failed: {(data.get('data') or {}).get('err_msg', '?')}"
                    )
                if time.time() > deadline:
                    raise RuntimeError(f"poll timeout (state={state})")
                time.sleep(3)

            # Download zip and extract markdown
            full_zip_url = (data.get("data") or {}).get("full_zip_url")
            if not full_zip_url:
                raise RuntimeError("no full_zip_url")
            req = urllib.request.Request(full_zip_url)
            with urllib.request.urlopen(req, timeout=120) as resp:
                zip_bytes = resp.read()
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                md_names = [
                    n for n in zf.namelist() if n.lower().endswith((".md", ".markdown"))
                ]
                best, best_size = None, 0
                for n in md_names:
                    low = n.lower()
                    if "readme" in low or "layout" in low or "debug" in low:
                        continue
                    sz = zf.getinfo(n).file_size
                    if sz > best_size:
                        best, best_size = n, sz
                if not best and md_names:
                    best = md_names[0]
                if best:
                    md = zf.read(best).decode("utf-8", errors="replace")
                    if not _looks_blocked(md):
                        if not quiet:
                            print("[tier5: mineru]", file=sys.stderr)
                        return _ok(url, "mineru", 5, md)
        except Exception as e:
            if not quiet:
                print(f"[tier5: mineru failed] {e}", file=sys.stderr)
            notes.append(f"mineru failed: {e}")

    # All tiers exhausted
    if antibot:
        host = urlparse(url).hostname or ""
        notes.append(
            f"{host} is an anti-bot domain; ask user to provide content or use browser-based extractor"
        )
    else:
        notes.append(
            "all tiers failed (CF content-negotiation, Jina Reader, CF Workers AI, Tavily, Firecrawl, MinerU)"
        )
    return _fail(url, notes)


def fetch_sync(url: str, *, quiet: bool = False) -> str:
    """Backward-compatible wrapper: returns markdown string or error message.

    Args:
        url: URL to fetch
        quiet: If True, suppress all diagnostic output to stderr
    """
    result = fetch_result(url, quiet=quiet)
    if result["ok"]:
        return result["markdown"]
    return "Error: " + "; ".join(result["notes"])


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(
        description="5-tier markdown fetcher with anti-bot domain awareness"
    )
    ap.add_argument("url", help="URL to fetch")
    ap.add_argument(
        "--json",
        action="store_true",
        dest="json_mode",
        help="Output unified Result Contract as JSON (suppresses diagnostic output)",
    )
    ap.add_argument(
        "--max-chars",
        type=int,
        default=0,
        help="Truncate markdown to N chars in JSON mode (0=unlimited)",
    )
    args = ap.parse_args()

    if args.json_mode:
        # In JSON mode, suppress all diagnostic output to stderr for clean JSON parsing
        result = fetch_result(args.url, quiet=True)
        if args.max_chars and result["ok"] and len(result["markdown"]) > args.max_chars:
            result["markdown"] = (
                result["markdown"][: args.max_chars] + "\n\n[TRUNCATED]"
            )
            result["notes"].append(f"markdown truncated to {args.max_chars} chars")
        sys.stdout.write(json.dumps(result, ensure_ascii=False))
    else:
        print(fetch_sync(args.url))
