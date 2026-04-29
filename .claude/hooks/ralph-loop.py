#!/usr/bin/env python3
"""
Ralph Loop - SubagentStop Hook for Check/Review Agent Loop Control

Based on the Ralph Wiggum technique for autonomous agent loops.
Uses completion promises to control when the check/review agent can stop.

Mechanism:
- Intercepts when check/review subagent tries to stop (SubagentStop event)
- If verify commands configured in worktree.yaml, runs them to verify
- Otherwise, reads check.jsonl to get dynamic completion markers ({reason}_FINISH)
- Blocks stopping until verification passes or all markers found
- Has max iterations as safety limit

Escalation (verify-fix loop):
- When MAX_ITERATIONS reached and checks still fail, records escalation state
- Sets needs_escalation=true with failed_checks list in per-agent state
- Dispatch agent reads .ralph-state.json and triggers debug agent to fix
- MAX_ESCALATIONS (2) per agent type before marking escalation_exhausted
- ESCALATION_COOLDOWN (60s) between escalation attempts

State file: .trellis/.ralph-state.json
- Per-agent state: {task, started_at, check: {...}, review: {...}}
- Each agent sub-object tracks: iteration, needs_escalation, failed_checks,
  escalation_count, escalation_exhausted, last_escalation_at
- Resets when task changes or state times out
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# =============================================================================
# Configuration
# =============================================================================

MAX_ITERATIONS = 5  # Safety limit to prevent infinite loops
STATE_TIMEOUT_MINUTES = 30  # Reset state if older than this
STATE_FILE = ".trellis/.ralph-state.json"
WORKTREE_YAML = ".trellis/worktree.yaml"
DIR_WORKFLOW = ".trellis"
FILE_CURRENT_TASK = ".current-task"
COMMAND_TIMEOUT = 120  # Per verify command timeout in seconds

# Escalation configuration (verify-fix loop)
MAX_ESCALATIONS = 2  # Max escalation attempts per agent type
ESCALATION_COOLDOWN_SECONDS = 60  # Cooldown between escalations

# Agents controlled by Ralph Loop
TARGET_AGENTS = {"check", "review"}

# Fixed markers for review agent (must match review.md)
REVIEW_MARKERS = [
    "SPECCOMPLIANCE_FINISH",
    "SCIENTIFIC_FINISH",
    "CROSSLAYER_FINISH",
    "PERFORMANCE_FINISH",
    "DATAINTEGRITY_FINISH",
    "CODECLARITY_FINISH",
]


def _append_audit_trail(
    repo_root: str, task_dir: str, agent_type: str, event: str, iteration: int = 0
) -> None:
    """Append audit trail entry for Ralph Loop decisions.

    Never raises — audit failure must never block hook execution.
    """
    from datetime import datetime, timezone

    audit_file = os.path.join(repo_root, task_dir, "audit.jsonl")
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "agent": agent_type,
        "event": event,
        "iteration": iteration,
    }
    try:
        with open(audit_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def find_repo_root(start_path: str) -> str | None:
    """Find git repo root from start_path upwards"""
    current = Path(start_path).resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return str(current)
        current = current.parent
    return None


def get_current_task(repo_root: str) -> str | None:
    """Read current task directory path"""
    current_task_file = os.path.join(repo_root, DIR_WORKFLOW, FILE_CURRENT_TASK)
    if not os.path.exists(current_task_file):
        return None

    try:
        with open(current_task_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return content if content else None
    except Exception:
        return None


def get_verify_commands(repo_root: str) -> list[str]:
    """
    Read verify commands from worktree.yaml.

    Returns list of commands to run, or empty list if not configured.
    Uses simple YAML parsing without external dependencies.
    """
    yaml_path = os.path.join(repo_root, WORKTREE_YAML)
    if not os.path.exists(yaml_path):
        return []

    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Simple YAML parsing for verify section
        # Look for "verify:" followed by list items
        lines = content.split("\n")
        in_verify_section = False
        commands = []

        for line in lines:
            stripped = line.strip()

            # Check for section start
            if stripped.startswith("verify:"):
                in_verify_section = True
                continue

            # Check for new section (not indented, ends with :)
            if (
                not line.startswith(" ")
                and not line.startswith("\t")
                and stripped.endswith(":")
                and stripped != ""
            ):
                in_verify_section = False
                continue

            # If in verify section, look for list items
            if in_verify_section:
                # Skip comments and empty lines
                if stripped.startswith("#") or stripped == "":
                    continue
                # Parse list item (- command)
                if stripped.startswith("- "):
                    cmd = stripped[2:].strip()
                    if cmd:
                        commands.append(cmd)

        return commands
    except Exception:
        return []


def run_verify_commands(repo_root: str, commands: list[str]) -> tuple[bool, str]:
    """
    Run verify commands and return (success, message).

    All commands must pass for success.
    """
    for cmd in commands:
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=repo_root,
                capture_output=True,
                timeout=COMMAND_TIMEOUT,  # 2 minute timeout per command
            )
            if result.returncode != 0:
                stderr = result.stderr.decode("utf-8", errors="replace")
                stdout = result.stdout.decode("utf-8", errors="replace")
                error_output = stderr or stdout
                # Truncate long output
                if len(error_output) > 500:
                    error_output = error_output[:500] + "..."
                return False, f"Command failed: {cmd}\n{error_output}"
        except subprocess.TimeoutExpired:
            return False, f"Command timed out: {cmd}"
        except Exception as e:
            return False, f"Command error: {cmd} - {str(e)}"

    return True, "All verify commands passed"


def get_completion_markers(repo_root: str, task_dir: str) -> list[str]:
    """
    Read check.jsonl and generate completion markers from reasons.

    Each entry's "reason" field becomes {REASON}_FINISH marker.
    Example: {"file": "...", "reason": "TypeCheck"} -> "TYPECHECK_FINISH"
    """
    check_jsonl_path = os.path.join(repo_root, task_dir, "check.jsonl")
    markers = []

    if not os.path.exists(check_jsonl_path):
        # Fallback: if no check.jsonl, use default marker
        return ["ALL_CHECKS_FINISH"]

    try:
        with open(check_jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                    reason = item.get("reason", "")
                    if reason:
                        # Convert to uppercase and add _FINISH suffix
                        marker = f"{reason.upper().replace(' ', '_')}_FINISH"
                        if marker not in markers:
                            markers.append(marker)
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass

    # If no markers found, use default
    if not markers:
        markers = ["ALL_CHECKS_FINISH"]

    return markers


def load_state(repo_root: str) -> dict:
    """Load Ralph Loop state from file."""
    state_path = os.path.join(repo_root, STATE_FILE)
    if not os.path.exists(state_path):
        return {"task": None, "started_at": None}

    try:
        with open(state_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"task": None, "started_at": None}


def save_state(repo_root: str, state: dict) -> None:
    """Save Ralph Loop state to file using atomic write (tmp + rename)."""
    state_path = os.path.join(repo_root, STATE_FILE)
    tmp_path = state_path + ".tmp"
    try:
        os.makedirs(os.path.dirname(state_path), exist_ok=True)
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, state_path)
    except Exception:
        # Clean up tmp file on failure
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def get_agent_state(state: dict, agent_type: str) -> dict:
    """Get per-agent state sub-object, creating defaults if missing.

    Supports backward compatibility with the old flat state format
    (which used top-level "iteration" key).
    """
    if agent_type not in state:
        state[agent_type] = {
            "iteration": 0,
            "needs_escalation": False,
            "failed_checks": [],
            "escalation_count": 0,
            "escalation_exhausted": False,
            "last_escalation_at": None,
        }
    agent_state = state[agent_type]
    # Ensure all keys exist (forward-compat for older state files)
    agent_state.setdefault("iteration", 0)
    agent_state.setdefault("needs_escalation", False)
    agent_state.setdefault("failed_checks", [])
    agent_state.setdefault("escalation_count", 0)
    agent_state.setdefault("escalation_exhausted", False)
    agent_state.setdefault("last_escalation_at", None)
    return agent_state


def record_escalation(agent_state: dict, failed_checks: list[str]) -> None:
    """Record escalation state when MAX_ITERATIONS reached with failures.

    Sets needs_escalation flag, records failed checks, increments
    escalation_count, and checks if escalation limit is exhausted.
    """
    agent_state["iteration"] = 0
    agent_state["needs_escalation"] = True
    agent_state["failed_checks"] = failed_checks
    agent_state["escalation_count"] = agent_state.get("escalation_count", 0) + 1
    agent_state["last_escalation_at"] = datetime.now().isoformat()

    if agent_state["escalation_count"] >= MAX_ESCALATIONS:
        agent_state["escalation_exhausted"] = True


def is_escalation_on_cooldown(agent_state: dict) -> bool:
    """Check if the agent is still within escalation cooldown period."""
    last_at = agent_state.get("last_escalation_at")
    if not last_at:
        return False
    try:
        last_time = datetime.fromisoformat(last_at)
        elapsed = (datetime.now() - last_time).total_seconds()
        return elapsed < ESCALATION_COOLDOWN_SECONDS
    except (ValueError, TypeError):
        return False


def check_completion(agent_output: str, markers: list[str]) -> tuple[bool, list[str]]:
    """
    Check if all completion markers are present in agent output.

    Returns:
        (all_complete, missing_markers)
    """
    missing = []
    for marker in markers:
        if marker not in agent_output:
            missing.append(marker)

    return len(missing) == 0, missing


def _emit(output: dict) -> None:
    """Print JSON output and exit."""
    print(json.dumps(output, ensure_ascii=False))
    sys.exit(0)


def _determine_failures(
    repo_root: str, task_dir: str, subagent_type: str, agent_output: str
) -> tuple[bool, list[str]]:
    """Determine what checks failed for the given agent type.

    Returns:
        (all_passed, failed_descriptions)
    """
    if subagent_type == "review":
        all_ok, missing = check_completion(agent_output, REVIEW_MARKERS)
        if all_ok:
            return True, []
        return False, [f"Missing marker: {m}" for m in missing]

    # Check agent: try verify commands first, then markers
    verify_commands = get_verify_commands(repo_root)
    if verify_commands:
        passed, message = run_verify_commands(repo_root, verify_commands)
        if passed:
            return True, []
        return False, [message]

    markers = get_completion_markers(repo_root, task_dir)
    all_ok, missing = check_completion(agent_output, markers)
    if all_ok:
        return True, []
    return False, [f"Missing marker: {m}" for m in missing]


def main() -> None:
    """Handle SubagentStop events for check/review agents with loop control and escalation."""
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    hook_event = input_data.get("hook_event_name", "")
    if hook_event != "SubagentStop":
        sys.exit(0)

    subagent_type = input_data.get("subagent_type", "")
    agent_output = input_data.get("agent_output", "")
    original_prompt = input_data.get("prompt", "")
    cwd = input_data.get("cwd", os.getcwd())

    if subagent_type not in TARGET_AGENTS:
        sys.exit(0)

    # Skip Ralph Loop for finish phase
    if "[finish]" in original_prompt.lower():
        sys.exit(0)

    repo_root = find_repo_root(cwd)
    if not repo_root:
        sys.exit(0)

    task_dir = get_current_task(repo_root)
    if not task_dir:
        sys.exit(0)

    # ── Load & reset state ──────────────────────────────────────────
    state = load_state(repo_root)

    should_reset = False
    if state.get("task") != task_dir:
        should_reset = True
    elif state.get("started_at"):
        try:
            started = datetime.fromisoformat(state["started_at"])
            elapsed = (datetime.now() - started).total_seconds()
            if elapsed > STATE_TIMEOUT_MINUTES * 60:
                should_reset = True
        except (ValueError, TypeError):
            should_reset = True

    if should_reset:
        state = {
            "task": task_dir,
            "started_at": datetime.now().isoformat(),
        }

    # ── Per-agent iteration tracking ────────────────────────────────
    agent_st = get_agent_state(state, subagent_type)
    agent_st["iteration"] = agent_st.get("iteration", 0) + 1
    current_iteration = agent_st["iteration"]

    # Clear escalation flag when agent re-enters loop (dispatch retried)
    if current_iteration == 1 and agent_st.get("needs_escalation"):
        agent_st["needs_escalation"] = False
        agent_st["failed_checks"] = []

    save_state(repo_root, state)

    # ── MAX_ITERATIONS reached: escalation branch ───────────────────
    if current_iteration >= MAX_ITERATIONS:
        all_passed, failures = _determine_failures(
            repo_root, task_dir, subagent_type, agent_output
        )

        if all_passed:
            # Checks actually passed on the last attempt
            agent_st["iteration"] = 0
            agent_st["needs_escalation"] = False
            agent_st["failed_checks"] = []
            save_state(repo_root, state)
            _append_audit_trail(repo_root, task_dir, subagent_type, "ralph_pass", current_iteration)
            _emit(
                {
                    "decision": "allow",
                    "reason": f"All checks passed on iteration {current_iteration}. Phase complete.",
                }
            )

        # Checks still failing -- escalation logic
        elif agent_st.get("escalation_exhausted"):
            # Already exhausted all escalation attempts
            agent_st["iteration"] = 0
            save_state(repo_root, state)
            _append_audit_trail(repo_root, task_dir, subagent_type, "ralph_escalate", current_iteration)
            _emit(
                {
                    "decision": "allow",
                    "reason": (
                        f"Max escalations ({MAX_ESCALATIONS}) exhausted for {subagent_type}. "
                        f"Failures: {'; '.join(failures)}. "
                        "Human intervention required."
                    ),
                }
            )

        elif is_escalation_on_cooldown(agent_st):
            # Still in cooldown from previous escalation
            agent_st["iteration"] = 0
            save_state(repo_root, state)
            _append_audit_trail(repo_root, task_dir, subagent_type, "ralph_escalate", current_iteration)
            _emit(
                {
                    "decision": "allow",
                    "reason": (
                        f"Escalation cooldown active for {subagent_type} "
                        f"({ESCALATION_COOLDOWN_SECONDS}s). Allowing stop. "
                        f"Failures: {'; '.join(failures)}"
                    ),
                }
            )

        else:
            # Record escalation and allow stop so dispatch can trigger debug
            record_escalation(agent_st, failures)
            save_state(repo_root, state)
            _append_audit_trail(repo_root, task_dir, subagent_type, "ralph_escalate", current_iteration)
            _emit(
                {
                    "decision": "allow",
                    "reason": (
                        f"Max iterations ({MAX_ITERATIONS}) reached for {subagent_type}. "
                        f"Escalation #{agent_st['escalation_count']}/{MAX_ESCALATIONS} recorded. "
                        f"Failures: {'; '.join(failures)}. "
                        "Dispatch should read .ralph-state.json and trigger debug agent."
                    ),
                }
            )

    # ── Normal loop: check and block/allow ──────────────────────────

    # Review agent: fixed markers
    if subagent_type == "review":
        all_complete, missing = check_completion(agent_output, REVIEW_MARKERS)

        if all_complete:
            agent_st["iteration"] = 0
            agent_st["needs_escalation"] = False
            agent_st["failed_checks"] = []
            save_state(repo_root, state)
            _append_audit_trail(repo_root, task_dir, subagent_type, "ralph_pass", current_iteration)
            _emit(
                {
                    "decision": "allow",
                    "reason": "All review markers found. Review phase complete.",
                }
            )
        else:
            _append_audit_trail(repo_root, task_dir, subagent_type, "ralph_retry", current_iteration)
            _emit(
                {
                    "decision": "block",
                    "reason": (
                        f"Iteration {current_iteration}/{MAX_ITERATIONS}. "
                        f"Missing review markers: {', '.join(missing)}.\n\n"
                        "You must check ALL 6 dimensions and output the "
                        "corresponding marker for each:\n"
                        "- SPECCOMPLIANCE_FINISH (D0: Spec Compliance)\n"
                        "- SCIENTIFIC_FINISH (D1: Scientific Correctness)\n"
                        "- CROSSLAYER_FINISH (D2: Cross-Layer Consistency)\n"
                        "- PERFORMANCE_FINISH (D4: Performance)\n"
                        "- DATAINTEGRITY_FINISH (D5: Data Integrity)\n"
                        "- CODECLARITY_FINISH (D6: Code Clarity)\n\n"
                        "If a dimension is N/A, still output the marker with a note."
                    ),
                }
            )

    # Check agent: verify commands from worktree.yaml, fallback to markers
    verify_commands = get_verify_commands(repo_root)

    if verify_commands:
        passed, message = run_verify_commands(repo_root, verify_commands)

        if passed:
            agent_st["iteration"] = 0
            agent_st["needs_escalation"] = False
            agent_st["failed_checks"] = []
            save_state(repo_root, state)
            _append_audit_trail(repo_root, task_dir, subagent_type, "ralph_pass", current_iteration)
            _emit(
                {
                    "decision": "allow",
                    "reason": "All verify commands passed. Check phase complete.",
                }
            )
        else:
            _append_audit_trail(repo_root, task_dir, subagent_type, "ralph_retry", current_iteration)
            _emit(
                {
                    "decision": "block",
                    "reason": (
                        f"Iteration {current_iteration}/{MAX_ITERATIONS}. "
                        f"Verification failed:\n{message}\n\n"
                        "Please fix the issues and try again."
                    ),
                }
            )
    else:
        markers = get_completion_markers(repo_root, task_dir)
        all_complete, missing = check_completion(agent_output, markers)

        if all_complete:
            agent_st["iteration"] = 0
            agent_st["needs_escalation"] = False
            agent_st["failed_checks"] = []
            save_state(repo_root, state)
            _append_audit_trail(repo_root, task_dir, subagent_type, "ralph_pass", current_iteration)
            _emit(
                {
                    "decision": "allow",
                    "reason": "All completion markers found. Check phase complete.",
                }
            )
        else:
            _append_audit_trail(repo_root, task_dir, subagent_type, "ralph_retry", current_iteration)
            _emit(
                {
                    "decision": "block",
                    "reason": (
                        f"Iteration {current_iteration}/{MAX_ITERATIONS}. "
                        f"Missing completion markers: {', '.join(missing)}.\n\n"
                        "IMPORTANT: You must ACTUALLY run the checks, not just "
                        "output the markers.\n"
                        "- Did you run lint? What was the output?\n"
                        "- Did you run typecheck? What was the output?\n"
                        "- Did they actually pass with zero errors?\n\n"
                        "Only output a marker (e.g., LINT_FINISH) AFTER:\n"
                        "1. You have executed the corresponding command\n"
                        "2. The command completed with zero errors\n"
                        "3. You have shown the command output in your response\n\n"
                        "Do NOT output markers just to escape the loop. "
                        "The loop exists to ensure quality."
                    ),
                }
            )


if __name__ == "__main__":
    main()
