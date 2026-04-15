"""
Trellis Context Assembly Module

Shared context assembly logic for both Claude Code hooks and Codex CLI scripts.
This module provides functions to assemble agent context from specs, PRD, memory, etc.

Usage:
    from common.context_assembly import get_implement_context, get_current_task

Note: This module is intentionally decoupled from Claude Code-specific environment
variables and hook infrastructure. It only reads files and returns strings.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .config import get_default_package, get_packages

# =============================================================================
# Path Constants (change here to rename directories)
# =============================================================================

DIR_WORKFLOW = ".trellis"
DIR_WORKSPACE = "workspace"
DIR_TASKS = "tasks"
DIR_SPEC = "spec"
FILE_CURRENT_TASK = ".current-task"
FILE_TASK_JSON = "task.json"
DIR_MEMORY = "memory"

# =============================================================================
# Subagent Constants (change here to rename subagent types)
# =============================================================================

AGENT_IMPLEMENT = "implement"
AGENT_CHECK = "check"
AGENT_REVIEW = "review"
AGENT_DEBUG = "debug"
AGENT_RESEARCH = "research"
AGENT_PLAN = "plan"

# Agents that require a task directory
AGENTS_REQUIRE_TASK = (AGENT_IMPLEMENT, AGENT_CHECK, AGENT_REVIEW, AGENT_DEBUG)
# All supported agents
AGENTS_ALL = (
    AGENT_IMPLEMENT,
    AGENT_CHECK,
    AGENT_REVIEW,
    AGENT_DEBUG,
    AGENT_RESEARCH,
    AGENT_PLAN,
)


# =============================================================================
# Basic Utility Functions
# =============================================================================


def find_repo_root(start_path: str) -> str | None:
    """
    Find git repo root from start_path upwards

    Returns:
        Repo root path, or None if not found
    """
    current = Path(start_path).resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return str(current)
        current = current.parent
    return None


def get_current_task(repo_root: str) -> str | None:
    """
    Read current task directory path from .trellis/.current-task

    Returns:
        Task directory relative path (relative to repo_root)
        None if not set
    """
    current_task_file = os.path.join(repo_root, DIR_WORKFLOW, FILE_CURRENT_TASK)
    if not os.path.exists(current_task_file):
        return None

    try:
        with open(current_task_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return content if content else None
    except Exception:
        return None


def read_file_content(base_path: str, file_path: str) -> str | None:
    """Read file content, return None if file doesn't exist"""
    full_path = os.path.join(base_path, file_path)
    if os.path.exists(full_path) and os.path.isfile(full_path):
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return None
    return None


