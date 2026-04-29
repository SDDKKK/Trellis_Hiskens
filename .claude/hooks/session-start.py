#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Session Start Hook - Inject structured context.
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

if sys.platform == "win32":
    import io as _io

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    elif hasattr(sys.stdout, "detach"):
        sys.stdout = _io.TextIOWrapper(  # type: ignore[union-attr]
            sys.stdout.detach(), encoding="utf-8", errors="replace"
        )


SCRIPTS_DIR = Path(__file__).parent.parent.parent / ".trellis" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

try:
    from nocturne_client import NocturneClient
except ImportError:
    NocturneClient = None  # type: ignore[misc,assignment]


LEGACY_MONOREPO_SPEC_MOVES = {
    "backend": "`spec/backend/` -> `spec/<package>/backend/`",
    "frontend": "`spec/frontend/` -> `spec/<package>/frontend/`",
    "python": "`spec/python/` -> `spec/<package>/python/`",
    "matlab": "`spec/matlab/` -> `spec/<package>/matlab/`",
}
LEGACY_SCIENTIFIC_ROOTS = {"python", "matlab"}


def should_skip_injection() -> bool:
    return (
        os.environ.get("CLAUDE_NON_INTERACTIVE") == "1"
        or os.environ.get("OPENCODE_NON_INTERACTIVE") == "1"
    )


def read_file(path: Path, fallback: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, PermissionError):
        return fallback


def run_script(script_path: Path) -> str:
    try:
        if script_path.suffix == ".py":
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            cmd = [sys.executable, "-W", "ignore", str(script_path)]
        else:
            env = os.environ.copy()
            cmd = [str(script_path)]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            cwd=script_path.parent.parent.parent,
            env=env,
        )
        return result.stdout if result.returncode == 0 else "No context available"
    except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
        return "No context available"


def _normalize_task_ref(task_ref: str) -> str:
    normalized = task_ref.strip()
    if not normalized:
        return ""

    path_obj = Path(normalized)
    if path_obj.is_absolute():
        return str(path_obj)

    normalized = normalized.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]

    if normalized.startswith("tasks/"):
        return f".trellis/{normalized}"

    return normalized


def _resolve_task_dir(trellis_dir: Path, task_ref: str) -> Path:
    normalized = _normalize_task_ref(task_ref)
    path_obj = Path(normalized)
    if path_obj.is_absolute():
        return path_obj
    if normalized.startswith(".trellis/"):
        return trellis_dir.parent / path_obj
    return trellis_dir / "tasks" / path_obj


def _get_task_status(trellis_dir: Path) -> str:
    """Check current task status and return structured status string."""
    current_task_file = trellis_dir / ".current-task"
    if not current_task_file.is_file():
        return "Status: NO ACTIVE TASK\nNext: Describe what you want to work on"

    task_ref = _normalize_task_ref(current_task_file.read_text(encoding="utf-8").strip())
    if not task_ref:
        return "Status: NO ACTIVE TASK\nNext: Describe what you want to work on"

    task_dir = _resolve_task_dir(trellis_dir, task_ref)
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


def _load_trellis_config(trellis_dir: Path) -> tuple:
    """Load Trellis config for session-start decisions."""
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


def get_memory_summary(trellis_dir: Path) -> str:
    """Build lightweight memory summary for session injection."""
    memory_dir = trellis_dir / "memory"
    if not memory_dir.exists():
        return ""

    parts = []

    scratchpad = memory_dir / "scratchpad.md"
    if scratchpad.exists():
        content = read_file(scratchpad)
        if content.strip() and "(No active task)" not in content:
            parts.append(f"## Scratchpad (current WIP)\n{content}")

    decisions = memory_dir / "decisions.md"
    if decisions.exists():
        content = read_file(decisions)
        headers = [line for line in content.split("\n") if line.startswith("## 20")]
        if headers:
            parts.append(f"## Recent Decisions ({len(headers)} total)")
            for header in headers[:5]:
                parts.append(f"- {header.lstrip('# ')}")

    known_issues = memory_dir / "known-issues.md"
    if known_issues.exists():
        content = read_file(known_issues)
        issues = [line for line in content.split("\n") if line.startswith("## Issue:")]
        if issues:
            parts.append(f"## Known Issues ({len(issues)} active)")
            for issue in issues:
                parts.append(f"- {issue.lstrip('# ')}")

    learnings = memory_dir / "learnings.md"
    if learnings.exists():
        content = read_file(learnings)
        entries = [line for line in content.split("\n") if line.startswith("## 20")]
        if entries:
            parts.append(f"## Learnings ({len(entries)} recorded)")
            for entry in entries[-3:]:
                parts.append(f"- {entry.lstrip('# ')}")

    return "\n".join(parts) if parts else ""


