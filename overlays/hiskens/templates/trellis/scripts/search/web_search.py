#!/usr/bin/env python3
"""Web Search — Grok API search via Responses API with native web_search tool.

Usage: python3 web_search.py <query> [--platform <platform>] [--model <model>]

Requires: GROK_API_URL, GROK_API_KEY
"""

import json
import os
import sys
import urllib.request
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common  # noqa: E402

SEARCH_PROMPT = (
    "Search the web for the following query and return structured results "
    "with title, URL, snippet, and source for each result."
)


def _has_web_search_evidence(data: dict) -> bool:
    """Check if the response contains evidence that web_search tool was invoked."""
    if not isinstance(data, dict):
        return False
    output = data.get("output", [])
    if isinstance(output, list):
        for item in output:
            if isinstance(item, dict) and item.get("type") == "web_search_call":
                return True

    usage = data.get("usage", {})
    if isinstance(usage, dict):
        num_tools = usage.get("num_server_side_tools_used")
        if isinstance(num_tools, int) and num_tools > 0:
            return True
        details = usage.get("server_side_tool_usage_details", {})
        if isinstance(details, dict):
            web_search_calls = details.get("web_search_calls")
            if isinstance(web_search_calls, int) and web_search_calls > 0:
                return True

    return False


def _extract_text(data: dict) -> str:
    """Defensively extract final message text from Responses API output."""
    parts: list[str] = []
    if not isinstance(data, dict):
        return ""
    output = data.get("output", [])
    if not isinstance(output, list):
        return ""
    for item in output:
        if isinstance(item, dict) and item.get("type") == "message":
            content = item.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "output_text":
                        text = block.get("text", "")
                        if isinstance(text, str) and text:
                            parts.append(text)
    return "\n".join(parts)


def _extract_sources(data: dict) -> list[dict]:
    """Extract and deduplicate sources from a Responses API result.

    Two known locations (proxy-dependent):
    1. ``output[i].type == "web_search_call"`` → ``action.sources[]`` (may be empty)
    2. ``output[i].type == "message"`` → ``content[j].annotations[]``
       with ``type == "url_citation"`` (used by some proxies as the real source list)

    Deduplicates across both by URL, preserving first-seen order.
    When annotation title is a pure citation index (e.g. "1", "2"), falls back
    to the URL hostname for readability.
    """
    seen: set[str] = set()
    sources: list[dict] = []
    if not isinstance(data, dict):
        return sources

    def _add(url: str, title: str | None) -> None:
        if not url or url in seen:
            return
        seen.add(url)
        clean_title = (title or "").strip()
        # A bare citation index like "1" / "2" isn't a useful title
        if not clean_title or clean_title.isdigit():
            clean_title = urlparse(url).hostname or url
        sources.append({"title": clean_title, "url": url})

    output = data.get("output", [])
    if not isinstance(output, list):
        return sources

    for item in output:
        if not isinstance(item, dict):
            continue
        item_type = item.get("type")

        # Location 1: web_search_call.action.sources
        if item_type == "web_search_call":
            action = item.get("action", {})
            if isinstance(action, dict):
                raw_sources = action.get("sources", [])
                if isinstance(raw_sources, list):
                    for src in raw_sources:
                        if isinstance(src, dict):
                            _add(src.get("url", ""), src.get("title"))

        # Location 2: message.content[].annotations[]
        elif item_type == "message":
            content = item.get("content", [])
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                raw_annotations = block.get("annotations", [])
                if not isinstance(raw_annotations, list):
                    continue
                for ann in raw_annotations:
                    if not isinstance(ann, dict):
                        continue
                    if ann.get("type") == "url_citation":
                        _add(ann.get("url", ""), ann.get("title"))

    return sources


_DEGRADED_REASON = (
    "web_search tool invocation was NOT confirmed by response metadata — "
    "this content is likely generated from model training data alone, not from "
    "live web search. Downstream consumers MUST NOT treat URLs or claims as "
    "verified. Re-run with --strict to reject unverified responses outright."
)
_WARNING_LINE = f"> \u26a0 {_DEGRADED_REASON}"

_STRICT_REJECT_MSG = (
    "Error: web_search tool invocation not confirmed (strict mode). "
    "Content rejected; check that GROK_API_URL supports Responses API with "
    "the web_search tool, or drop --strict to accept degraded results with warning."
)


