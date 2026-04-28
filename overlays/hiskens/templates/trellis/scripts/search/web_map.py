#!/usr/bin/env python3
"""Web Map — Tavily Map API for site structure discovery.

Usage: python3 web_map.py <url> [--depth N] [--breadth N] [--limit N] [--instructions "..."] [--timeout N]

Requires: TAVILY_API_KEY
"""

import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common  # noqa: E402


def map_site(
    url: str,
    depth: int = 1,
    breadth: int = 20,
    limit: int = 50,
    timeout: int = 150,
    instructions: str = "",
) -> str:
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return "Error: TAVILY_API_KEY must be set"

    tavily_url = os.environ.get("TAVILY_API_URL", "https://api.tavily.com")
    endpoint = f"{tavily_url.rstrip('/')}/map"

    body = {
        "url": url,
        "max_depth": depth,
        "max_breadth": breadth,
        "limit": limit,
        "timeout": timeout,
    }
    if instructions:
        body["instructions"] = instructions

    payload = json.dumps(body).encode()
    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    def _do_request():
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())

    try:
        data = _common.with_retry(_do_request, attempts=3, base_delay=1.0)
        return json.dumps(
            {
                "base_url": data.get("base_url", ""),
                "results": data.get("results", []),
                "response_time": data.get("response_time", 0),
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return f"Error: {e}"


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(
        description="Tavily Map API for site structure discovery"
    )
    ap.add_argument("url", help="Target URL")
    ap.add_argument("--depth", type=int, default=1, help="Max depth (default: 1)")
    ap.add_argument("--breadth", type=int, default=20, help="Max breadth (default: 20)")
    ap.add_argument("--limit", type=int, default=50, help="Max links (default: 50)")
    ap.add_argument(
        "--timeout",
        type=int,
        default=150,
        help="Request timeout in seconds (default: 150)",
    )
    ap.add_argument("--instructions", default="", help="Optional Tavily instructions")
    args = ap.parse_args()

    print(
        map_site(
            args.url,
            args.depth,
            args.breadth,
            args.limit,
            args.timeout,
            instructions=args.instructions,
        )
    )
