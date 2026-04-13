#!/usr/bin/env python3
"""Web Map — Tavily Map API for site structure discovery.

Usage: python3 web_map.py <url> [--depth N] [--breadth N] [--limit N] [--instructions "..."]

Requires: TAVILY_API_KEY
"""

import json
import os
import sys
import urllib.request


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

    try:
        with urllib.request.urlopen(req, timeout=timeout + 10) as resp:
            data = json.loads(resp.read())
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
    if len(sys.argv) < 2:
        print(
            "Usage: web_map.py <url> [--depth N] [--breadth N] [--limit N]",
            file=sys.stderr,
        )
        sys.exit(1)

    args = sys.argv[1:]
    url = args[0]
    depth, breadth, limit, instructions = 1, 20, 50, ""
    i = 1
    while i < len(args):
        if args[i] == "--depth" and i + 1 < len(args):
            depth = int(args[i + 1])
            i += 2
        elif args[i] == "--breadth" and i + 1 < len(args):
            breadth = int(args[i + 1])
            i += 2
        elif args[i] == "--limit" and i + 1 < len(args):
            limit = int(args[i + 1])
            i += 2
        elif args[i] == "--instructions" and i + 1 < len(args):
            instructions = args[i + 1]
            i += 2
        else:
            i += 1

    print(map_site(url, depth, breadth, limit, instructions=instructions))