def read_directory_contents(
    base_path: str, dir_path: str, max_files: int = 20
) -> list[tuple[str, str]]:
    """
    Read all .md files in a directory

    Args:
        base_path: Base path (usually repo_root)
        dir_path: Directory relative path
        max_files: Max files to read (prevent huge directories)

    Returns:
        [(file_path, content), ...]
    """
    full_path = os.path.join(base_path, dir_path)
    if not os.path.exists(full_path) or not os.path.isdir(full_path):
        return []

    results = []
    try:
        # Only read .md files, sorted by filename
        md_files = sorted(
            [
                f
                for f in os.listdir(full_path)
                if f.endswith(".md") and os.path.isfile(os.path.join(full_path, f))
            ]
        )

        for filename in md_files[:max_files]:
            file_full_path = os.path.join(full_path, filename)
            relative_path = os.path.join(dir_path, filename)
            try:
                with open(file_full_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    results.append((relative_path, content))
            except Exception:
                continue
    except Exception:
        pass

    return results


def read_jsonl_entries(base_path: str, jsonl_path: str) -> list[tuple[str, str]]:
    """
    Read all file/directory contents referenced in jsonl file

    Schema:
        {"file": "path/to/file.md", "reason": "..."}
        {"file": "path/to/dir/", "type": "directory", "reason": "..."}
        {"file": "path/to/dir/", "type": "reference", "reason": "..."}
        {"file": "path/to/file.md", "type": "reference", "reason": "..."}
        {"path": "path/to/file.md", "reason": "..."}  # "path" is alias for "file"

    Returns:
        [(path, content), ...]
    """
    full_path = os.path.join(base_path, jsonl_path)
    if not os.path.exists(full_path):
        return []

    results = []
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                    file_path = item.get("file") or item.get("path")
                    entry_type = item.get("type", "file")

                    if not file_path:
                        continue

                    if entry_type == "directory":
                        # Read all .md files in directory
                        dir_contents = read_directory_contents(base_path, file_path)
                        results.extend(dir_contents)
                    elif entry_type == "reference":
                        # Reference mode: inject only index.md from directory,
                        # or file with hint suffix
                        full_target = os.path.join(base_path, file_path)
                        if os.path.isdir(full_target):
                            index_path = os.path.join(file_path, "index.md")
                            content = read_file_content(base_path, index_path)
                            if content:
                                content += (
                                    "\n\n> This is a reference index. "
                                    "Use Read tool to access detailed "
                                    "sub-files when needed."
                                )
                                results.append((index_path, content))
                            else:
                                # Fallback: read first .md file
                                md_files = sorted(
                                    f
                                    for f in os.listdir(full_target)
                                    if f.endswith(".md")
                                )
                                if md_files:
                                    fb_path = os.path.join(file_path, md_files[0])
                                    fb_content = read_file_content(base_path, fb_path)
                                    if fb_content:
                                        results.append((fb_path, fb_content))
                        else:
                            content = read_file_content(base_path, file_path)
                            if content:
                                content += (
                                    "\n\n> This is a reference summary. "
                                    "Use Read tool to access detailed "
                                    "files listed above."
                                )
                                results.append((file_path, content))
                    else:
                        # Read single file
                        content = read_file_content(base_path, file_path)
                        if content:
                            results.append((file_path, content))
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass

    return results


# =============================================================================
# Memory Context Functions
# =============================================================================


def get_memory_context(repo_root: str, agent_type: str) -> str:
    """
    Get memory context for agents (Mod 1: Structured Memory).

    - implement/debug: decisions.md + known-issues.md + scratchpad.md
    - check/review: decisions.md only (understand architecture context)
    - others: no memory injection
    """
    if agent_type not in ("implement", "check", "debug"):
        return ""

    memory_dir = os.path.join(repo_root, DIR_WORKFLOW, DIR_MEMORY)
    if not os.path.isdir(memory_dir):
        return ""

    parts = []
    memory_files = []

    if agent_type in ("implement", "debug"):
        memory_files = ["decisions.md", "known-issues.md", "scratchpad.md"]
    elif agent_type == "check":
        memory_files = ["decisions.md"]

    for filename in memory_files:
        filepath = os.path.join(memory_dir, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content:
                    rel_path = f"{DIR_WORKFLOW}/{DIR_MEMORY}/{filename}"
                    parts.append(f"=== {rel_path} (Memory) ===\n{content}")
            except Exception:
                continue

    return "\n\n".join(parts)


def get_nocturne_hints(subagent_type: str) -> str:
    """
    Get Nocturne query hints for the specified agent type.

    Returns agent-specific hints about using Nocturne long-term memory.
    Agents can call MCP tools to read/search Nocturne memories.

    Args:
        subagent_type: Type of subagent (implement, check, debug, etc.)

    Returns:
        Formatted hints string, or empty string for unsupported agent types
    """
    if subagent_type not in (AGENT_IMPLEMENT, AGENT_CHECK, AGENT_REVIEW, AGENT_DEBUG):
        return ""

    # Common header for all agents
    hints = """## Long-Term Memory (Nocturne)

You have access to long-term memories via MCP tools:
- `read_memory(uri)` - Read a specific memory by URI
- `search_memory(query, domain="trellis")` - Search memories

Available URI namespaces:
- `trellis://patterns/python/...` - Python coding patterns
- `trellis://patterns/matlab/...` - MATLAB patterns
- `trellis://domain/power-systems/...` - Power system domain knowledge
- `trellis://domain/cim/...` - CIM standard knowledge
- `trellis://tools/claude-code/...` - Claude Code usage tips
- `trellis://projects/anhui-cim/...` - Project-specific memories
"""

    # Agent-specific guidance
    if subagent_type == AGENT_IMPLEMENT:
        hints += """
### When to Query Nocturne (Implement Agent)

**Before starting implementation:**
1. Query `trellis://patterns/python/` for language-specific patterns
2. Query `trellis://domain/power-systems/` or `trellis://domain/cim/` for domain knowledge
3. Query `trellis://tools/claude-code/` for tool usage tips

**During implementation:**
- Need error handling patterns? Query `trellis://patterns/python/error-handling`
- Working with data processing? Query `trellis://patterns/python/data-processing`
- Unsure about testing patterns? Query `trellis://patterns/python/testing`

**Common URI patterns to try:**
```
read_memory("trellis://patterns/python/idioms")
read_memory("trellis://patterns/python/error-handling/result-type")
read_memory("trellis://domain/power-systems/reliability/metrics")
read_memory("trellis://domain/cim/topology-processing/bus-branch")
```

**Search examples:**
```
search_memory("polars dataframe", domain="trellis")
search_memory("ruff type annotations", domain="trellis")
search_memory("MATLAB vectorization", domain="trellis")
```

**How to apply patterns:**
1. Read the pattern content
2. Understand the context and rationale
3. Adapt to your specific use case
4. Follow any referenced conventions
"""
    elif subagent_type in (AGENT_CHECK, AGENT_REVIEW):
        hints += """
### When to Query Nocturne (Check/Review Agent)

**Before code review:**
1. Query `trellis://patterns/python/` for verification criteria
2. Query `trellis://patterns/python/quality` for quality guidelines
3. Query `trellis://domain/power-systems/` for domain-specific rules

**During code review:**
- Checking code style? Query `trellis://patterns/python/code-style`
- Checking error handling? Query `trellis://patterns/python/error-handling`
- Checking cross-layer issues? Query `trellis://domain/power-systems/` for data format rules

**Common URI patterns to try:**
```
read_memory("trellis://patterns/python/quality-guidelines")
read_memory("trellis://patterns/python/code-style/ruff")
read_memory("trellis://domain/power-systems/data-formats")
read_memory("trellis://projects/anhui-cim/decisions")
```

**Search examples:**
```
search_memory("ruff polars", domain="trellis")
search_memory("cross-layer validation", domain="trellis")
search_memory("MATLAB checkcode", domain="trellis")
```

**How to verify against patterns:**
1. Query relevant quality patterns
2. Check if code follows documented conventions
3. Verify domain-specific rules are respected
4. Note any deviations and their justifications
"""
    elif subagent_type == AGENT_DEBUG:
        hints += """
### When to Query Nocturne (Debug Agent)

**Initial diagnosis:**
1. Query `trellis://projects/anhui-cim/known-issues` for active issues
2. Query `trellis://patterns/python/error-handling` for error patterns
3. Query `trellis://tools/claude-code/debugging` for debugging tips

**Deep investigation:**
- Specific error type? Query `trellis://patterns/python/error-handling/<type>`
- Cross-layer data issue? Query `trellis://domain/power-systems/data-formats`
- Tool usage problem? Query `trellis://tools/claude-code/<tool>`

**Common URI patterns to try:**
```
read_memory("trellis://projects/anhui-cim/known-issues")
read_memory("trellis://patterns/python/error-handling/result-type")
read_memory("trellis://patterns/python/error-handling/exceptions")
read_memory("trellis://tools/claude-code/debugging")
```

**Search examples:**
```
search_memory("common errors", domain="trellis")
search_memory("troubleshooting", domain="trellis")
search_memory("workaround", domain="trellis")
```

**How to use patterns for debugging:**
1. Search for similar issues in known-issues
2. Read relevant error handling patterns
3. Check if the fix follows established patterns
4. Verify the solution doesn't introduce new issues
"""

    return hints


# =============================================================================
# Agent Context Assembly Functions
# =============================================================================


def get_agent_context(repo_root: str, task_dir: str, agent_type: str) -> str:
    """
    Get complete context for specified agent

    Prioritize agent-specific jsonl, fallback to spec.jsonl if not exists
    """
    context_parts = []

    # 1. Try agent-specific jsonl
    agent_jsonl = f"{task_dir}/{agent_type}.jsonl"
    agent_entries = read_jsonl_entries(repo_root, agent_jsonl)

    # 2. If agent-specific jsonl doesn't exist or empty, fallback to spec.jsonl
    if not agent_entries:
        agent_entries = read_jsonl_entries(repo_root, f"{task_dir}/spec.jsonl")

    # 3. Add all files from jsonl
    for file_path, content in agent_entries:
        context_parts.append(f"=== {file_path} ===\n{content}")

    return "\n\n".join(context_parts)


def get_implement_context(repo_root: str, task_dir: str) -> str:
    """
    Complete context for Implement Agent

    Read order:
    1. All files in implement.jsonl (dev specs)
    2. prd.md (requirements)
    3. info.md (technical design)
    """
    context_parts = []

    # 1. Read implement.jsonl (or fallback to spec.jsonl)
    base_context = get_agent_context(repo_root, task_dir, "implement")
    if base_context:
        context_parts.append(base_context)

    # 2. Requirements document
    prd_content = read_file_content(repo_root, f"{task_dir}/prd.md")
    if prd_content:
        context_parts.append(f"=== {task_dir}/prd.md (Requirements) ===\n{prd_content}")

    # 3. Technical design
    info_content = read_file_content(repo_root, f"{task_dir}/info.md")
    if info_content:
        context_parts.append(
            f"=== {task_dir}/info.md (Technical Design) ===\n{info_content}"
        )

    # 4. Memory context (decisions + known-issues + scratchpad)
    memory_context = get_memory_context(repo_root, "implement")
    if memory_context:
        context_parts.append(memory_context)

    # 5. TDD context (conditional: only when task.json has tdd=true)
    task_json_path = os.path.join(repo_root, task_dir, FILE_TASK_JSON)
    if os.path.exists(task_json_path):
        try:
            with open(task_json_path, "r", encoding="utf-8") as f:
                task_config = json.load(f)
            if task_config.get("tdd", False):
                tdd_files = [
                    (
                        f"{DIR_WORKFLOW}/{DIR_SPEC}/guides/tdd-guide.md",
                        "TDD mode enabled",
                    ),
                    (
                        f"{DIR_WORKFLOW}/{DIR_SPEC}/unit-test/testing-anti-patterns.md",
                        "Testing anti-patterns",
                    ),
                ]
                for file_path, reason in tdd_files:
                    content = read_file_content(repo_root, file_path)
                    if content:
                        context_parts.append(
                            f"=== {file_path} ({reason}) ===\n{content}"
                        )
        except (json.JSONDecodeError, OSError):
            pass

    return "\n\n".join(context_parts)


def get_check_context(repo_root: str, task_dir: str) -> str:
    """
    Complete context for Check Agent

    Read order:
    1. All files in check.jsonl (check specs + dev specs)
    2. prd.md (for understanding task intent)
    """
    context_parts = []

    # 1. Read check.jsonl (or fallback to spec.jsonl + hardcoded check files)
    check_entries = read_jsonl_entries(repo_root, f"{task_dir}/check.jsonl")

    if check_entries:
        for file_path, content in check_entries:
            context_parts.append(f"=== {file_path} ===\n{content}")
    else:
        # Fallback: use hardcoded check files + spec.jsonl
        check_files = [
            (".claude/commands/trellis/finish-work.md", "Finish work checklist"),
            (".claude/commands/trellis/check-cross-layer.md", "Cross-layer check spec"),
            (".claude/commands/trellis/check-python.md", "Python check spec"),
            (".claude/commands/trellis/check-matlab.md", "MATLAB check spec"),
        ]
        for file_path, description in check_files:
            content = read_file_content(repo_root, file_path)
            if content:
                context_parts.append(f"=== {file_path} ({description}) ===\n{content}")

        # Add spec.jsonl
        spec_entries = read_jsonl_entries(repo_root, f"{task_dir}/spec.jsonl")
        for file_path, content in spec_entries:
            context_parts.append(f"=== {file_path} (Dev spec) ===\n{content}")

    # 2. Requirements document (for understanding task intent)
    prd_content = read_file_content(repo_root, f"{task_dir}/prd.md")
    if prd_content:
        context_parts.append(
            f"=== {task_dir}/prd.md (Requirements - for understanding intent) ===\n{prd_content}"
        )

    # 3. Memory context (decisions only for check)
    memory_context = get_memory_context(repo_root, "check")
    if memory_context:
        context_parts.append(memory_context)

    return "\n\n".join(context_parts)


def get_review_context(repo_root: str, task_dir: str) -> str:
    """
    Complete context for Review Agent.

    Read order:
    1. All files in review.jsonl (or fallback to check.jsonl)
    2. prd.md (for understanding task intent)
    """
    context_parts = []

    review_entries = read_jsonl_entries(repo_root, f"{task_dir}/review.jsonl")

    if review_entries:
        for file_path, content in review_entries:
            context_parts.append(f"=== {file_path} ===\n{content}")
    else:
        # Fallback: use check.jsonl entries
        check_entries = read_jsonl_entries(repo_root, f"{task_dir}/check.jsonl")
        for file_path, content in check_entries:
            context_parts.append(f"=== {file_path} ===\n{content}")

    prd_content = read_file_content(repo_root, f"{task_dir}/prd.md")
    if prd_content:
        context_parts.append(
            f"=== {task_dir}/prd.md (Requirements - for understanding intent) ===\n{prd_content}"
        )

    memory_context = get_memory_context(repo_root, "check")
    if memory_context:
        context_parts.append(memory_context)

    return "\n\n".join(context_parts)


def get_finish_context(repo_root: str, task_dir: str) -> str:
    """
    Complete context for Finish phase (final check before PR)

    Read order:
    1. All files in finish.jsonl (if exists)
    2. Fallback to finish-work.md only (lightweight final check)
    3. update-spec.md (for active spec sync — ALWAYS injected)
    4. prd.md (for verifying requirements are met)
    """
    context_parts = []

    # 1. Try finish.jsonl first
    finish_entries = read_jsonl_entries(repo_root, f"{task_dir}/finish.jsonl")

    if finish_entries:
        for file_path, content in finish_entries:
            context_parts.append(f"=== {file_path} ===\n{content}")
    else:
        # Fallback: only finish-work.md (lightweight)
        finish_work = read_file_content(
            repo_root, ".claude/commands/trellis/finish-work.md"
        )
        if finish_work:
            context_parts.append(
                f"=== .claude/commands/trellis/finish-work.md (Finish checklist) ===\n{finish_work}"
            )

    # 2. ALWAYS inject update-spec.md (for active spec sync)
    update_spec = read_file_content(
        repo_root, ".claude/commands/trellis/update-spec.md"
    )
    if update_spec:
        context_parts.append(
            f"=== .claude/commands/trellis/update-spec.md (Spec update process) ===\n{update_spec}"
        )

    # 3. Requirements document (for verifying requirements are met)
    prd_content = read_file_content(repo_root, f"{task_dir}/prd.md")
    if prd_content:
        context_parts.append(
            f"=== {task_dir}/prd.md (Requirements - verify all met) ===\n{prd_content}"
        )

    return "\n\n".join(context_parts)


def get_debug_context(repo_root: str, task_dir: str) -> str:
    """
    Complete context for Debug Agent

    Read order:
    1. All files in debug.jsonl (specs needed for fixing)
    2. codex-review-output.txt (Codex Review results)
    """
    context_parts = []

    # 1. Read debug.jsonl (or fallback to spec.jsonl + hardcoded check files)
    debug_entries = read_jsonl_entries(repo_root, f"{task_dir}/debug.jsonl")

    if debug_entries:
        for file_path, content in debug_entries:
            context_parts.append(f"=== {file_path} ===\n{content}")
    else:
        # Fallback: use spec.jsonl + hardcoded check files
        spec_entries = read_jsonl_entries(repo_root, f"{task_dir}/spec.jsonl")
        for file_path, content in spec_entries:
            context_parts.append(f"=== {file_path} (Dev spec) ===\n{content}")

        check_files = [
            (".claude/commands/trellis/check-python.md", "Python check spec"),
            (".claude/commands/trellis/check-matlab.md", "MATLAB check spec"),
            (".claude/commands/trellis/check-cross-layer.md", "Cross-layer check spec"),
        ]
        for file_path, description in check_files:
            content = read_file_content(repo_root, file_path)
            if content:
                context_parts.append(f"=== {file_path} ({description}) ===\n{content}")

    # 2. Codex review output (if exists)
    codex_output = read_file_content(repo_root, f"{task_dir}/codex-review-output.txt")
    if codex_output:
        context_parts.append(
            f"=== {task_dir}/codex-review-output.txt (Codex Review Results) ===\n{codex_output}"
        )

    # 3. Memory context (decisions + known-issues + scratchpad)
    memory_context = get_memory_context(repo_root, "debug")
    if memory_context:
        context_parts.append(memory_context)

    return "\n\n".join(context_parts)


def get_research_context(repo_root: str, task_dir: str | None) -> str:
    """
    Context for Research Agent

    Research doesn't need much preset context, only needs:
    1. Project structure overview (where spec directories are)
    2. Optional research.jsonl (if there are specific search needs)
    """
    context_parts = []

    # 1. Project structure overview (uses constants for paths)
    spec_path = f"{DIR_WORKFLOW}/{DIR_SPEC}"
    project_structure = f"""## Project Spec Directory Structure

```
{spec_path}/
├── python/      # Python standards (scientific computing, ruff, polars)
├── matlab/      # MATLAB standards (code style, checkcode)
├── guides/      # Thinking guides (cross-layer, code reuse, etc.)

{DIR_WORKFLOW}/big-question/  # Known issues and pitfalls
```

## Search Tips (Three-Layer External Search + Local Codebase)

- Spec files: `{spec_path}/**/*.md`
- Known issues: `{DIR_WORKFLOW}/big-question/`
- **GitHub repo analysis**: Read `{spec_path}/guides/github-analysis-guide.md` first, then follow its methodology (multi-source, tool selection, output checklist)
- **Local code search (semantic)**: Use `mcp__morph-mcp__warpgrep_codebase_search` (preferred, multi-turn parallel) or `mcp__augment-context-engine__codebase-retrieval` (fallback)
- Local code search (exact match): Use Grep tool
- Layer 0 (Library docs): Use mcp__context7__resolve-library-id then mcp__context7__query-docs
- Layer 1 (Quick answer): Use Bash("python3 .trellis/scripts/search/web_search.py '<query>'")
- Layer 2 (Structured search): Use web_search.py then web_fetch.py for key URLs
- Layer 3 (Deep research): Use multiple web_search.py rounds then web_fetch.py for verification
- Web search (Grok): Use Bash("python3 .trellis/scripts/search/web_search.py '<query>'")
- Web content (Grok): Use Bash("python3 .trellis/scripts/search/web_fetch.py '<url>'")
- Escalation: Layer 0 → 1 → 2 → 3. Start at lowest sufficient layer.
- Fallback: If morph-mcp unavailable, use codebase-retrieval for all semantic search needs"""

    context_parts.append(project_structure)

    # 2. If task directory exists, try reading research.jsonl (optional)
    if task_dir:
        research_entries = read_jsonl_entries(repo_root, f"{task_dir}/research.jsonl")
        if research_entries:
            context_parts.append(
                "\n## Additional Search Context (from research.jsonl)\n"
            )
            for file_path, content in research_entries:
                context_parts.append(f"=== {file_path} ===\n{content}")

    return "\n\n".join(context_parts)


def get_plan_context(repo_root: str, task_dir: str | None) -> str:
    """
    Context for Plan Agent.

    Plan agent evaluates requirements and configures task directories.
    It needs:
    1. Project spec directory overview (available categories)
    2. Optional plan.jsonl (if task directory exists)
    """
    context_parts = []

    # 1. Project spec directory overview
    spec_path = f"{DIR_WORKFLOW}/{DIR_SPEC}"
    repo_root_path = Path(repo_root)
    spec_root = repo_root_path / DIR_WORKFLOW / DIR_SPEC
    packages = get_packages(repo_root_path)

    if packages:
        default_pkg = get_default_package(repo_root_path)
        package_lines = []
        for package_name in sorted(packages):
            label = (
                f"{package_name} (default)"
                if package_name == default_pkg
                else package_name
            )
            package_spec_dir = spec_root / package_name
            if not package_spec_dir.is_dir():
                package_lines.append(
                    f"- {label}: missing `{spec_path}/{package_name}/`"
                )
                continue

            layers = sorted(
                entry.name
                for entry in package_spec_dir.iterdir()
                if entry.is_dir() and not entry.name.startswith(".")
            )
            if layers:
                package_lines.append(
                    f"- {label}: "
                    + ", ".join(
                        f"`{spec_path}/{package_name}/{layer}/`" for layer in layers
                    )
                )
            else:
                package_lines.append(
                    f"- {label}: no layer directories found under `{spec_path}/{package_name}/`"
                )

        legacy_dirs = []
        if spec_root.is_dir():
            for entry in sorted(spec_root.iterdir()):
                if not entry.is_dir() or entry.name.startswith("."):
                    continue
                if entry.name in packages or entry.name == "guides":
                    continue
                legacy_dirs.append(entry.name)

        guides_line = (
            f"- shared guides: `{spec_path}/guides/`"
            if (spec_root / "guides").is_dir()
            else "- shared guides: not found"
        )
        legacy_block = ""
        if legacy_dirs:
            legacy_block = (
                "\n\n## Legacy Flat Spec Directories\n\n"
                + "\n".join(f"- `{spec_path}/{entry}/`" for entry in legacy_dirs)
            )

        project_structure = f"""## Project Spec Directory

Mode: monorepo

## Declared Packages

{chr(10).join(package_lines) if package_lines else "- (no packages found)"}

## Shared Spec Roots

{guides_line}{legacy_block}

## Available Dev Types

- `python` — Python development (scientific computing)
- `matlab` — MATLAB development
- `both` — Cross-layer Python + MATLAB"""
    else:
        categories = []
        if spec_root.is_dir():
            for entry in sorted(spec_root.iterdir()):
                if not entry.is_dir():
                    continue
                index_file = entry / "index.md"
                has_index = index_file.exists()
                categories.append(
                    f"  ├── {entry.name}/" + (" (has index.md)" if has_index else "")
                )

        category_tree = (
            "\n".join(categories) if categories else "  (no categories found)"
        )
        project_structure = f"""## Project Spec Directory

```
{spec_path}/
{category_tree}
```

## Available Dev Types

- `python` — Python development (scientific computing)
- `matlab` — MATLAB development
- `both` — Cross-layer Python + MATLAB"""

    context_parts.append(project_structure)

    # 2. If task directory exists, try reading plan.jsonl (optional)
    if task_dir:
        plan_entries = read_jsonl_entries(repo_root, f"{task_dir}/plan.jsonl")
        if plan_entries:
            context_parts.append("\n## Additional Plan Context (from plan.jsonl)\n")
            for file_path, content in plan_entries:
                context_parts.append(f"=== {file_path} ===\n{content}")

    return "\n\n".join(context_parts)
