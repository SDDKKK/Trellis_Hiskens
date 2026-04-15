#!/usr/bin/env python3
"""
Create Bootstrap Task for First-Time Setup.

Creates a guided task to help users fill in project guidelines
after initializing Trellis for the first time.

Usage:
    uv run python ./.trellis/scripts/create_bootstrap.py [project-type] [--package <package>]

Arguments:
    project-type: python | matlab | both (default: both)

Prerequisites:
    - .trellis/.developer must exist (run init_developer.py first)

Creates:
    .trellis/tasks/00-bootstrap-guidelines/
        - task.json    # Task metadata
        - prd.md       # Task description and guidance
"""

from __future__ import annotations

import json
import argparse
import sys
from datetime import datetime
from pathlib import Path

from common.config import (
    get_packages,
    get_spec_base,
    is_monorepo,
    resolve_package,
    validate_package,
)
from common.paths import (
    DIR_SCRIPTS,
    DIR_TASKS,
    DIR_WORKFLOW,
    get_developer,
    get_repo_root,
    get_tasks_dir,
    set_current_task,
)

# =============================================================================
# Constants
# =============================================================================

TASK_NAME = "00-bootstrap-guidelines"


# =============================================================================
# PRD Content
# =============================================================================


def write_prd_header() -> str:
    """Write PRD header section."""
    return """# Bootstrap: Fill Project Development Guidelines

## Purpose

Welcome to Trellis! This is your first task.

AI agents use `.trellis/spec/` to understand YOUR project's coding conventions.
**Empty templates = AI writes generic code that doesn't match your project style.**

Filling these guidelines is a one-time setup that pays off for every future AI session.

---

## Your Task

Fill in the guideline files based on your **existing codebase**.
"""


def write_prd_python_section(spec_base: str) -> str:
    """Write PRD Python section."""
    return f"""

### Python Guidelines

| File | What to Document |
|------|------------------|
| `.trellis/{spec_base}/python/directory-structure.md` | Python module layout (src/ structure) |
| `.trellis/{spec_base}/python/data-processing.md` | polars, data I/O, file formats |
| `.trellis/{spec_base}/python/code-style.md` | Code style, ruff, typing, architecture |
| `.trellis/{spec_base}/python/docstring.md` | Docstring and comment format |
| `.trellis/{spec_base}/python/quality-guidelines.md` | ruff, uv run, pytest |
"""


def write_prd_matlab_section(spec_base: str) -> str:
    """Write PRD MATLAB section."""
    return f"""

### MATLAB Guidelines

| File | What to Document |
|------|------------------|
| `.trellis/{spec_base}/matlab/code-style.md` | MATLAB code style and checkcode |
| `.trellis/{spec_base}/matlab/quality-guidelines.md` | MATLAB quality (checkcode L1-L5) |
| `.trellis/{spec_base}/matlab/docstring.md` | MATLAB docstring format |
"""


def write_prd_footer() -> str:
    """Write PRD footer section."""
    return """

### Thinking Guides (Optional)

The `.trellis/spec/guides/` directory contains thinking guides that are already
filled with general best practices. You can customize them for your project if needed.

---

## How to Fill Guidelines

### Principle: Document Reality, Not Ideals

Write what your codebase **actually does**, not what you wish it did.
AI needs to match existing patterns, not introduce new ones.

### Steps

1. **Look at existing code** - Find 2-3 examples of each pattern
2. **Document the pattern** - Describe what you see
3. **Include file paths** - Reference real files as examples
4. **List anti-patterns** - What does your team avoid?

---

## Tips for Using AI

Ask AI to help analyze your codebase:

- "Look at my codebase and document the patterns you see"
- "Analyze my code structure and summarize the conventions"
- "Find error handling patterns and document them"

The AI will read your code and help you document it.

---

## Completion Checklist

- [ ] Guidelines filled for your project type
- [ ] At least 2-3 real code examples in each guideline
- [ ] Anti-patterns documented

When done:

```bash
uv run python ./.trellis/scripts/task.py finish
uv run python ./.trellis/scripts/task.py archive 00-bootstrap-guidelines
```

---

## Why This Matters

After completing this task:

1. AI will write code that matches your project style
2. Relevant `/trellis:before-*-dev` commands will inject real context
3. `/trellis:check-*` commands will validate against your actual standards
4. Future developers (human or AI) will onboard faster
"""