def _search_core(
    query: str, platform: str, model: str, *, strict: bool = False
) -> tuple[bool, str, bool, str]:
    """Shared search logic for both text-mode and json-mode entry points.

    Returns ``(ok, text, degraded, degraded_reason)``:

    - ``ok=False``: ``text`` is an "Error: ..." message; ``degraded`` is False
      and ``degraded_reason`` is empty. Callers should surface ``text`` as-is.
    - ``ok=True, degraded=False``: ``text`` is the model response with an
      optional ``## Sources`` section appended.
    - ``ok=True, degraded=True``: ``text`` begins with a blockquote warning
      line and ``degraded_reason`` is populated. Caller may expose the flag.

    When ``strict=True``, the "no web_search evidence" case is escalated from
    a soft degraded success to a hard ``ok=False`` rejection. This gives
    callers a per-invocation opt-in to the stricter anti-hallucination posture.
    """
    api_url = os.environ.get("GROK_API_URL")
    api_key = os.environ.get("GROK_API_KEY")
    if not api_url or not api_key:
        return (False, "Error: GROK_API_URL and GROK_API_KEY must be set", False, "")

    effective_model = model or os.environ.get("GROK_MODEL", "grok-4.20-multi-agent")
    full_query = f"{query} (platform: {platform})" if platform else query

    payload = json.dumps(
        {
            "model": effective_model,
            "instructions": SEARCH_PROMPT,
            "input": [{"role": "user", "content": full_query}],
            "tools": [{"type": "web_search"}],
        }
    ).encode()

    endpoint = _common.join_api_url(api_url.rstrip("/"), "/responses")
    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers=_common.bearer_headers(api_key),
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status != 200:
                return (False, f"Error: HTTP {resp.status}", False, "")
            data = json.loads(resp.read())
    except Exception as e:
        return (False, f"Error: {e}", False, "")
    if not isinstance(data, dict):
        return (False, "Error: malformed response payload", False, "")

    output = data.get("output", [])
    if not isinstance(output, list) or not output:
        return (False, "Error: empty response", False, "")

    text = _extract_text(data)
    if not text.strip():
        has_message = any(
            isinstance(item, dict) and item.get("type") == "message" for item in output
        )
        has_reasoning = any(
            isinstance(item, dict) and item.get("type") == "reasoning"
            for item in output
        )
        if has_message:
            return (False, "Error: malformed message, no text content", False, "")
        if has_reasoning:
            return (
                False,
                "Error: no final message, model did not produce output",
                False,
                "",
            )
        return (False, "Error: malformed message, no text content", False, "")

    degraded = False
    degraded_reason = ""
    if not _has_web_search_evidence(data):
        if strict:
            return (False, _STRICT_REJECT_MSG, False, "")
        text = f"{_WARNING_LINE}\n\n{text}"
        degraded = True
        degraded_reason = _DEGRADED_REASON

    sources = _extract_sources(data)
    if sources:
        lines = ["\n## Sources"]
        for src in sources:
            lines.append(f"- [{src['title']}]({src['url']})")
        text = text + "\n" + "\n".join(lines)

    return (True, text, degraded, degraded_reason)


def search(
    query: str, platform: str = "", model: str = "", *, strict: bool = False
) -> str:
    """Text-mode entry point. Returns markdown string (or ``Error: ...``).

    When ``strict=True``, responses lacking web_search tool evidence are
    rejected with an error message instead of returned with a warning.
    """
    _ok, text, _degraded, _reason = _search_core(query, platform, model, strict=strict)
    return text


def search_json(
    query: str, platform: str = "", model: str = "", *, strict: bool = False
) -> dict:
    """JSON-mode entry point. Returns a structured dict.

    Shape: ``{ok, query, result, [degraded, degraded_reason]}``. The last two
    keys are only present when the response was accepted but no web_search
    tool invocation could be confirmed.

    When ``strict=True``, the same "no evidence" case becomes ``ok=False``
    with ``result`` set to the strict rejection error message.
    """
    ok, text, degraded, degraded_reason = _search_core(
        query, platform, model, strict=strict
    )
    result: dict = {"ok": ok, "query": query, "result": text}
    if degraded:
        result["degraded"] = True
        result["degraded_reason"] = degraded_reason
    return result


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Grok API web search via Responses API")
    ap.add_argument("query", help="Search query")
    ap.add_argument(
        "--platform",
        default="",
        help=(
            "query hint concatenated into prompt; "
            "does NOT enforce hard filtering under Responses API web_search tool"
        ),
    )
    ap.add_argument(
        "--model",
        default="",
        help="Optional model ID for this request",
    )
    ap.add_argument(
        "--json",
        action="store_true",
        dest="json_mode",
        help="Output result as JSON",
    )
    ap.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Reject responses where the web_search tool invocation cannot be "
            "confirmed from response metadata (hard fail instead of soft "
            "degraded success). Use when downstream consumers cannot safely "
            "handle model-only answers."
        ),
    )
    args = ap.parse_args()

    if args.json_mode:
        output = search_json(args.query, args.platform, args.model, strict=args.strict)
        sys.stdout.write(json.dumps(output, ensure_ascii=False))
    else:
        print(search(args.query, args.platform, args.model, strict=args.strict))
