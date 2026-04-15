#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Codex Session Start Hook - Inject Trellis context into Codex sessions.

Output format follows Codex hook protocol:
  stdout JSON → { hookSpecificOutput: { hookEventName: "SessionStart", additionalContext: "..." } }
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import warnings
from io import StringIO
from pathlib import Path

warnings.filterwarnings("ignore")


LEGACY_MONOREPO_SPEC_MOVES = {
    "backend": "`spec/backend/` -> `spec/<package>/backend/`",
    "frontend": "`spec/frontend/` -> `spec/<package>/frontend/`",
    "python": "`spec/python/` -> `spec/<package>/python/`",
    "matlab": "`spec/matlab/` -> `spec/<package>/matlab/`",
}
LEGACY_SCIENTIFIC_ROOTS = {"python", "matlab"}


def should_skip_injection() -> bool:
    return os.environ.get("CODEX_NON_INTERACTIVE") == "1"


def read_file(path: Path, fallback: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, PermissionError):
        return fallback


def run_script(script_path: Path) -> str:
    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        cmd = [sys.executable, "-W", "ignore", str(script_path)]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            cwd=str(script_path.parent.parent.parent),
            env=env,
        )
        return result.stdout if result.returncode == 0 else "No context available"
    except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
        return "No context available"


def _get_task_status(trellis_dir: Path) -> str:
    current_task_file = trellis_dir / ".current-task"
    if not current_task_file.is_file():
        return "Status: NO ACTIVE TASK\nNext: Describe what you want to work on"

    task_ref = current_task_file.read_text(encoding="utf-8").strip()
    if not task_ref:
        return "Status: NO ACTIVE TASK\nNext: Describe what you want to work on"

    if Path(task_ref).is_absolute():
        task_dir = Path(task_ref)
    elif task_ref.startswith(".trellis/"):
        task_dir = trellis_dir.parent / task_ref
    else:
        task_dir = trellis_dir / "tasks" / task_ref

    if not task_dir.is_dir():
        return f"Status: STALE POINTER\nTask: {task_ref}\nNext: Task directory not found. Run: uv run python ./.trellis/scripts/task.py finish"

    task_json_path = task_dir / "task.json"
    task_data: dict = {}
    if task_json_path.is_file():
        try:
            task_data = json.loads(task_json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, PermissionError):
            pass

    task_title = task_data.get("title", task_ref)
    task_status = task_data.get("status", "unknown")

    if task_status == "completed":
        return f"Status: COMPLETED\nTask: {task_title}\nNext: Archive with `uv run python ./.trellis/scripts/task.py archive {task_dir.name}` or start a new task"

    has_context = False
    for jsonl_name in ("implement.jsonl", "check.jsonl", "review.jsonl", "spec.jsonl"):
        jsonl_path = task_dir / jsonl_name
        if jsonl_path.is_file() and jsonl_path.stat().st_size > 0:
            has_context = True
            break

    has_prd = (task_dir / "prd.md").is_file()

    if not has_prd:
        return f"Status: NOT READY\nTask: {task_title}\nMissing: prd.md not created\nNext: Write PRD, then research → init-context → start"

    if not has_context:
        return f"Status: NOT READY\nTask: {task_title}\nMissing: Context not configured (no jsonl files)\nNext: Complete Phase 2 (research → init-context → start) before implementing"

    return f"Status: READY\nTask: {task_title}\nNext: Continue with implement or check"


def _build_workflow_toc(workflow_path: Path) -> str:
    """Build a compact section index for workflow.md (lazy-load the full file on demand).

    Replaces full-file injection to keep additionalContext payload small.
    The full file is accessible via: Read tool on .trellis/workflow.md
    """
    content = read_file(workflow_path)
    if not content:
        return "No workflow.md found"

    toc_lines = [
        "# Development Workflow — Section Index",
        "Full guide: .trellis/workflow.md  (read on demand)",
        "",
    ]
    for line in content.splitlines():
        if line.startswith("## "):
            toc_lines.append(line)

    toc_lines += [
        "",
        "To read a section: use the Read tool on .trellis/workflow.md",
    ]
    return "\n".join(toc_lines)


def _load_trellis_config(trellis_dir: Path) -> tuple:
    """Load Trellis config for package-scoped guideline injection."""
    scripts_dir = trellis_dir / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    try:
        from common.config import (  # type: ignore[import-not-found]
            get_default_package,
            get_packages,
            get_spec_scope,
            is_monorepo,
        )
        from common.paths import get_current_task  # type: ignore[import-not-found]

        repo_root = trellis_dir.parent
        is_mono = is_monorepo(repo_root)
        packages = get_packages(repo_root) or {}
        scope = get_spec_scope(repo_root)

        task_pkg = None
        current = get_current_task(repo_root)
        if current:
            task_json = repo_root / current / "task.json"
            if task_json.is_file():
                try:
                    data = json.loads(task_json.read_text(encoding="utf-8"))
                    if isinstance(data, dict):
                        task_package = data.get("package")
                        if isinstance(task_package, str) and task_package:
                            task_pkg = task_package
                except (json.JSONDecodeError, OSError):
                    pass

        default_pkg = get_default_package(repo_root)
        return is_mono, packages, scope, task_pkg, default_pkg
    except Exception:
        return False, {}, None, None, None


