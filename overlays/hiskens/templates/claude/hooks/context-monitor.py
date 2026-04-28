#!/usr/bin/env python3
"""
Context Monitor - PostToolUse hook that warns agents about context exhaustion.

Inspired by GSD (get-shit-done) framework's context engineering approach.
Reads context metrics from bridge file written by statusline-bridge.py,
then injects warnings into agent context when thresholds are breached.

Problem solved:
    As Claude fills its context window, output quality degrades silently.
    At 50-70% usage, responses become less thorough. At 70%+, critical
    details are missed. This hook provides early warnings so agents can
    adjust their behavior (be more concise, finish current task, skip
    non-essential checks).

Architecture:
    statusline-bridge.py (Statusline hook)
        → writes /tmp/claude-ctx-{session_id}.json (bridge file)
    context-monitor.py (PostToolUse hook) [this file]
        → reads bridge file
        → injects additionalContext warnings when thresholds breached

Debounce logic:
    - WARNING fires once when remaining first drops below 35%
    - CRITICAL fires once when remaining first drops below 25%
    - Re-fires if remaining drops another 5% (progressive degradation)
    - Bridge file tracks last_warned_pct to prevent spam

Configuration in .claude/settings.json:
    "PostToolUse": [{
        "matcher": "",
        "hooks": [{
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/context-monitor.py\"",
            "timeout": 5
        }]
    }]
"""

import json
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# ==============================================================================
# Configuration
# ==============================================================================

WARNING_THRESHOLD = 35  # remaining <= 35% → suggest concise mode
CRITICAL_THRESHOLD = 25  # remaining <= 25% → force finish current step
BRIDGE_STALE_SECONDS = 120  # Ignore bridge file older than 2 minutes
REWARN_DROP_PCT = 5  # Re-warn if remaining dropped 5% since last warning

# ==============================================================================
# Warning messages
# ==============================================================================

WARNING_MSG = """
## Context Budget Warning

Context window is at {remaining:.0f}% remaining ({used:.0f}% used).
Quality may degrade as context fills up.

**Adjust your behavior:**
- Be more concise in outputs (skip verbose explanations)
- Prioritize completing the current task over perfection
- Avoid reading additional files unless absolutely necessary
- Skip non-essential checks or reviews
- Summarize findings instead of quoting full content
""".strip()

CRITICAL_MSG = """
## Context Budget CRITICAL

Context window is at {remaining:.0f}% remaining ({used:.0f}% used).
Quality degradation is likely occurring NOW.

**Immediate actions required:**
- FINISH your current step immediately
- Output results/findings NOW before context runs out
- Do NOT start new subtasks or explorations
- Do NOT read more files — work with what you have
- If in a verification loop, output your findings and stop
""".strip()


def main() -> None:
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        print("{}")
        sys.exit(0)

    # Only act on PostToolUse events
    event = hook_input.get("hook_event_name", "")
    if event != "PostToolUse":
        print("{}")
        sys.exit(0)

    session_id = hook_input.get("session_id", "")
    if not session_id:
        print("{}")
        sys.exit(0)

    # Read bridge file written by statusline-bridge.py
    bridge_path = Path(f"/tmp/claude-ctx-{session_id}.json")
    if not bridge_path.exists():
        print("{}")
        sys.exit(0)

    try:
        bridge_data = json.loads(bridge_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        print("{}")
        sys.exit(0)

    # Check staleness
    timestamp = bridge_data.get("timestamp", 0)
    if time.time() - timestamp > BRIDGE_STALE_SECONDS:
        print("{}")
        sys.exit(0)

    remaining = bridge_data.get("remaining_pct")
    used = bridge_data.get("used_pct", 0)
    if remaining is None:
        print("{}")
        sys.exit(0)

    # Determine severity
    if remaining > WARNING_THRESHOLD:
        print("{}")
        sys.exit(0)  # No warning needed

    is_critical = remaining <= CRITICAL_THRESHOLD

    # Debounce: check if we already warned at a similar level
    last_warned = bridge_data.get("last_warned_pct")
    if last_warned is not None:
        drop_since_last = last_warned - remaining
        # Skip if we haven't dropped enough since last warning
        # Exception: always fire when crossing from WARNING to CRITICAL
        was_critical = last_warned <= CRITICAL_THRESHOLD
        if drop_since_last < REWARN_DROP_PCT and (is_critical == was_critical):
            print("{}")
            sys.exit(0)

    # Build warning message
    if is_critical:
        message = CRITICAL_MSG.format(remaining=remaining, used=used)
    else:
        message = WARNING_MSG.format(remaining=remaining, used=used)

    # Update bridge file with last_warned_pct for debounce
    bridge_data["last_warned_pct"] = remaining
    try:
        bridge_path.write_text(
            json.dumps(bridge_data, ensure_ascii=False), encoding="utf-8"
        )
    except OSError:
        pass

    # Output additionalContext to inject warning into agent's context
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": message,
        }
    }
    print(json.dumps(output, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
