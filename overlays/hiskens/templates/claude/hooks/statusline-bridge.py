#!/usr/bin/env python3
"""
Statusline Bridge - Transparent proxy that wraps existing statusline commands.

Writes context_window metrics to /tmp/claude-ctx-{session_id}.json (bridge file)
for context-monitor.py to consume, then delegates display to the inner statusline
command (e.g., CCR statusline).

Architecture:
    Claude Code → statusline-bridge.py
                    ├─ writes bridge file (silent)
                    └─ calls inner command → stdout (display)

Configuration in ~/.claude/settings.json (USER-level, not project-level):
    "statusLine": {
        "type": "command",
        "command": "python3 /path/to/statusline-bridge.py"
    }

Inner command resolution (first match wins):
    1. TRELLIS_INNER_STATUSLINE env var
    2. Project-local `.claude/hooks/statusline.py`
    3. Auto-detect: `ccr statusline` if ccr is on PATH
    4. Fallback: built-in display [Model] Ctx:XX% $X.XX

Bridge file: /tmp/claude-ctx-{session_id}.json
"""

import json
import os
import shutil
import subprocess
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

WARNING_THRESHOLD = 35
CRITICAL_THRESHOLD = 25

RED = "\033[31m"
YELLOW = "\033[33m"
DIM = "\033[2m"
RESET = "\033[0m"


def write_bridge(data: dict) -> None:
    """Write context metrics to bridge file for context-monitor.py."""
    session_id = data.get("session_id", "")
    ctx = data.get("context_window") or {}
    remaining = ctx.get("remaining_percentage")

    if not session_id or remaining is None:
        return

    bridge_path = Path(f"/tmp/claude-ctx-{session_id}.json")

    # Preserve debounce state from existing bridge file
    last_warned_pct = None
    if bridge_path.exists():
        try:
            old = json.loads(bridge_path.read_text(encoding="utf-8"))
            last_warned_pct = old.get("last_warned_pct")
        except (json.JSONDecodeError, OSError):
            pass

    bridge_data = {
        "session_id": session_id,
        "remaining_pct": remaining,
        "used_pct": ctx.get("used_percentage"),
        "model": data.get("model", {}).get("display_name", ""),
        "timestamp": int(time.time()),
        "last_warned_pct": last_warned_pct,
    }
    try:
        bridge_path.write_text(
            json.dumps(bridge_data, ensure_ascii=False), encoding="utf-8"
        )
    except OSError:
        pass


def find_inner_command() -> list[str] | None:
    """Find the inner statusline command to delegate display to."""
    # 1. Explicit env var
    inner = os.environ.get("TRELLIS_INNER_STATUSLINE")
    if inner:
        return inner.split()

    # 2. Prefer project-local Trellis statusline implementation
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if project_dir:
        project_statusline = Path(project_dir) / ".claude" / "hooks" / "statusline.py"
        if project_statusline.is_file():
            return [sys.executable, str(project_statusline)]

    # 3. Auto-detect ccr
    ccr = shutil.which("ccr")
    if ccr:
        return [ccr, "statusline"]

    return None


def fallback_display(data: dict) -> None:
    """Built-in statusline when no inner command is available."""
    model = data.get("model", {}).get("display_name", "Claude")
    ctx = data.get("context_window") or {}
    remaining = ctx.get("remaining_percentage")
    cost = (data.get("cost") or {}).get("total_cost_usd")

    parts = [f"[{model}]"]
    if remaining is not None:
        if remaining <= CRITICAL_THRESHOLD:
            parts.append(f"{RED}Ctx:{remaining:.0f}%{RESET}")
        elif remaining <= WARNING_THRESHOLD:
            parts.append(f"{YELLOW}Ctx:{remaining:.0f}%{RESET}")
        else:
            parts.append(f"{DIM}Ctx:{remaining:.0f}%{RESET}")
    if cost is not None:
        parts.append(f"{DIM}${cost:.2f}{RESET}")
    print(" ".join(parts))


def main() -> None:
    try:
        raw = sys.stdin.buffer.read()
        data = json.loads(raw)
    except (json.JSONDecodeError, EOFError):
        print("Trellis")
        return

    # 1. Write bridge file (silent, never fails)
    write_bridge(data)

    # 2. Delegate display to inner command
    inner_cmd = find_inner_command()
    if inner_cmd:
        try:
            result = subprocess.run(
                inner_cmd,
                input=raw,
                capture_output=True,
                timeout=5,
            )
            output = result.stdout.decode("utf-8", errors="replace").strip()
            if output:
                print(output)
                return
        except (subprocess.TimeoutExpired, OSError):
            pass

    # 3. Fallback display
    fallback_display(data)


if __name__ == "__main__":
    main()
