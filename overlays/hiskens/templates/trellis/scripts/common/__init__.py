"""
Common utilities for Trellis workflow scripts.

This module provides shared functionality used by other Trellis scripts.
"""

import io
import sys

# =============================================================================
# Windows Encoding Fix (MUST be at top, before any other output)
# =============================================================================
# On Windows, stdout defaults to the system code page (often GBK/CP936).
# This causes UnicodeEncodeError when printing non-ASCII characters.
#
# Any script that imports from common will automatically get this fix.
# =============================================================================


def _configure_stream(stream: object) -> object:
    """Configure a stream for UTF-8 encoding on Windows."""
    # Try reconfigure() first (Python 3.7+, more reliable)
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        return stream
    # Fallback: detach and rewrap with TextIOWrapper
    elif hasattr(stream, "detach"):
        return io.TextIOWrapper(
            stream.detach(),  # type: ignore[union-attr]
            encoding="utf-8",
            errors="replace",
        )
    return stream


if sys.platform == "win32":
    sys.stdout = _configure_stream(sys.stdout)  # type: ignore[assignment]
    sys.stderr = _configure_stream(sys.stderr)  # type: ignore[assignment]
    sys.stdin = _configure_stream(sys.stdin)  # type: ignore[assignment]


def configure_encoding() -> None:
    """
    Configure stdout/stderr/stdin for UTF-8 encoding on Windows.

    This is automatically called when importing from common,
    but can be called manually for scripts that don't import common.

    Safe to call multiple times.
    """
    global sys
    if sys.platform == "win32":
        sys.stdout = _configure_stream(sys.stdout)  # type: ignore[assignment]
        sys.stderr = _configure_stream(sys.stderr)  # type: ignore[assignment]
        sys.stdin = _configure_stream(sys.stdin)  # type: ignore[assignment]


from .paths import (  # noqa: E402
    DIR_WORKFLOW,
    DIR_WORKSPACE,
    DIR_TASKS,
    DIR_ARCHIVE,
    DIR_SPEC,
    DIR_SCRIPTS,
    DIR_MEMORY,
    FILE_DEVELOPER,
    FILE_CURRENT_TASK,
    FILE_TASK_JSON,
    FILE_JOURNAL_PREFIX,
    FILE_DECISIONS,
    FILE_KNOWN_ISSUES,
    FILE_SCRATCHPAD,
    FILE_LEARNINGS,
    get_repo_root,
    get_developer,
    check_developer,
    get_tasks_dir,
    get_workspace_dir,
    get_memory_dir,
    ensure_memory_dir,
    get_active_journal_file,
    count_lines,
    get_current_task,
    get_current_task_abs,
    set_current_task,
    clear_current_task,
    has_current_task,
    generate_task_date_prefix,
    get_spec_dir,
    get_package_path,
)

# New modules from upstream v0.4.0-beta.8
from .io import read_json, write_json  # noqa: E402
from .git import run_git  # noqa: E402
from .log import Colors, colored, log_info, log_success, log_warn, log_error  # noqa: E402
from .types import TaskData, TaskInfo, AgentRecord  # noqa: E402
from .tasks import load_task, iter_active_tasks, get_all_statuses, children_progress  # noqa: E402
from .config import (  # noqa: E402
    get_packages,
    get_default_package,
    is_monorepo,
    validate_package,
    resolve_package,
    get_spec_scope,
    get_features,
    get_hooks,
)

__all__ = [
    "configure_encoding",
    # paths
    "DIR_WORKFLOW",
    "DIR_WORKSPACE",
    "DIR_TASKS",
    "DIR_ARCHIVE",
    "DIR_SPEC",
    "DIR_SCRIPTS",
    "DIR_MEMORY",
    "FILE_DEVELOPER",
    "FILE_CURRENT_TASK",
    "FILE_TASK_JSON",
    "FILE_JOURNAL_PREFIX",
    "FILE_DECISIONS",
    "FILE_KNOWN_ISSUES",
    "FILE_SCRATCHPAD",
    "FILE_LEARNINGS",
    "check_developer",
    "clear_current_task",
    "count_lines",
    "generate_task_date_prefix",
    "get_active_journal_file",
    "get_current_task",
    "get_current_task_abs",
    "get_developer",
    "get_repo_root",
    "get_tasks_dir",
    "get_workspace_dir",
    "get_memory_dir",
    "ensure_memory_dir",
    "has_current_task",
    "set_current_task",
    "get_spec_dir",
    "get_package_path",
    # io
    "read_json",
    "write_json",
    # git
    "run_git",
    # log
    "Colors",
    "colored",
    "log_info",
    "log_success",
    "log_warn",
    "log_error",
    # types
    "TaskData",
    "TaskInfo",
    "AgentRecord",
    # tasks
    "load_task",
    "iter_active_tasks",
    "get_all_statuses",
    "children_progress",
    # config (monorepo)
    "get_packages",
    "get_default_package",
    "is_monorepo",
    "validate_package",
    "resolve_package",
    "get_spec_scope",
    # config (local customization)
    "get_features",
    "get_hooks",
]
