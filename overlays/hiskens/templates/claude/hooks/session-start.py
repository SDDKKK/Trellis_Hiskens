#!/usr/bin/env python3
"""
Session Start Hook - Inject structured context

Matcher: "startup" - only runs on normal startup (not resume/clear/compact)

This hook injects:
1. Current state (git status, current task, task queue)
2. Workflow guide
3. Guidelines index (python/matlab/guides)
4. Session instructions (start.md)
5. Action directive
"""

import os
import subprocess
import sys
from pathlib import Path

# Add nocturne_client to path for importing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".trellis" / "scripts"))

try:
    from nocturne_client import NocturneClient
except ImportError:
    NocturneClient = None  # type: ignore[misc,assignment]


def should_skip_injection() -> bool:
    """
    Determine if context injection should be skipped.

    Multi-agent scripts (start.py, plan.py) set CLAUDE_NON_INTERACTIVE=1
    to prevent duplicate context injection.
    """
    return os.environ.get("CLAUDE_NON_INTERACTIVE") == "1"


def read_file(path: Path, fallback: str = "") -> str:
    """Read file content, return fallback if not found."""
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, PermissionError):
        return fallback


def run_script(script_path: Path) -> str:
    """Run a script and return its output."""
    try:
        result = subprocess.run(
            [str(script_path)],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=script_path.parent.parent.parent,  # repo root
        )
        return result.stdout if result.returncode == 0 else "No context available"
    except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
        return "No context available"


def get_memory_summary(trellis_dir: Path) -> str:
    """Build lightweight memory summary for session injection."""
    memory_dir = trellis_dir / "memory"
    if not memory_dir.exists():
        return ""

    parts = []

    # Scratchpad (full content — it's ephemeral and short)
    scratchpad = memory_dir / "scratchpad.md"
    if scratchpad.exists():
        content = read_file(scratchpad)
        if content.strip() and "(No active task)" not in content:
            parts.append(f"## Scratchpad (current WIP)\n{content}")

    # Last 5 decisions (parse ## headers only)
    decisions = memory_dir / "decisions.md"
    if decisions.exists():
        content = read_file(decisions)
        headers = [line for line in content.split("\n") if line.startswith("## 20")]
        if headers:
            parts.append(f"## Recent Decisions ({len(headers)} total)")
            for h in headers[:5]:
                parts.append(f"- {h.lstrip('# ')}")

    # Active known issues (titles only)
    known_issues = memory_dir / "known-issues.md"
    if known_issues.exists():
        content = read_file(known_issues)
        issues = [line for line in content.split("\n") if line.startswith("## Issue:")]
        if issues:
            parts.append(f"## Known Issues ({len(issues)} active)")
            for issue in issues:
                parts.append(f"- {issue.lstrip('# ')}")

    # Learnings count + last 3 titles
    learnings = memory_dir / "learnings.md"
    if learnings.exists():
        content = read_file(learnings)
        entries = [line for line in content.split("\n") if line.startswith("## 20")]
        if entries:
            parts.append(f"## Learnings ({len(entries)} recorded)")
            for e in entries[-3:]:
                parts.append(f"- {e.lstrip('# ')}")

    return "\n".join(parts) if parts else ""


def get_nocturne_context(trellis_dir: Path) -> str:
    """
    Build Nocturne long-term memory context for session injection.

    Reads high-priority memories from Nocturne SQLite database based on
    auto_load_patterns configuration in nocturne.yaml.

    Args:
        trellis_dir: Path to .trellis directory

    Returns:
        Formatted Nocturne context string, or empty string if unavailable
    """
    # Check if Nocturne client is available
    if NocturneClient is None:
        return ""

    config_path = trellis_dir / "config" / "nocturne.yaml"

    # Check if config exists and is enabled
    if not config_path.exists():
        return ""

    try:
        import yaml

        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        if not config or not isinstance(config, dict):
            return ""

        # Check if enabled
        if not config.get("enabled", True):
            return ""

        # Get project_id
        project_id = config.get("project_id", "")

        # Get auto_load_patterns
        auto_load_patterns = config.get("auto_load_patterns", [])
        priority_threshold = config.get("priority_threshold", 2)

        if not auto_load_patterns and not project_id:
            return ""

        # Create client and check availability
        client = NocturneClient()
        if not client.is_available():
            return ""

        parts = []
        all_memories = []

        # Query patterns from auto_load_patterns
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
                # Filter by priority threshold
                memories = [m for m in memories if m.priority <= priority_threshold]
                all_memories.extend(memories)
            except Exception:
                continue

        # Query project-specific memories
        if project_id:
            try:
                project_memories = client.get_project_memories(
                    project_id, max_results=10
                )
                # Filter by priority threshold
                project_memories = [
                    m for m in project_memories if m.priority <= priority_threshold
                ]
                all_memories.extend(project_memories)
            except Exception:
                pass

        # Remove duplicates (by URI) and sort by priority
        seen_uris = set()
        unique_memories = []
        for m in all_memories:
            if m.uri not in seen_uris:
                seen_uris.add(m.uri)
                unique_memories.append(m)

        unique_memories.sort(key=lambda x: (x.priority, x.uri))

        # Format output (limit to first 20 memories to keep context size reasonable)
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
                # Truncate content if too long (first 500 chars)
                content = memory.content.strip()
                if len(content) > 500:
                    content = content[:500] + "..."
                parts.append(content)
                parts.append("")

        client.close()
        return "\n".join(parts) if parts else ""

    except Exception:
        # Graceful degradation: return empty string on any error
        return ""