def get_nocturne_context(trellis_dir: Path) -> str:
    """Build Nocturne long-term memory context for session injection."""
    if NocturneClient is None:
        return ""

    config_path = trellis_dir / "config" / "nocturne.yaml"
    if not config_path.exists():
        return ""

    try:
        import yaml

        with config_path.open(encoding="utf-8") as handle:
            config = yaml.safe_load(handle)

        if not config or not isinstance(config, dict):
            return ""

        if not config.get("enabled", True):
            return ""

        project_id = config.get("project_id", "")
        auto_load_patterns = config.get("auto_load_patterns", [])
        priority_threshold = config.get("priority_threshold", 2)
        if not auto_load_patterns and not project_id:
            return ""

        client = NocturneClient()
        if not client.is_available():
            return ""

        parts = []
        all_memories = []

        for pattern in auto_load_patterns:
            if not isinstance(pattern, dict):
                continue

            domain = pattern.get("domain", "trellis")
            prefix = pattern.get("path_prefix", "")
            max_results = pattern.get("max_results", 10)
            if not prefix:
                continue

            try:
                memories = client.query_patterns(domain, prefix, max_results)
                all_memories.extend(
                    memory
                    for memory in memories
                    if memory.priority <= priority_threshold
                )
            except Exception:
                continue

        if project_id:
            try:
                project_memories = client.get_project_memories(
                    project_id, max_results=10
                )
                all_memories.extend(
                    memory
                    for memory in project_memories
                    if memory.priority <= priority_threshold
                )
            except Exception:
                pass

        seen_uris = set()
        unique_memories = []
        for memory in all_memories:
            if memory.uri in seen_uris:
                continue
            seen_uris.add(memory.uri)
            unique_memories.append(memory)

        unique_memories.sort(key=lambda item: (item.priority, item.uri))

        if unique_memories:
            parts.append(f"## Nocturne Memories ({len(unique_memories)} loaded)")
            parts.append("")
            for memory in unique_memories[:20]:
                priority_label = ""
                if memory.priority == 0:
                    priority_label = " [CRITICAL]"
                elif memory.priority == 1:
                    priority_label = " [HIGH]"

                parts.append(f"### {memory.uri}{priority_label}")
                if memory.disclosure:
                    parts.append(f"**When to use**: {memory.disclosure}")
                content = memory.content.strip()
                if len(content) > 500:
                    content = content[:500] + "..."
                parts.append(content)
                parts.append("")

        client.close()
        return "\n".join(parts) if parts else ""
    except Exception:
        return ""


