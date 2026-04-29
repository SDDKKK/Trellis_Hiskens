#!/usr/bin/env python3
"""
IntentGate - UserPromptSubmit Hook for Intent Detection

Detects user intent keywords and injects mode-specific hints to reduce
manual task classification friction.

Trigger: UserPromptSubmit (fires when user submits a prompt)

Guards:
- Strip code blocks before matching (prevent false positives)
- Skip if .trellis/.current-task exists with active status
- Skip non-user messages

Keyword mapping:
- fix/修复/bug/报错         → debug mode
- refactor/重构/优化代码     → refactor mode
- research/调研/分析/了解    → research mode
- parallel/并行/多agent      → parallel mode
- quick/简单/typo/一行       → trivial fix
"""

import json
import os
import re
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# =============================================================================
# Constants
# =============================================================================

DIR_WORKFLOW = ".trellis"
FILE_CURRENT_TASK = ".current-task"
FILE_TASK_JSON = "task.json"

# Code block pattern (``` ... ```)
CODE_BLOCK_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)

# Intent keyword patterns and their hints
# Each entry: (compiled_regex, intent_name, hint_message)
# NOTE: \b word boundary does not work with CJK characters in Python regex.
# Use \b only for ASCII keywords; Chinese keywords match without boundary.
INTENT_RULES: list[tuple[re.Pattern[str], str, str]] = [
    (
        re.compile(
            r"(?:\b(?:fix|bug|error)\b|修复|报错|错误)",
            re.IGNORECASE,
        ),
        "debug",
        (
            "\n\n[IntentGate: debug 模式检测] "
            "建议跳过 Research，直接进入 debug 路径。"
            "使用 Task(subagent_type='debug') 或手动定位并修复问题。"
        ),
    ),
    (
        re.compile(
            r"(?:\b(?:refactor)\b|重构|优化代码)",
            re.IGNORECASE,
        ),
        "refactor",
        (
            "\n\n[IntentGate: refactor 模式检测] "
            "进入重构路径，强调保持行为不变。"
            "先写测试确认现有行为，再进行结构调整。"
        ),
    ),
    (
        re.compile(
            r"(?:\b(?:research)\b|调研|分析|了解)",
            re.IGNORECASE,
        ),
        "research",
        (
            "\n\n[IntentGate: research 模式检测] "
            "纯研究模式，不修改代码。"
            "使用 Task(subagent_type='research') 进行代码/技术调研。"
        ),
    ),
    (
        re.compile(
            r"(?:\b(?:parallel)\b|并行|多agent)",
            re.IGNORECASE,
        ),
        "parallel",
        (
            "\n\n[IntentGate: parallel 模式检测] "
            "建议使用 /trellis:parallel 流程启动多 Agent 并行开发。"
        ),
    ),
    (
        re.compile(
            r"(?:\b(?:quick|typo)\b|简单|一行)",
            re.IGNORECASE,
        ),
        "trivial",
        "\n\n[IntentGate: trivial fix 检测] 简单修复，直接编辑即可，无需创建任务。",
    ),
]


def find_repo_root(start_path: str) -> str | None:
    """
    从 start_path 向上查找 git 仓库根目录

    输入：
        start_path: str, 起始路径

    输出：
        str | None: 仓库根目录路径，未找到返回 None
    """
    current = Path(start_path).resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return str(current)
        current = current.parent
    return None


def has_active_task(repo_root: str) -> bool:
    """
    检查是否存在活跃任务

    输入：
        repo_root: str, 仓库根目录

    输出：
        bool: 存在 active 状态任务返回 True
    """
    current_task_file = os.path.join(repo_root, DIR_WORKFLOW, FILE_CURRENT_TASK)
    if not os.path.exists(current_task_file):
        return False

    try:
        with open(current_task_file, "r", encoding="utf-8") as f:
            task_rel = f.read().strip()
        if not task_rel:
            return False

        task_json_path = os.path.join(repo_root, task_rel, FILE_TASK_JSON)
        if not os.path.exists(task_json_path):
            return False

        with open(task_json_path, "r", encoding="utf-8") as f:
            task_data = json.load(f)

        return task_data.get("status") == "active"
    except Exception:
        return False


def strip_code_blocks(text: str) -> str:
    """
    去除 markdown 代码块后返回纯文本

    输入：
        text: str, 原始文本

    输出：
        str: 去除代码块后的文本
    """
    return CODE_BLOCK_RE.sub("", text)


def detect_intent(text: str) -> tuple[str, str] | None:
    """
    检测文本中的意图关键词

    输入：
        text: str, 去除代码块后的用户消息

    输出：
        tuple[str, str] | None: (intent_name, hint_message)，未匹配返回 None
    """
    for pattern, intent_name, hint in INTENT_RULES:
        if pattern.search(text):
            return intent_name, hint
    return None


def main() -> None:
    """Process UserPromptSubmit event and inject intent hints if matched."""
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        print("{}")
        sys.exit(0)

    # Extract user prompt from message object
    # UserPromptSubmit schema: {"sessionId", "message": {"role": "user", "content": "..."}}
    message = input_data.get("message", {})
    if not isinstance(message, dict):
        print("{}")
        sys.exit(0)

    user_prompt = message.get("content", "")
    if not user_prompt:
        print("{}")
        sys.exit(0)

    # Find repo root
    cwd = input_data.get("cwd", os.getcwd())
    repo_root = find_repo_root(cwd)

    # Guard: skip if active task exists
    if repo_root and has_active_task(repo_root):
        print("{}")
        sys.exit(0)

    # Strip code blocks before matching
    clean_text = strip_code_blocks(user_prompt)

    # Detect intent
    result = detect_intent(clean_text)
    if result is None:
        print("{}")
        sys.exit(0)

    _intent_name, hint = result

    # Inject hint by appending to user message content
    # Output schema: {"hookSpecificOutput": {"updatedInput": {"message": ...}}}
    updated_message = {
        "role": message.get("role", "user"),
        "content": user_prompt + hint,
    }
    output = {
        "hookSpecificOutput": {
            "updatedInput": {
                "message": updated_message,
            }
        }
    }
    print(json.dumps(output, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