def get_stale_session_warning(trellis_dir: Path, project_dir: Path) -> str:
    """Detect stale/interrupted sessions and provide recovery context."""
    import json as _json

    current_task_file = trellis_dir / ".current-task"
    if not current_task_file.exists():
        return ""

    task_rel = read_file(current_task_file).strip()
    if not task_rel:
        return ""

    task_dir = project_dir / task_rel
    if not task_dir.exists():
        return f"WARNING: .current-task points to non-existent directory: {task_rel}\nRun: python3 ./.trellis/scripts/task.py finish"

    parts = ["WARNING: Previous session may not have ended cleanly."]
    parts.append(f"Active task: {task_rel}")

    # Task info from task.json
    task_json = task_dir / "task.json"
    if task_json.exists():
        try:
            data = _json.loads(task_json.read_text(encoding="utf-8"))
            parts.append(f"Title: {data.get('title', 'unknown')}")
            parts.append(f"Status: {data.get('status', 'unknown')}")
            parts.append(f"Phase: {data.get('current_phase', 0)}")
        except Exception:
            pass

    # PRD preview (first 5 non-empty lines)
    prd = task_dir / "prd.md"
    if prd.exists():
        lines = [line.strip() for line in read_file(prd).split("\n") if line.strip()][
            :5
        ]
        parts.append(f"PRD preview: {' '.join(lines)[:200]}")

    # Git diff stat
    try:
        result = subprocess.run(
            ["git", "diff", "--stat"],
            capture_output=True,
            text=True,
            timeout=3,
            cwd=str(project_dir),
        )
        if result.stdout.strip():
            parts.append(f"Uncommitted changes:\n{result.stdout.strip()}")
    except Exception:
        pass

    # Scratchpad content
    scratchpad = trellis_dir / "memory" / "scratchpad.md"
    if scratchpad.exists():
        content = read_file(scratchpad).strip()
        if content and "(No active task)" not in content:
            parts.append(f"Scratchpad:\n{content[:500]}")

    return "\n".join(parts)


def main():
    # Skip injection in non-interactive mode (multi-agent scripts set CLAUDE_NON_INTERACTIVE=1)
    if should_skip_injection():
        sys.exit(0)

    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")).resolve()
    trellis_dir = project_dir / ".trellis"
    claude_dir = project_dir / ".claude"

    # 1. Header
    print("""<session-context>
You are starting a new session in a Trellis-managed project.
Read and follow all instructions below carefully.
</session-context>
""")

    # 2. Current Context (dynamic)
    print("<current-state>")
    context_script = trellis_dir / "scripts" / "get_context.py"
    print(run_script(context_script))
    print("</current-state>")
    print()

    # 2.5. Stale session warning (before memory, so user sees it first)
    stale_warning = get_stale_session_warning(trellis_dir, project_dir)
    if stale_warning:
        print("<stale-session-warning>")
        print(stale_warning)
        print("</stale-session-warning>")
        print()

    # 2.6. Memory summary (lightweight)
    memory_summary = get_memory_summary(trellis_dir)
    if memory_summary:
        print("<memory>")
        print(memory_summary)
        print("</memory>")
        print()

    # 2.7. Nocturne long-term memory
    nocturne_context = get_nocturne_context(trellis_dir)
    if nocturne_context:
        print("<nocturne>")
        print(nocturne_context)
        print("</nocturne>")
        print()

    # 2.8. Thinking Framework (lightweight skeleton — always injected)
    print("<thinking-framework>")
    print("""# Main Agent Thinking Framework (Skeleton)

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

**Full methodology**: `cat .trellis/spec/guides/thinking-framework.md`""")
    print("</thinking-framework>")
    print()

    # 3. Workflow Guide
    print("<workflow>")
    workflow_content = read_file(trellis_dir / "workflow.md", "No workflow.md found")
    print(workflow_content)
    print("</workflow>")
    print()

    # 4. Guidelines Index
    print("<guidelines>")

    print("## Python")
    python_index = read_file(
        trellis_dir / "spec" / "python" / "index.md", "Not configured"
    )
    print(python_index)
    print()

    print("## MATLAB")
    matlab_index = read_file(
        trellis_dir / "spec" / "matlab" / "index.md", "Not configured"
    )
    print(matlab_index)
    print()

    print("## Guides")
    guides_index = read_file(
        trellis_dir / "spec" / "guides" / "index.md", "Not configured"
    )
    print(guides_index)

    print("</guidelines>")
    print()

    # 5. Session Instructions
    print("<instructions>")
    start_md = read_file(
        claude_dir / "commands" / "trellis" / "start.md", "No start.md found"
    )
    print(start_md)
    print("</instructions>")
    print()

    # 6. Final directive
    print("""<ready>
Context loaded. Wait for user's first message, then follow <instructions> to handle their request.
</ready>""")


if __name__ == "__main__":
    main()