def _check_legacy_spec(trellis_dir: Path, is_mono: bool, packages: dict) -> str | None:
    """Check for legacy spec directory structure in monorepo."""
    if not is_mono or not packages:
        return None

    spec_dir = trellis_dir / "spec"
    if not spec_dir.is_dir():
        return None

    legacy_roots = [
        name
        for name in LEGACY_MONOREPO_SPEC_MOVES
        if (spec_dir / name).is_dir() and (spec_dir / name / "index.md").is_file()
    ]
    if not legacy_roots:
        return None

    missing = [
        name for name in sorted(packages.keys()) if not (spec_dir / name).is_dir()
    ]
    legacy_paths = ", ".join(f"`spec/{name}/`" for name in legacy_roots)
    move_hint = "; ".join(LEGACY_MONOREPO_SPEC_MOVES[name] for name in legacy_roots)
    if not missing:
        return (
            f"[!] Legacy monorepo spec roots detected: {legacy_paths}\n"
            f"Monorepo packages: {', '.join(sorted(packages.keys()))}\n"
            f"Package-scoped specs are used in monorepo mode. Remove or migrate legacy roots: {move_hint}"
        )

    if len(missing) == len(packages):
        return (
            f"[!] Legacy spec structure detected: found {legacy_paths} but no "
            "`spec/<package>/` directories.\n"
            f"Monorepo packages: {', '.join(sorted(packages.keys()))}\n"
            f"Please reorganize: {move_hint}"
        )

    return (
        f"[!] Partial spec migration detected: found legacy roots {legacy_paths} "
        f"while packages {', '.join(missing)} still missing `spec/<pkg>/` directory.\n"
        f"Please complete migration for all packages. Target layout: {move_hint}"
    )


def _resolve_spec_scope(
    is_mono: bool,
    packages: dict,
    scope,
    task_pkg: str | None,
    default_pkg: str | None,
) -> set[str] | None:
    """Resolve which packages should have their specs injected."""
    if not is_mono or not packages:
        return None

    if scope is None:
        return None

    if isinstance(scope, str) and scope == "active_task":
        if task_pkg and task_pkg in packages:
            return {task_pkg}
        if default_pkg and default_pkg in packages:
            return {default_pkg}
        return None

    if isinstance(scope, list):
        valid = set()
        for entry in scope:
            if entry in packages:
                valid.add(entry)
            else:
                print(
                    f"Warning: spec_scope contains unknown package: {entry}, ignoring",
                    file=sys.stderr,
                )

        if valid:
            if task_pkg and task_pkg not in valid:
                print(
                    f"Warning: active task package '{task_pkg}' is out of configured spec_scope",
                    file=sys.stderr,
                )
            return valid

        print(
            "Warning: all spec_scope entries invalid, falling back to task/default/full",
            file=sys.stderr,
        )
        if task_pkg and task_pkg in packages:
            return {task_pkg}
        if default_pkg and default_pkg in packages:
            return {default_pkg}

    return None


def main() -> None:
    if should_skip_injection():
        sys.exit(0)

    # Read hook input from stdin
    try:
        hook_input = json.loads(sys.stdin.read())
        project_dir = Path(hook_input.get("cwd", ".")).resolve()
    except (json.JSONDecodeError, KeyError):
        project_dir = Path(".").resolve()

    trellis_dir = project_dir / ".trellis"
    is_mono, packages, scope_config, task_pkg, default_pkg = _load_trellis_config(
        trellis_dir
    )
    allowed_pkgs = _resolve_spec_scope(
        is_mono, packages, scope_config, task_pkg, default_pkg
    )

    output = StringIO()

    output.write("""<session-context>
You are starting a new session in a Trellis-managed project.
Read and follow all instructions below carefully.
</session-context>

""")

    legacy_warning = _check_legacy_spec(trellis_dir, is_mono, packages)
    if legacy_warning:
        output.write(
            f"<migration-warning>\n{legacy_warning}\n</migration-warning>\n\n"
        )

    output.write("<current-state>\n")
    context_script = trellis_dir / "scripts" / "get_context.py"
    output.write(run_script(context_script))
    output.write("\n</current-state>\n\n")

    output.write("<workflow>\n")
    output.write(_build_workflow_toc(trellis_dir / "workflow.md"))
    output.write("\n</workflow>\n\n")

    output.write("<guidelines>\n")
    output.write("**Note**: The guidelines below are index files — they list available guideline documents and their locations.\n")
    output.write("During actual development, you MUST read the specific guideline files listed in each index's Pre-Development Checklist.\n\n")

    spec_dir = trellis_dir / "spec"
    if spec_dir.is_dir():
        for sub in sorted(spec_dir.iterdir()):
            if not sub.is_dir() or sub.name.startswith("."):
                continue

            if sub.name == "guides":
                index_file = sub / "index.md"
                if index_file.is_file():
                    output.write(f"## {sub.name}\n")
                    output.write(read_file(index_file))
                    output.write("\n\n")
                continue

            if is_mono and packages and sub.name in LEGACY_SCIENTIFIC_ROOTS:
                continue

            index_file = sub / "index.md"
            if index_file.is_file():
                output.write(f"## {sub.name}\n")
                output.write(read_file(index_file))
                output.write("\n\n")
            else:
                if allowed_pkgs is not None and sub.name not in allowed_pkgs:
                    continue
                for nested in sorted(sub.iterdir()):
                    if not nested.is_dir():
                        continue
                    nested_index = nested / "index.md"
                    if nested_index.is_file():
                        output.write(f"## {sub.name}/{nested.name}\n")
                        output.write(read_file(nested_index))
                        output.write("\n\n")

    output.write("</guidelines>\n\n")

    task_status = _get_task_status(trellis_dir)
    output.write(f"<task-status>\n{task_status}\n</task-status>\n\n")

    output.write("""<ready>
Context loaded. Workflow index, project state, and guidelines are already injected above — do NOT re-read them.
Wait for the user's first message, then handle it following the workflow guide.
If there is an active task, ask whether to continue it.
</ready>""")

    context = output.getvalue()
    result = {
        "suppressOutput": True,
        "systemMessage": f"Trellis context injected ({len(context)} chars)",
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        },
    }

    print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