def write_prd(task_dir: Path, project_type: str, spec_base: str) -> None:
    """Write prd.md file."""
    content = write_prd_header()

    if project_type == "matlab":
        content += write_prd_matlab_section(spec_base)
    elif project_type == "python":
        content += write_prd_python_section(spec_base)
    else:  # both
        content += write_prd_python_section(spec_base)
        content += write_prd_matlab_section(spec_base)

    content += write_prd_footer()

    prd_file = task_dir / "prd.md"
    prd_file.write_text(content, encoding="utf-8")


# =============================================================================
# Task JSON
# =============================================================================


def write_task_json(
    task_dir: Path,
    developer: str,
    project_type: str,
    spec_base: str,
    package: str | None,
) -> None:
    """Write task.json file."""
    today = datetime.now().strftime("%Y-%m-%d")

    # Generate subtasks and related files based on project type
    if project_type == "matlab":
        subtasks = [
            {"name": "Fill MATLAB guidelines", "status": "pending"},
            {"name": "Add code examples", "status": "pending"},
        ]
        related_files = [f".trellis/{spec_base}/matlab/"]
    elif project_type == "python":
        subtasks = [
            {"name": "Fill Python guidelines", "status": "pending"},
            {"name": "Add code examples", "status": "pending"},
        ]
        related_files = [f".trellis/{spec_base}/python/"]
    else:  # both
        subtasks = [
            {"name": "Fill Python guidelines", "status": "pending"},
            {"name": "Fill MATLAB guidelines", "status": "pending"},
            {"name": "Add code examples", "status": "pending"},
        ]
        related_files = [f".trellis/{spec_base}/python/", f".trellis/{spec_base}/matlab/"]

    task_data = {
        "id": TASK_NAME,
        "name": "Bootstrap Guidelines",
        "description": "Fill in project development guidelines for AI agents",
        "status": "in_progress",
        "dev_type": "docs",
        "package": package,
        "priority": "P1",
        "creator": developer,
        "assignee": developer,
        "createdAt": today,
        "completedAt": None,
        "commit": None,
        "subtasks": subtasks,
        "relatedFiles": related_files,
        "notes": f"First-time setup task created by trellis init ({project_type} project)",
    }

    task_json = task_dir / "task.json"
    task_json.write_text(
        json.dumps(task_data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


# =============================================================================
# Main
# =============================================================================


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Create Bootstrap Task for First-Time Setup"
    )
    parser.add_argument(
        "project_type",
        nargs="?",
        default="both",
        help="Project type: python | matlab | both (default: both)",
    )
    parser.add_argument("--package", help="Package name for monorepo projects")
    args = parser.parse_args()

    project_type = args.project_type

    # Validate project type
    if project_type not in ("python", "matlab", "both"):
        print(f"Unknown project type: {project_type}, defaulting to both")
        project_type = "both"

    repo_root = get_repo_root()
    developer = get_developer(repo_root)

    # Check developer initialized
    if not developer:
        print("Error: Developer not initialized")
        print(
            f"Run: uv run python ./{DIR_WORKFLOW}/{DIR_SCRIPTS}/init_developer.py <your-name>"
        )
        return 1

    package = args.package
    if package:
        if not is_monorepo(repo_root):
            print("Warning: --package ignored in single-repo project")
            package = None
        elif not validate_package(package, repo_root):
            packages = get_packages(repo_root)
            available = ", ".join(sorted(packages.keys())) if packages else "(none)"
            print(f"Error: unknown package '{package}'. Available: {available}")
            return 1
    else:
        package = resolve_package(repo_root=repo_root)

    spec_base = get_spec_base(package, repo_root)

    tasks_dir = get_tasks_dir(repo_root)
    task_dir = tasks_dir / TASK_NAME
    relative_path = f"{DIR_WORKFLOW}/{DIR_TASKS}/{TASK_NAME}"

    # Check if already exists
    if task_dir.exists():
        print(f"Bootstrap task already exists: {relative_path}")
        return 0

    # Create task directory
    task_dir.mkdir(parents=True, exist_ok=True)

    # Write files
    write_task_json(task_dir, developer, project_type, spec_base, package)
    write_prd(task_dir, project_type, spec_base)

    # Set as current task
    set_current_task(relative_path, repo_root)

    # Silent output - init command handles user-facing messages
    # Only output the task path for programmatic use
    print(relative_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
