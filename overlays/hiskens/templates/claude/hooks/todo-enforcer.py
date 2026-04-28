#!/usr/bin/env python3
"""
Todo Enforcer - Stop Hook for Main Session Todo Completion

Prevents the main session from stopping when there are incomplete todos
and an active task exists. Companion PostToolUse hook on TodoWrite
tracks todo state to a local state file.

Mechanism:
- PostToolUse on TodoWrite: updates todo snapshot in state file
- Stop event: reads state file, blocks if incomplete todos remain
- Backoff: MAX_CONTINUATIONS=3, then 5-minute cooldown

State file: .trellis/.todo-enforcer-state.json (gitignored)
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path

warnings.filterwarnings("ignore")

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Configuration
MAX_CONTINUATIONS = 3
COOLDOWN_MINUTES = 5
STATE_FILE = ".trellis/.todo-enforcer-state.json"
DIR_WORKFLOW = ".trellis"
FILE_CURRENT_TASK = ".current-task"


def find_repo_root(start_path: str) -> str | None:
    """Find git repo root from start_path upwards."""
    current = Path(start_path).resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return str(current)
        current = current.parent
    return None


def get_current_task(repo_root: str) -> str | None:
    """Read current task directory path from .trellis/.current-task."""
    current_task_file = os.path.join(repo_root, DIR_WORKFLOW, FILE_CURRENT_TASK)
    if not os.path.exists(current_task_file):
        return None
    try:
        with open(current_task_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return content if content else None
    except Exception:
        return None


def load_state(repo_root: str) -> dict:
    """Load todo enforcer state from file."""
    state_path = os.path.join(repo_root, STATE_FILE)
    if not os.path.exists(state_path):
        return {}
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(repo_root: str, state: dict) -> None:
    """
    Save state atomically (write temp file then rename).

    Atomic write prevents corruption from concurrent reads/writes.
    """
    state_path = os.path.join(repo_root, STATE_FILE)
    dir_path = os.path.dirname(state_path)
    try:
        os.makedirs(dir_path, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, state_path)
        except Exception:
            # Clean up temp file on failure
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    except Exception:
        pass


def handle_todo_write(input_data: dict, repo_root: str) -> None:
    """
    Handle PostToolUse for TodoWrite - track todo state.

    Reads the tool_input to extract the todo list snapshot and
    persists it to the state file.
    """
    tool_input = input_data.get("tool_input", {})
    tool_result = input_data.get("tool_result", {})

    # TodoWrite tool_input contains the todos array
    todos = tool_input.get("todos", [])
    if not todos and isinstance(tool_result, dict):
        todos = tool_result.get("todos", [])

    # Count incomplete todos
    pending = 0
    in_progress = 0
    completed = 0
    total = len(todos)

    for todo in todos:
        status = todo.get("status", "pending")
        if status == "completed":
            completed += 1
        elif status == "in_progress":
            in_progress += 1
        else:
            pending += 1

    incomplete = pending + in_progress

    state = load_state(repo_root)
    state["todos"] = {
        "total": total,
        "completed": completed,
        "in_progress": in_progress,
        "pending": pending,
        "incomplete": incomplete,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    save_state(repo_root, state)


def handle_stop(input_data: dict, repo_root: str) -> None:
    """
    Handle Stop event - block if incomplete todos remain.

    Checks the state file for todo status. If incomplete todos exist
    and an active task is set, blocks the stop with a continuation prompt.
    Implements exponential backoff to prevent infinite loops.
    """
    task_dir = get_current_task(repo_root)
    if not task_dir:
        # No active task, allow stop
        print("{}")
        return

    state = load_state(repo_root)
    todos_info = state.get("todos")

    # No todo tracking data yet, allow stop
    if not todos_info:
        print("{}")
        return

    incomplete = todos_info.get("incomplete", 0)
    if incomplete <= 0:
        # All todos done, allow stop and reset continuation count
        if "continuation_count" in state:
            state["continuation_count"] = 0
            save_state(repo_root, state)
        print("{}")
        return

    # There are incomplete todos - check backoff state
    session_id = input_data.get("sessionId", "")
    now = datetime.now(timezone.utc)

    # Reset continuation tracking if session changed
    if state.get("session_id") != session_id:
        state["session_id"] = session_id
        state["continuation_count"] = 0
        state["cooldown_until"] = None

    # Check cooldown
    cooldown_until = state.get("cooldown_until")
    if cooldown_until:
        try:
            cooldown_dt = datetime.fromisoformat(cooldown_until)
            if now < cooldown_dt:
                # Still in cooldown, allow stop
                print("{}")
                return
        except (ValueError, TypeError):
            pass
        # Cooldown expired, reset
        state["cooldown_until"] = None
        state["continuation_count"] = 0

    continuation_count = state.get("continuation_count", 0)

    if continuation_count >= MAX_CONTINUATIONS:
        # Hit max, enter cooldown
        cooldown_end = (now + timedelta(minutes=COOLDOWN_MINUTES)).isoformat()
        state["cooldown_until"] = cooldown_end
        state["continuation_count"] = 0
        save_state(repo_root, state)
        # Allow stop after max continuations
        print("{}")
        return

    # Block the stop
    state["continuation_count"] = continuation_count + 1
    state["last_continuation_at"] = now.isoformat()
    save_state(repo_root, state)

    in_progress = todos_info.get("in_progress", 0)
    pending = todos_info.get("pending", 0)
    total = todos_info.get("total", 0)
    completed = todos_info.get("completed", 0)

    reason_parts = [
        f"You have {incomplete} incomplete todo(s) "
        f"({pending} pending, {in_progress} in progress) "
        f"out of {total} total ({completed} completed).",
        "Please continue working until all todos are completed.",
        f"(Continuation {continuation_count + 1}/{MAX_CONTINUATIONS})",
    ]

    output = {
        "hookSpecificOutput": {
            "decision": "block",
            "reason": " ".join(reason_parts),
        }
    }
    print(json.dumps(output, ensure_ascii=False))


def main() -> None:
    """Route hook events to appropriate handlers (PostToolUse/TodoWrite or Stop)."""
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        print("{}")
        sys.exit(0)

    hook_event = input_data.get("hook_event_name", "")
    cwd = input_data.get("cwd", os.getcwd())

    repo_root = find_repo_root(cwd)
    if not repo_root:
        print("{}")
        sys.exit(0)

    try:
        if hook_event == "PostToolUse":
            tool_name = input_data.get("tool_name", "")
            if tool_name == "TodoWrite":
                handle_todo_write(input_data, repo_root)
            # For non-TodoWrite PostToolUse, do nothing
            print("{}")
        elif hook_event == "Stop":
            handle_stop(input_data, repo_root)
        else:
            print("{}")
    except Exception:
        # Fail-open: any error allows stop
        print("{}")

    sys.exit(0)


if __name__ == "__main__":
    main()
