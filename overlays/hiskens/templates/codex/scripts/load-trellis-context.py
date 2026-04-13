#!/usr/bin/env python3
"""
Trellis Context Loader for Codex CLI

Loads Trellis context (specs, PRD, memory) for Codex subagents.
Called via Bash by Codex subagent to get task context.

Usage:
    python3 .codex/scripts/load-trellis-context.py <agent-type> [--task-dir <path>] [--verify]

Exit codes:
    0 - Success
    1 - No active task
    2 - Parameter error
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap: add .trellis/scripts to sys.path so we can import context_assembly
# We find repo root first (simple upward .git search), then set up the import.
# ---------------------------------------------------------------------------


def _find_repo_root() -> str | None:
    """Find git repo root from cwd upwards, resolving symlinks."""
    current = Path(os.path.realpath(os.getcwd())).resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return str(current)
        current = current.parent
    return None


_repo_root = _find_repo_root()
if _repo_root is None:
    print("Error: Could not find git repository root", file=sys.stderr)
    sys.exit(2)

sys.path.insert(0, os.path.join(_repo_root, ".trellis", "scripts"))

from common.context_assembly import (  # noqa: E402
    get_check_context,
    get_current_task,
    get_debug_context,
    get_finish_context,
    get_implement_context,
    get_nocturne_hints,
    get_plan_context,
    get_research_context,
    get_review_context,
    read_file_content,
    read_jsonl_entries,
)

# ---------------------------------------------------------------------------
# Agent context dispatcher
# ---------------------------------------------------------------------------

AGENT_CONTEXT_GETTERS = {
    "implement": get_implement_context,
    "check": get_check_context,
    "debug": get_debug_context,
    "review": get_review_context,
    "research": get_research_context,
    "plan": get_plan_context,
    "finish": get_finish_context,
}

AGENT_INSTRUCTIONS = {
    "implement": (
        "1. Read requirements above carefully\n"
        "2. Implement the feature following specs\n"
        "3. Run `uv run ruff check .` before finishing\n"
        "4. Run `uv run ruff format --check .` before finishing\n"
        "5. Summarize files changed and verification results"
    ),
    "check": (
        "1. Read specs above carefully\n"
        "2. Run `git diff --name-only` and `git diff` to see changes\n"
        "3. Check code quality against specs\n"
        "4. Fix issues directly (don't just report)\n"
        "5. Run verification commands to confirm fixes"
    ),
    "debug": (
        "1. Read error context above carefully\n"
        "2. Identify root cause following debug methodology\n"
        "3. Fix the bug precisely (no refactoring)\n"
        "4. Verify fix with lint/typecheck\n"
        "5. Report completion status"
    ),
    "review": (
        "1. Read specs and requirements above\n"
        "2. Run `git diff --name-only` and `git diff`\n"
        "3. Review across D0-D6 dimensions\n"
        "4. Output completion markers for each dimension\n"
        "5. Report findings with file:line references"
    ),
    "research": (
        "1. Read project info above\n"
        "2. Analyze codebase using appropriate tools\n"
        "3. Find relevant specs and patterns\n"
        "4. Report findings in structured format\n"
        "5. Do not modify any files"
    ),
    "plan": (
        "1. Read project info above\n"
        "2. Analyze requirement for clarity and feasibility\n"
        "3. Reject unclear requirements with clear reasons\n"
        "4. Create task plan with acceptance criteria\n"
        "5. Configure context files via task.py"
    ),
    "finish": (
        "1. Read checklist above carefully\n"
        "2. Verify all requirements in prd.md are met\n"
        "3. Run final verification commands\n"
        "4. Check for spec sync needs\n"
        "5. Report completion status"
    ),
}


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------


def _split_context(context: str) -> dict[str, list[str]]:
    """Split raw getter context string into categorized block lists.

    The getter functions in context_assembly.py return a single string of
    ``=== path ===`` blocks.  This helper classifies each block into one
    of four categories so that format_context() can render them under the
    correct Markdown section headings.

    Returns a dict with keys: requirements, design, specs, memory.
    Each value is a list of raw block strings (including their header line).
    """
    result: dict[str, list[str]] = {
        "requirements": [],
        "design": [],
        "specs": [],
        "memory": [],
    }
    if not context:
        return result

    # Split on the block separator pattern: a blank line followed by "=== "
    blocks = context.split("\n\n=== ")
    for i, block in enumerate(blocks):
        # Restore the leading "=== " that was consumed by split (except the
        # very first block which may or may not start with "=== ").
        if i > 0:
            block = "=== " + block
        block = block.strip()
        if not block:
            continue

        # Classify by the header content in the first line.
        first_line = block.split("\n", 1)[0]
        if "prd.md (Requirements)" in first_line:
            result["requirements"].append(block)
        elif "info.md (Technical Design)" in first_line:
            result["design"].append(block)
        elif "(Memory)" in first_line:
            result["memory"].append(block)
        else:
            result["specs"].append(block)

    return result


def format_context(
    agent_type: str,
    task_dir: str,
    task_info: dict,
    context: str,
    prd: str | None,
    info: str | None,
    nocturne: str,
) -> str:
    """Format complete context as Markdown."""
    parts = [f"# Trellis Context for {agent_type}", ""]

    # Task section
    parts.append("## Task")
    if task_info:
        parts.append(f"- Title: {task_info.get('title', 'Unknown')}")
        parts.append(f"- Status: {task_info.get('status', 'Unknown')}")
    parts.append(f"- Directory: {task_dir}")
    parts.append("")

    # Split context into categories so we can render them under the correct
    # section headings even when the getter already embedded prd/info.
    sections = (
        _split_context(context)
        if context
        else {
            "requirements": [],
            "design": [],
            "specs": [],
            "memory": [],
        }
    )

    # Requirements: prefer explicit prd param (debug/research/plan), fallback
    # to extracting from the getter context (implement/check/review/finish).
    if prd:
        parts.append("## Requirements (prd.md)")
        parts.append(prd)
        parts.append("")
    elif sections["requirements"]:
        parts.append("## Requirements (prd.md)")
        parts.extend(sections["requirements"])
        parts.append("")

    # Technical Design: same logic as Requirements.
    if info:
        parts.append("## Technical Design (info.md)")
        parts.append(info)
        parts.append("")
    elif sections["design"]:
        parts.append("## Technical Design (info.md)")
        parts.extend(sections["design"])
        parts.append("")

    # Specs (everything that is not requirements/design/memory).
    if sections["specs"]:
        parts.append("## Specs")
        parts.extend(sections["specs"])
        parts.append("")

    # Memory
    if sections["memory"]:
        parts.append("## Memory")
        parts.extend(sections["memory"])
        parts.append("")

    # Nocturne hints
    if nocturne:
        parts.append("## Nocturne Hints")
        parts.append(nocturne)
        parts.append("")

    # Instructions
    parts.append("## Instructions")
    parts.append(AGENT_INSTRUCTIONS.get(agent_type, AGENT_INSTRUCTIONS["implement"]))

    return "\n".join(parts)


def format_verify(
    agent_type: str,
    task_dir: str,
    task_info: dict,
    context: str,
    prd: str | None,
    info: str | None,
    jsonl_path: str,
    repo_root: str,
) -> str:
    """Format verification output."""
    lines = []

    # Task
    if task_info:
        title = task_info.get("title", "Unknown")
        status = task_info.get("status", "Unknown")
        lines.append(f"[OK] Task: {title} ({status})")
    else:
        lines.append(f"[OK] Task directory: {task_dir}")

    # PRD
    if prd:
        lines.append(f"[OK] prd.md: {len(prd.encode('utf-8'))} bytes")
    else:
        lines.append("[WARN] prd.md: not found")

    # Info
    if info:
        lines.append(f"[OK] info.md: {len(info.encode('utf-8'))} bytes")
    else:
        lines.append("[WARN] info.md: not found")

    # Specs from jsonl
    entries = read_jsonl_entries(repo_root, jsonl_path)
    if entries:
        lines.append(f"[OK] {agent_type}.jsonl: {len(entries)} entries")
        for file_path, content in entries:
            kb = len(content.encode("utf-8")) / 1024
            lines.append(f"  - {file_path} ({kb:.1f}KB)")
    else:
        lines.append(f"[WARN] {agent_type}.jsonl: no entries or file not found")

    # Memory summary
    from common.context_assembly import get_memory_context

    mem = get_memory_context(repo_root, agent_type)
    if mem:
        lines.append(f"[OK] Memory: ({len(mem.encode('utf-8')) / 1024:.1f}KB)")
    else:
        lines.append("[INFO] Memory: no files loaded")

    # Token estimate
    total_chars = len(context) + (len(prd) if prd else 0) + (len(info) if info else 0)
    lines.append(f"Total context: ~{total_chars // 4} tokens")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Load Trellis context for Codex subagents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "agent_type",
        choices=list(AGENT_CONTEXT_GETTERS.keys()),
        help="Type of agent to load context for",
    )
    parser.add_argument(
        "--task-dir",
        dest="task_dir",
        help="Override .current-task pointer (optional)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Output summary only (file list + sizes)",
    )

    args = parser.parse_args()
    repo_root = _repo_root  # already resolved at module level

    # Determine task directory
    task_dir = args.task_dir or get_current_task(repo_root)
    if not task_dir:
        print(
            "Error: No active task. "
            "Run 'python3 .trellis/scripts/task.py start <task-dir>' first.",
            file=sys.stderr,
        )
        print(
            "Or use --task-dir to specify task directory explicitly.", file=sys.stderr
        )
        sys.exit(1)

    # Verify task directory exists
    if not os.path.exists(os.path.join(repo_root, task_dir)):
        print(f"Error: Task directory not found: {task_dir}", file=sys.stderr)
        sys.exit(1)

    # Load task info
    task_json_path = os.path.join(repo_root, task_dir, "task.json")
    task_info: dict = {}
    if os.path.exists(task_json_path):
        try:
            with open(task_json_path, "r", encoding="utf-8") as f:
                task_info = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    # Get agent context via shared context_assembly module
    getter = AGENT_CONTEXT_GETTERS[args.agent_type]
    context = getter(repo_root, task_dir)

    # Load PRD and info only for agents whose getters don't already embed them.
    # Getters that embed prd: implement, check, review, finish
    # Getters that embed info: implement
    agents_with_prd = {"implement", "check", "review", "finish"}
    agents_with_info = {"implement"}
    prd = (
        None
        if args.agent_type in agents_with_prd
        else read_file_content(repo_root, f"{task_dir}/prd.md")
    )
    info = (
        None
        if args.agent_type in agents_with_info
        else read_file_content(repo_root, f"{task_dir}/info.md")
    )

    # Get nocturne hints
    nocturne = get_nocturne_hints(args.agent_type)

    # Output
    if args.verify:
        # Verify mode always shows prd/info status regardless of agent type
        verify_prd = read_file_content(repo_root, f"{task_dir}/prd.md")
        verify_info = read_file_content(repo_root, f"{task_dir}/info.md")
        jsonl_path = f"{task_dir}/{args.agent_type}.jsonl"
        output = format_verify(
            args.agent_type,
            task_dir,
            task_info,
            context,
            verify_prd,
            verify_info,
            jsonl_path,
            repo_root,
        )
    else:
        output = format_context(
            args.agent_type, task_dir, task_info, context, prd, info, nocturne
        )

    print(output)
    sys.exit(0)


if __name__ == "__main__":
    main()
