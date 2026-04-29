#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Codex PostToolUse Hook - Enhance context loading reliability for subagents.

Triggered after any Bash tool execution. When the command contains
'load-trellis-context.py', injects additionalContext to remind the agent
to follow the loaded specs and requirements.

Output format follows Codex hook protocol:
  stdout JSON → { hookSpecificOutput: { hookEventName: "PostToolUse", additionalContext: "..." } }
  or {} for non-matching commands (no-op)
"""

from __future__ import annotations

import json
import sys
import warnings

warnings.filterwarnings("ignore")

# Marker string to identify context loading commands
CONTEXT_LOADER_MARKER = "load-trellis-context.py"


def main() -> None:
    """Main entry point for PostToolUse hook."""
    # Read hook input from stdin
    try:
        hook_input = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        # Invalid JSON input - return empty response, don't block
        print("{}", flush=True)
        sys.exit(0)

    # Extract tool information
    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})
    command = tool_input.get("command", "")

    # Only process Bash tool calls
    if tool_name != "Bash":
        print("{}", flush=True)
        sys.exit(0)

    # Check if this is a context loading command
    if CONTEXT_LOADER_MARKER not in command:
        # Not a context loader command - return empty, don't interfere
        print("{}", flush=True)
        sys.exit(0)

    # This is a context loading command - inject additional context
    additional_context = (
        "Trellis context has been loaded above. "
        "IMPORTANT: Follow the specs and requirements strictly. "
        "Do NOT skip any requirement from prd.md. "
        "If you encounter issues, check the Memory section for known decisions and constraints."
    )

    result = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": additional_context,
        }
    }

    print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