def get_stale_session_warning(trellis_dir: Path, project_dir: Path) -> str:
    """Detect stale/interrupted sessions and provide recovery context."""
    current_task_file = trellis_dir / ".current-task"
    if not current_task_file.is_file():
        return ""

    task_ref = _normalize_task_ref(read_file(current_task_file).strip())
    if not task_ref:
        return ""

    task_dir = _resolve_task_dir(trellis_dir, task_ref)
    if not task_dir.exists():
        return f"WARNING: .current-task points to non-existent directory: {task_ref}\nRun: uv run python ./.trellis/scripts/task.py finish"

    parts = ["WARNING: Previous session may not have ended cleanly."]
    parts.append(f"Active task: {task_ref}")

    task_json = task_dir / "task.json"
    if task_json.exists():
        try:
            data = json.loads(task_json.read_text(encoding="utf-8"))
            parts.append(f"Title: {data.get('title', 'unknown')}")
            parts.append(f"Status: {data.get('status', 'unknown')}")
            parts.append(f"Phase: {data.get('current_phase', 0)}")
        except Exception:
            pass

    prd = task_dir / "prd.md"
    if prd.exists():
        lines = [line.strip() for line in read_file(prd).split("\n") if line.strip()][:5]
        parts.append(f"PRD preview: {' '.join(lines)[:200]}")

    try:
        result = subprocess.run(
            ["git", "diff", "--stat"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=3,
            cwd=str(project_dir),
        )
        if result.stdout.strip():
            parts.append(f"Uncommitted changes:\n{result.stdout.strip()}")
    except Exception:
        pass

    scratchpad = trellis_dir / "memory" / "scratchpad.md"
    if scratchpad.exists():
        content = read_file(scratchpad).strip()
        if content and "(No active task)" not in content:
            parts.append(f"Scratchpad:\n{content[:500]}")

    return "\n".join(parts)


def _build_workflow_toc(workflow_path: Path) -> str:
    """Build a compact section index for workflow.md."""
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


def _thinking_framework_text() -> str:
    return """# Main Agent Thinking Framework (Skeleton)

## When to Apply

| Complexity | Think | Plan | Reflect |
|------------|-------|------|---------|
| Trivial    | Skip  | Skip | Skip    |
| Simple     | Premise Check only | Skip | Skip |
| Moderate   | Full 1a-1d | Temporal + Error Map | Full |
| Complex    | Full 1a-1d | Full (+ Architecture) | Full |

## Think Phase — New tasks only, skip when continuing

1a. Restate understanding — confirm shared mental model
1b. Premise Challenge — extract 2-3 implicit assumptions, validate each (agree/disagree/adjust)
1c. Code Mapping — what sub-problems exist? what code already covers them?
1d. Scope Decision — EXPANSION / SELECTIVE_EXPANSION / HOLD_SCOPE / REDUCTION

## Plan Phase — Moderate/Complex tasks, during brainstorm

2a. Temporal Walk-through — HOUR 1 (foundation) / 2-3 (core ambiguities) / 4-5 (surprises) / 6+ (regrets)
2b. Error & Rescue Map — table of Operation | Failure Mode | Impact | Rescue Strategy
2c. Architecture Sketch — data flow diagram + dependencies + boundary conditions (3+ modules)

## Reflect Phase — After code changes, before commit

3a. Process Review — were premises accurate? what was unexpected? what caused rework?
3b. Pattern Extraction — new gotcha -> learnings.md / new convention -> /trellis:update-spec
3c. Brief structured reflection (3-5 lines) for journal

**Full methodology**: `cat .trellis/spec/guides/thinking-framework.md`"""


def main() -> None:
    if should_skip_injection():
        sys.exit(0)

    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")).resolve()
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

    stale_warning = get_stale_session_warning(trellis_dir, project_dir)
    if stale_warning:
        output.write(
            f"<stale-session-warning>\n{stale_warning}\n</stale-session-warning>\n\n"
        )

    memory_summary = get_memory_summary(trellis_dir)
    if memory_summary:
        output.write(f"<memory>\n{memory_summary}\n</memory>\n\n")

    nocturne_context = get_nocturne_context(trellis_dir)
    if nocturne_context:
        output.write(f"<nocturne>\n{nocturne_context}\n</nocturne>\n\n")

    output.write("<thinking-framework>\n")
    output.write(_thinking_framework_text())
    output.write("\n</thinking-framework>\n\n")

    output.write("<workflow>\n")
    output.write(_build_workflow_toc(trellis_dir / "workflow.md"))
    output.write("\n</workflow>\n\n")

    output.write("<guidelines>\n")
    output.write(
        "**Note**: The guidelines below are index files — they list available guideline documents and their locations.\n"
    )
    output.write(
        "During actual development, you MUST read the specific guideline files listed in each index's Pre-Development Checklist.\n\n"
    )

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
                continue

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

    result = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": output.getvalue(),
        }
    }
    print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
