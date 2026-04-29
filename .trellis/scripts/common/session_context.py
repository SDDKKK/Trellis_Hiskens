#!/usr/bin/env python3
"""
Session context generation (default + record modes).

Provides:
    get_context_json          - JSON output for default mode
    get_context_text          - Text output for default mode
    get_context_record_json   - JSON for record mode
    get_context_text_record   - Text for record mode
    output_json               - Print JSON
    output_text               - Print text
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from .config import get_git_packages
from .git import run_git
from .packages_context import get_packages_section
from .tasks import iter_active_tasks, load_task, get_all_statuses, children_progress
from .paths import (
    DIR_MEMORY,
    DIR_SCRIPTS,
    DIR_SPEC,
    DIR_TASKS,
    DIR_WORKFLOW,
    DIR_WORKSPACE,
    FILE_DECISIONS,
    FILE_KNOWN_ISSUES,
    FILE_LEARNINGS,
    FILE_SCRATCHPAD,
    count_lines,
    get_active_journal_file,
    get_current_task,
    get_developer,
    get_memory_dir,
    get_repo_root,
    get_tasks_dir,
)


# =============================================================================
# Helpers (Local adaptations)
# =============================================================================


def _count_entries(file_path: Path, pattern: str) -> int:
    """Count lines matching a pattern in a file.

    Args:
        file_path: Path to the file.
        pattern: String prefix to match at the start of each line.

    Returns:
        Number of matching lines, or 0 if file doesn't exist.
    """
    if not file_path.is_file():
        return 0
    try:
        text = file_path.read_text(encoding="utf-8")
        return sum(1 for line in text.splitlines() if line.startswith(pattern))
    except (OSError, IOError):
        return 0


def _is_scratchpad_active(file_path: Path) -> bool:
    """Check if scratchpad has active content (not just placeholder).

    Args:
        file_path: Path to scratchpad.md.

    Returns:
        True if scratchpad exists and does not contain "(No active task)".
    """
    if not file_path.is_file():
        return False
    try:
        text = file_path.read_text(encoding="utf-8")
        return "(No active task)" not in text
    except (OSError, IOError):
        return False


def _get_session_freshness_data(repo_root: Path, journal_file: Path | None) -> dict:
    """Get session freshness data for JSON output.

    Args:
        repo_root: Repository root path.
        journal_file: Active journal file path, or None.

    Returns:
        Dictionary with session freshness info.
    """
    current_task = get_current_task(repo_root)
    if not current_task:
        return {"hasActiveTask": False, "message": "No active task (session is fresh)"}

    result: dict = {"hasActiveTask": True}

    if journal_file and journal_file.is_file():
        try:
            last_modified = journal_file.stat().st_mtime
            age_hours = int((time.time() - last_modified) / 3600)
            result["lastJournalUpdateHours"] = age_hours
            result["isStale"] = age_hours > 24
        except OSError:
            pass

    _, status_out, _ = run_git(["status", "--porcelain"], cwd=repo_root)
    result["uncommittedChanges"] = len(
        [line for line in status_out.splitlines() if line.strip()]
    )

    return result


def _get_memory_data(repo_root: Path) -> dict:
    """Get memory section data for JSON output.

    Args:
        repo_root: Repository root path.

    Returns:
        Dictionary with memory counts and scratchpad status.
    """
    memory_dir = get_memory_dir(repo_root)
    if not memory_dir.is_dir():
        return {"initialized": False}

    return {
        "initialized": True,
        "decisions": _count_entries(memory_dir / FILE_DECISIONS, "## 20"),
        "knownIssues": _count_entries(memory_dir / FILE_KNOWN_ISSUES, "## Issue:"),
        "learnings": _count_entries(memory_dir / FILE_LEARNINGS, "## 20"),
        "scratchpadActive": _is_scratchpad_active(memory_dir / FILE_SCRATCHPAD),
    }


def _append_package_git_context(lines: list[str], package_git_info: list[dict]) -> None:
    """Append Git status and recent commits for package repositories."""
    for pkg in package_git_info:
        lines.append(f"## GIT STATUS ({pkg['name']}: {pkg['path']})")
        lines.append(f"Branch: {pkg['branch']}")
        if pkg["isClean"]:
            lines.append("Working directory: Clean")
        else:
            lines.append(
                f"Working directory: {pkg['uncommittedChanges']} uncommitted change(s)"
            )
        lines.append("")
        lines.append(f"## RECENT COMMITS ({pkg['name']}: {pkg['path']})")
        if pkg["recentCommits"]:
            for commit in pkg["recentCommits"]:
                lines.append(f"{commit['hash']} {commit['message']}")
        else:
            lines.append("(no commits)")
        lines.append("")


def _collect_package_git_info(repo_root: Path) -> list[dict]:
    """Collect git status and recent commits for packages with independent git repos.

    Only packages marked with ``git: true`` in config.yaml are included.

    Returns:
        List of dicts with keys: name, path, branch, isClean,
        uncommittedChanges, recentCommits.
        Empty list if no git-repo packages are configured.
    """
    git_pkgs = get_git_packages(repo_root)
    if not git_pkgs:
        return []

    result = []
    for pkg_name, pkg_path in git_pkgs.items():
        pkg_dir = repo_root / pkg_path
        if not (pkg_dir / ".git").exists():
            continue

        _, branch_out, _ = run_git(["branch", "--show-current"], cwd=pkg_dir)
        branch = branch_out.strip() or "unknown"

        _, status_out, _ = run_git(["status", "--porcelain"], cwd=pkg_dir)
        changes = len([line for line in status_out.splitlines() if line.strip()])

        _, log_out, _ = run_git(["log", "--oneline", "-5"], cwd=pkg_dir)
        commits = []
        for line in log_out.splitlines():
            if line.strip():
                parts = line.split(" ", 1)
                if len(parts) >= 2:
                    commits.append({"hash": parts[0], "message": parts[1]})
                elif len(parts) == 1:
                    commits.append({"hash": parts[0], "message": ""})

        result.append(
            {
                "name": pkg_name,
                "path": pkg_path,
                "branch": branch,
                "isClean": changes == 0,
                "uncommittedChanges": changes,
                "recentCommits": commits,
            }
        )

    return result


# =============================================================================
# JSON Output
# =============================================================================


def get_context_json(repo_root: Path | None = None) -> dict:
    """Get context as a dictionary.

    Args:
        repo_root: Repository root path. Defaults to auto-detected.

    Returns:
        Context dictionary.
    """
    if repo_root is None:
        repo_root = get_repo_root()

    developer = get_developer(repo_root)
    tasks_dir = get_tasks_dir(repo_root)
    journal_file = get_active_journal_file(repo_root)

    journal_lines = 0
    journal_relative = ""
    if journal_file and developer:
        journal_lines = count_lines(journal_file)
        journal_relative = (
            f"{DIR_WORKFLOW}/{DIR_WORKSPACE}/{developer}/{journal_file.name}"
        )

    # Git info
    _, branch_out, _ = run_git(["branch", "--show-current"], cwd=repo_root)
    branch = branch_out.strip() or "unknown"

    _, status_out, _ = run_git(["status", "--porcelain"], cwd=repo_root)
    git_status_count = len([line for line in status_out.splitlines() if line.strip()])
    is_clean = git_status_count == 0

    # Recent commits
    _, log_out, _ = run_git(["log", "--oneline", "-5"], cwd=repo_root)
    commits = []
    for line in log_out.splitlines():
        if line.strip():
            parts = line.split(" ", 1)
            if len(parts) >= 2:
                commits.append({"hash": parts[0], "message": parts[1]})
            elif len(parts) == 1:
                commits.append({"hash": parts[0], "message": ""})

    # Tasks
    tasks = [
        {
            "dir": t.dir_name,
            "name": t.name,
            "status": t.status,
            "children": list(t.children),
            "parent": t.parent,
        }
        for t in iter_active_tasks(tasks_dir)
    ]

    # Package git repos (independent sub-repositories)
    pkg_git_info = _collect_package_git_info(repo_root)

    result = {
        "developer": developer or "",
        "git": {
            "branch": branch,
            "isClean": is_clean,
            "uncommittedChanges": git_status_count,
            "recentCommits": commits,
        },
        "tasks": {
            "active": tasks,
            "directory": f"{DIR_WORKFLOW}/{DIR_TASKS}",
        },
        "journal": {
            "file": journal_relative,
            "lines": journal_lines,
            "nearLimit": journal_lines > 1800,
        },
        "sessionFreshness": _get_session_freshness_data(repo_root, journal_file),
        "memory": _get_memory_data(repo_root),
    }

    if pkg_git_info:
        result["packageGit"] = pkg_git_info

    return result


def output_json(repo_root: Path | None = None) -> None:
    """Output context in JSON format.

    Args:
        repo_root: Repository root path. Defaults to auto-detected.
    """
    context = get_context_json(repo_root)
    print(json.dumps(context, indent=2, ensure_ascii=False))


# =============================================================================
# Text Output
# =============================================================================


def get_context_text(repo_root: Path | None = None) -> str:
    """Get context as formatted text.

    Args:
        repo_root: Repository root path. Defaults to auto-detected.

    Returns:
        Formatted text output.
    """
    if repo_root is None:
        repo_root = get_repo_root()

    lines = []
    lines.append("========================================")
    lines.append("SESSION CONTEXT")
    lines.append("========================================")
    lines.append("")

    developer = get_developer(repo_root)

    # Developer section
    lines.append("## DEVELOPER")
    if not developer:
        lines.append(
            f"ERROR: Not initialized. Run: python3 ./{DIR_WORKFLOW}/{DIR_SCRIPTS}/init_developer.py <name>"
        )
        return "\n".join(lines)

    lines.append(f"Name: {developer}")
    lines.append("")

    # Git status
    lines.append("## GIT STATUS")
    _, branch_out, _ = run_git(["branch", "--show-current"], cwd=repo_root)
    branch = branch_out.strip() or "unknown"
    lines.append(f"Branch: {branch}")

    _, status_out, _ = run_git(["status", "--porcelain"], cwd=repo_root)
    status_lines = [line for line in status_out.splitlines() if line.strip()]
    status_count = len(status_lines)

    if status_count == 0:
        lines.append("Working directory: Clean")
    else:
        lines.append(f"Working directory: {status_count} uncommitted change(s)")
        lines.append("")
        lines.append("Changes:")
        _, short_out, _ = run_git(["status", "--short"], cwd=repo_root)
        for line in short_out.splitlines()[:10]:
            lines.append(line)
    lines.append("")

    # Recent commits
    lines.append("## RECENT COMMITS")
    _, log_out, _ = run_git(["log", "--oneline", "-5"], cwd=repo_root)
    if log_out.strip():
        for line in log_out.splitlines():
            lines.append(line)
    else:
        lines.append("(no commits)")
    lines.append("")

    # Package git repos — independent sub-repositories
    _append_package_git_context(lines, _collect_package_git_info(repo_root))

    # Current task
    lines.append("## CURRENT TASK")
    current_task = get_current_task(repo_root)
    if current_task:
        current_task_dir = repo_root / current_task
        lines.append(f"Path: {current_task}")

        ct = load_task(current_task_dir)
        if ct:
            lines.append(f"Name: {ct.name}")
            lines.append(f"Status: {ct.status}")
            lines.append(f"Created: {ct.raw.get('createdAt', 'unknown')}")
            if ct.description:
                lines.append(f"Description: {ct.description}")

        # Check for prd.md
        prd_file = current_task_dir / "prd.md"
        if prd_file.is_file():
            lines.append("")
            lines.append("[!] This task has prd.md - read it for task details")
    else:
        lines.append("(none)")
    lines.append("")

    # Active tasks
    lines.append("## ACTIVE TASKS")
    tasks_dir = get_tasks_dir(repo_root)
    task_count = 0

    # Collect all task data for hierarchy display
    all_tasks = {t.dir_name: t for t in iter_active_tasks(tasks_dir)}
    all_statuses = {name: t.status for name, t in all_tasks.items()}

    def _print_task_tree(name: str, indent: int = 0) -> None:
        nonlocal task_count
        t = all_tasks[name]
        progress = children_progress(t.children, all_statuses)
        prefix = "  " * indent
        lines.append(f"{prefix}- {name}/ ({t.status}){progress} @{t.assignee or '-'}")
        task_count += 1
        for child in t.children:
            if child in all_tasks:
                _print_task_tree(child, indent + 1)

    for dir_name in sorted(all_tasks.keys()):
        if not all_tasks[dir_name].parent:
            _print_task_tree(dir_name)

    if task_count == 0:
        lines.append("(no active tasks)")
    lines.append(f"Total: {task_count} active task(s)")
    lines.append("")

    # My tasks
    lines.append("## MY TASKS (Assigned to me)")
    my_task_count = 0

    for t in all_tasks.values():
        if t.assignee == developer and t.status != "done":
            progress = children_progress(t.children, all_statuses)
            lines.append(f"- [{t.priority}] {t.title} ({t.status}){progress}")
            my_task_count += 1

    if my_task_count == 0:
        lines.append("(no tasks assigned to you)")
    lines.append("")

    # Journal file
    lines.append("## JOURNAL FILE")
    journal_file = get_active_journal_file(repo_root)
    if journal_file:
        journal_lines = count_lines(journal_file)
        relative = f"{DIR_WORKFLOW}/{DIR_WORKSPACE}/{developer}/{journal_file.name}"
        lines.append(f"Active file: {relative}")
        lines.append(f"Line count: {journal_lines} / 2000")
        if journal_lines > 1800:
            lines.append("[!] WARNING: Approaching 2000 line limit!")
    else:
        lines.append("No journal file found")
    lines.append("")

    # Session freshness
    lines.append("## SESSION FRESHNESS")
    current_task = get_current_task(repo_root)
    if current_task:
        if journal_file and journal_file.is_file():
            try:
                last_modified = journal_file.stat().st_mtime
                age_hours = int((time.time() - last_modified) / 3600)
                lines.append(f"Last journal update: {age_hours}h ago")
                if age_hours > 24:
                    lines.append(
                        "[!] WARNING: Journal not updated in >24h. Session may be stale."
                    )
            except OSError:
                pass
        _, status_out, _ = run_git(["status", "--porcelain"], cwd=repo_root)
        uncommitted = len([s for s in status_out.splitlines() if s.strip()])
        lines.append(f"Uncommitted changes: {uncommitted}")
    else:
        lines.append("No active task (session is fresh)")
    lines.append("")

    # Memory
    lines.append("## MEMORY")
    memory_dir = get_memory_dir(repo_root)
    if memory_dir.is_dir():
        decisions_count = _count_entries(memory_dir / FILE_DECISIONS, "## 20")
        issues_count = _count_entries(memory_dir / FILE_KNOWN_ISSUES, "## Issue:")
        learnings_count = _count_entries(memory_dir / FILE_LEARNINGS, "## 20")
        scratchpad_active = _is_scratchpad_active(memory_dir / FILE_SCRATCHPAD)

        lines.append(f"Decisions: {decisions_count}")
        lines.append(f"Known Issues: {issues_count}")
        lines.append(f"Learnings: {learnings_count}")
        lines.append(f"Scratchpad: {'Active' if scratchpad_active else 'Empty'}")
    else:
        lines.append("(memory directory not initialized)")
    lines.append("")

    # Packages
    packages_text = get_packages_section(repo_root)
    if packages_text:
        lines.append(packages_text)
        lines.append("")

    # Paths
    lines.append("## PATHS")
    lines.append(f"Workspace: {DIR_WORKFLOW}/{DIR_WORKSPACE}/{developer}/")
    lines.append(f"Tasks: {DIR_WORKFLOW}/{DIR_TASKS}/")
    lines.append(f"Spec: {DIR_WORKFLOW}/{DIR_SPEC}/")
    lines.append(f"Memory: {DIR_WORKFLOW}/{DIR_MEMORY}/")
    lines.append("")

    lines.append("========================================")

    return "\n".join(lines)


def output_text(repo_root: Path | None = None) -> None:
    """Output context in text format.

    Args:
        repo_root: Repository root path. Defaults to auto-detected.
    """
    print(get_context_text(repo_root))


# =============================================================================
# Record Mode
# =============================================================================


def get_context_record_json(repo_root: Path | None = None) -> dict:
    """Get record-mode context as a dictionary.

    Focused on: my active tasks, git status, current task.
    """
    if repo_root is None:
        repo_root = get_repo_root()

    developer = get_developer(repo_root)
    tasks_dir = get_tasks_dir(repo_root)

    # Git info
    _, branch_out, _ = run_git(["branch", "--show-current"], cwd=repo_root)
    branch = branch_out.strip() or "unknown"

    _, status_out, _ = run_git(["status", "--porcelain"], cwd=repo_root)
    git_status_count = len([line for line in status_out.splitlines() if line.strip()])

    _, log_out, _ = run_git(["log", "--oneline", "-5"], cwd=repo_root)
    commits = []
    for line in log_out.splitlines():
        if line.strip():
            parts = line.split(" ", 1)
            if len(parts) >= 2:
                commits.append({"hash": parts[0], "message": parts[1]})

    # My tasks (single pass — collect statuses and filter by assignee)
    all_tasks_list = list(iter_active_tasks(tasks_dir))
    all_statuses = {t.dir_name: t.status for t in all_tasks_list}

    my_tasks = []
    for t in all_tasks_list:
        if t.assignee == developer:
            done = sum(
                1 for c in t.children if all_statuses.get(c) in ("completed", "done")
            )
            my_tasks.append(
                {
                    "dir": t.dir_name,
                    "title": t.title,
                    "status": t.status,
                    "priority": t.priority,
                    "children": list(t.children),
                    "childrenDone": done,
                    "parent": t.parent,
                    "meta": t.meta,
                }
            )

    # Current task
    current_task_info = None
    current_task = get_current_task(repo_root)
    if current_task:
        ct = load_task(repo_root / current_task)
        if ct:
            current_task_info = {
                "path": current_task,
                "name": ct.name,
                "status": ct.status,
            }

    # Package git repos
    pkg_git_info = _collect_package_git_info(repo_root)

    result = {
        "developer": developer or "",
        "git": {
            "branch": branch,
            "isClean": git_status_count == 0,
            "uncommittedChanges": git_status_count,
            "recentCommits": commits,
        },
        "myTasks": my_tasks,
        "currentTask": current_task_info,
        "sessionFreshness": _get_session_freshness_data(
            repo_root, get_active_journal_file(repo_root)
        ),
        "memory": _get_memory_data(repo_root),
    }

    if pkg_git_info:
        result["packageGit"] = pkg_git_info

    return result


def get_context_text_record(repo_root: Path | None = None) -> str:
    """Get context as formatted text for record-session mode.

    Focused output: MY ACTIVE TASKS first (with [!!!] emphasis),
    then GIT STATUS, RECENT COMMITS, CURRENT TASK.
    """
    if repo_root is None:
        repo_root = get_repo_root()

    lines: list[str] = []
    lines.append("========================================")
    lines.append("SESSION CONTEXT (RECORD MODE)")
    lines.append("========================================")
    lines.append("")

    developer = get_developer(repo_root)
    if not developer:
        lines.append(
            f"ERROR: Not initialized. Run: python3 ./{DIR_WORKFLOW}/{DIR_SCRIPTS}/init_developer.py <name>"
        )
        return "\n".join(lines)

    # MY ACTIVE TASKS — first and prominent
    lines.append(f"## [!!!] MY ACTIVE TASKS (Assigned to {developer})")
    lines.append(
        "[!] Review whether any should be archived before recording this session."
    )
    lines.append("")

    tasks_dir = get_tasks_dir(repo_root)
    my_task_count = 0

    # Single pass — collect all tasks and filter by assignee
    all_statuses = get_all_statuses(tasks_dir)

    for t in iter_active_tasks(tasks_dir):
        if t.assignee == developer:
            progress = children_progress(t.children, all_statuses)
            lines.append(
                f"- [{t.priority}] {t.title} ({t.status}){progress} — {t.dir_name}"
            )
            my_task_count += 1

    if my_task_count == 0:
        lines.append("(no active tasks assigned to you)")
    lines.append("")

    # GIT STATUS
    lines.append("## GIT STATUS")
    _, branch_out, _ = run_git(["branch", "--show-current"], cwd=repo_root)
    branch = branch_out.strip() or "unknown"
    lines.append(f"Branch: {branch}")

    _, status_out, _ = run_git(["status", "--porcelain"], cwd=repo_root)
    status_lines = [line for line in status_out.splitlines() if line.strip()]
    status_count = len(status_lines)

    if status_count == 0:
        lines.append("Working directory: Clean")
    else:
        lines.append(f"Working directory: {status_count} uncommitted change(s)")
        lines.append("")
        lines.append("Changes:")
        _, short_out, _ = run_git(["status", "--short"], cwd=repo_root)
        for line in short_out.splitlines()[:10]:
            lines.append(line)
    lines.append("")

    # RECENT COMMITS
    lines.append("## RECENT COMMITS")
    _, log_out, _ = run_git(["log", "--oneline", "-5"], cwd=repo_root)
    if log_out.strip():
        for line in log_out.splitlines():
            lines.append(line)
    else:
        lines.append("(no commits)")
    lines.append("")

    # Package git repos — independent sub-repositories
    _append_package_git_context(lines, _collect_package_git_info(repo_root))

    # CURRENT TASK
    lines.append("## CURRENT TASK")
    current_task = get_current_task(repo_root)
    if current_task:
        lines.append(f"Path: {current_task}")
        ct = load_task(repo_root / current_task)
        if ct:
            lines.append(f"Name: {ct.name}")
            lines.append(f"Status: {ct.status}")
    else:
        lines.append("(none)")
    lines.append("")

    # Session freshness
    lines.append("## SESSION FRESHNESS")
    journal_file = get_active_journal_file(repo_root)
    if current_task:
        if journal_file and journal_file.is_file():
            try:
                last_modified = journal_file.stat().st_mtime
                age_hours = int((time.time() - last_modified) / 3600)
                lines.append(f"Last journal update: {age_hours}h ago")
                if age_hours > 24:
                    lines.append(
                        "[!] WARNING: Journal not updated in >24h. Session may be stale."
                    )
            except OSError:
                pass
        _, status_out, _ = run_git(["status", "--porcelain"], cwd=repo_root)
        uncommitted = len([s for s in status_out.splitlines() if s.strip()])
        lines.append(f"Uncommitted changes: {uncommitted}")
    else:
        lines.append("No active task (session is fresh)")
    lines.append("")

    # Memory
    lines.append("## MEMORY")
    memory_dir = get_memory_dir(repo_root)
    if memory_dir.is_dir():
        decisions_count = _count_entries(memory_dir / FILE_DECISIONS, "## 20")
        issues_count = _count_entries(memory_dir / FILE_KNOWN_ISSUES, "## Issue:")
        learnings_count = _count_entries(memory_dir / FILE_LEARNINGS, "## 20")
        scratchpad_active = _is_scratchpad_active(memory_dir / FILE_SCRATCHPAD)

        lines.append(f"Decisions: {decisions_count}")
        lines.append(f"Known Issues: {issues_count}")
        lines.append(f"Learnings: {learnings_count}")
        lines.append(f"Scratchpad: {'Active' if scratchpad_active else 'Empty'}")
    else:
        lines.append("(memory directory not initialized)")
    lines.append("")

    lines.append("========================================")

    return "\n".join(lines)


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Get Session Context for AI Agent")
    parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output context in JSON format",
    )
    parser.add_argument(
        "--mode",
        choices=["default", "record"],
        default="default",
        help="Context mode: default (full) or record (focused)",
    )

    args = parser.parse_args()

    if args.mode == "record":
        if args.json:
            context = get_context_record_json()
            print(json.dumps(context, indent=2, ensure_ascii=False))
        else:
            print(get_context_text_record())
    else:
        if args.json:
            output_json()
        else:
            output_text()


if __name__ == "__main__":
    main()
