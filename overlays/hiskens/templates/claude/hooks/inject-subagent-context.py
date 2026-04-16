#!/usr/bin/env python3
"""
Multi-Agent Pipeline Context Injection Hook

Core Design Philosophy:
- Dispatch becomes a pure dispatcher, only responsible for "calling subagents"
- Hook is responsible for injecting all context, subagent works autonomously with complete info
- Each agent has a dedicated jsonl file defining its context
- No resume needed, no segmentation, behavior controlled by code not prompt

Trigger: PreToolUse (before Task tool call)

Context Source: .trellis/.current-task points to task directory
- implement.jsonl - Implement agent dedicated context
- check.jsonl     - Check agent dedicated context
- debug.jsonl     - Debug agent dedicated context
- research.jsonl  - Research agent dedicated context (optional, usually not needed)
- cr.jsonl        - Code review dedicated context
- prd.md          - Requirements document
- info.md         - Technical design
- codex-review-output.txt - Code Review results
"""

from __future__ import annotations

import json
import os
import sys
import warnings
from pathlib import Path

# Suppress Python warnings that could corrupt JSON stdout
warnings.filterwarnings("ignore")

# Windows UTF-8 stdout fix (prevents UnicodeEncodeError with CJK characters)
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Add .trellis/scripts to path for importing common modules and nocturne_client
sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".trellis" / "scripts"))

try:
    from nocturne_client import NocturneClient
except ImportError:
    NocturneClient = None  # type: ignore[misc,assignment]

# Import shared context assembly module
from common.context_assembly import (  # noqa: E402
    AGENT_CHECK,
    AGENT_DEBUG,
    AGENT_IMPLEMENT,
    AGENT_PLAN,
    AGENT_RESEARCH,
    AGENT_REVIEW,
    AGENTS_ALL,
    AGENTS_REQUIRE_TASK,
    DIR_WORKFLOW,
    FILE_TASK_JSON,
    find_repo_root,
    get_check_context,
    get_current_task,
    get_debug_context,
    get_finish_context,
    get_implement_context,
    get_nocturne_hints,
    get_plan_context,
    get_research_context,
    get_review_context,
)

# =============================================================================
# Hook-Specific Constants (not in shared module)
# =============================================================================

# Agents that don't update phase (can be called at any time)
AGENTS_NO_PHASE_UPDATE = {"debug", "research", "plan"}

# Valid status transitions (Mod 5: State Machine)
VALID_STATUS_TRANSITIONS = {
    "planning": {"active", "rejected"},
    "active": {"review", "blocked"},
    "review": {"active", "completed"},
    "blocked": {"active"},
    "completed": set(),  # terminal
    "rejected": set(),  # terminal
}

# Map subagent type to expected task status
AGENT_TARGET_STATUS = {
    "implement": "active",
    "check": "review",
    "review": "review",
}

# =============================================================================
# Codex Agent Convention
# codex-{base} agents delegate to Codex CLI with same context as {base} agent.
# Adding a new codex variant only requires a new .claude/agents/codex-{base}.md
# file — no hook changes needed.
# =============================================================================

CODEX_PREFIX = "codex-"
CODEX_ALLOWED_BASES = (AGENT_IMPLEMENT, AGENT_CHECK, AGENT_DEBUG, AGENT_REVIEW)


def parse_codex_agent(subagent_type: str) -> str | None:
    """If subagent_type is codex-{base}, return base type. Otherwise None."""
    if not subagent_type.startswith(CODEX_PREFIX):
        return None
    base = subagent_type[len(CODEX_PREFIX) :]
    if base not in CODEX_ALLOWED_BASES:
        return None
    return base


def _load_features(repo_root: str) -> dict[str, bool]:
    """Load feature flags from .trellis/config.yaml.

    Used by hooks which cannot import from common.config (different sys.path).
    Returns empty dict on any error (graceful degradation).
    """
    config_path = os.path.join(repo_root, DIR_WORKFLOW, "config.yaml")
    if not os.path.isfile(config_path):
        return {}
    try:
        with open(config_path, encoding="utf-8") as f:
            content = f.read()
        # Minimal YAML parsing for flat key: value pairs
        features: dict[str, bool] = {}
        in_features = False
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("features"):
                in_features = True
                continue
            if in_features:
                if line and line[0] in (" ", "\t") and ":" in stripped:
                    key, _, val = stripped.partition(":")
                    key = key.strip()
                    val = val.strip()
                    if val.lower() in ("true", "yes", "1"):
                        features[key] = True
                    elif val.lower() in ("false", "no", "0", "", "[]"):
                        features[key] = False
                    else:
                        features[key] = bool(val)
                elif line and line[0] not in (" ", "\t"):
                    break
        return features
    except (OSError, UnicodeDecodeError):
        return {}


def get_ccr_model_tag(repo_root: str, subagent_type: str) -> str:
    """Read agent-models.json and return CCR tag prefix if configured.
    Only injects when CCR proxy is active (ANTHROPIC_BASE_URL points to localhost)
    and ccr_routing feature is enabled in config.yaml.
    """
    features = _load_features(repo_root)
    if not features.get("ccr_routing", False):
        return ""
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "")
    if "127.0.0.1" not in base_url and "localhost" not in base_url:
        return ""
    config_path = os.path.join(repo_root, DIR_WORKFLOW, "config", "agent-models.json")
    if not os.path.isfile(config_path):
        return ""
    try:
        with open(config_path, encoding="utf-8") as f:
            mapping = json.load(f)
        model = mapping.get(subagent_type, "")
        if model:
            return f"<CCR-SUBAGENT-MODEL>{model}</CCR-SUBAGENT-MODEL>\n"
    except (json.JSONDecodeError, OSError):
        pass
    return ""


def _append_audit_trail(
    repo_root: str, task_dir: str, agent_type: str, phase: int
) -> None:
    """Append audit trail entry when a subagent is dispatched.

    Never raises — audit failure must never block subagent dispatch.
    """
    from datetime import datetime, timezone

    audit_file = os.path.join(repo_root, task_dir, "audit.jsonl")
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "phase": phase,
        "agent": agent_type,
        "event": "dispatch",
    }
    try:
        with open(audit_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def update_current_phase(repo_root: str, task_dir: str, subagent_type: str) -> None:
    """
    Update current_phase in task.json based on subagent_type.

    This ensures phase tracking is always accurate, regardless of whether
    dispatch agent remembers to update it.

    Logic:
    - Read next_action array from task.json
    - Find the next phase whose action matches subagent_type
    - Only move forward, never backward
    - Some agents (debug, research) don't update phase
    """
    if subagent_type in AGENTS_NO_PHASE_UPDATE:
        return

    task_json_path = os.path.join(repo_root, task_dir, FILE_TASK_JSON)
    if not os.path.exists(task_json_path):
        return

    try:
        with open(task_json_path, "r", encoding="utf-8") as f:
            task_data = json.load(f)

        current_phase = task_data.get("current_phase", 0)
        next_actions = task_data.get("next_action", [])

        # Map action names to subagent types
        # "implement" -> "implement", "check" -> "check", "finish" -> "check"
        # "codex-implement" -> "implement", etc. (codex-* delegates to base)
        action_to_agent = {
            "implement": "implement",
            "check": "check",
            "review": "review",
            "finish": "check",  # finish uses check agent
            "codex-implement": "implement",
            "codex-check": "check",
            "codex-debug": "debug",
            "codex-review": "review",
        }

        # Find the next phase that matches this subagent_type
        new_phase = None
        for action in next_actions:
            phase_num = action.get("phase", 0)
            action_name = action.get("action", "")
            expected_agent = action_to_agent.get(action_name)

            # Only consider phases after current_phase
            if phase_num > current_phase and expected_agent == subagent_type:
                new_phase = phase_num
                break

        if new_phase is not None:
            task_data["current_phase"] = new_phase

            with open(task_json_path, "w", encoding="utf-8") as f:
                json.dump(task_data, f, indent=2, ensure_ascii=False)
    except Exception:
        # Don't fail the hook if phase update fails
        pass


def validate_status_transition(
    repo_root: str, task_dir: str, subagent_type: str
) -> None:
    """
    Validate and update task status based on subagent type (Mod 5: State Machine).

    Warns on invalid transitions but does not block (gradual introduction).
    """
    if subagent_type not in AGENT_TARGET_STATUS:
        return

    task_json_path = os.path.join(repo_root, task_dir, FILE_TASK_JSON)
    if not os.path.exists(task_json_path):
        return

    try:
        with open(task_json_path, "r", encoding="utf-8") as f:
            task_data = json.load(f)

        current_status = task_data.get("status", "planning")
        target_status = AGENT_TARGET_STATUS[subagent_type]

        # Already at target status, no transition needed
        if current_status == target_status:
            return

        allowed = VALID_STATUS_TRANSITIONS.get(current_status, set())
        if target_status not in allowed:
            print(
                f"WARNING: Invalid status transition {current_status} → {target_status} "
                f"(triggered by {subagent_type} agent)",
                file=sys.stderr,
            )
            return

        # Valid transition: update status and append to history
        task_data["status"] = target_status

        # Append to status_history
        history = task_data.get("status_history", [])
        from datetime import datetime, timezone

        history.append(
            {
                "from": current_status,
                "to": target_status,
                "at": datetime.now(timezone.utc).isoformat(),
                "by": subagent_type,
            }
        )
        task_data["status_history"] = history

        with open(task_json_path, "w", encoding="utf-8") as f:
            json.dump(task_data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


# =============================================================================
# Prompt Builder Functions (Claude-specific, not in shared module)
# =============================================================================


def build_implement_prompt(
    original_prompt: str, context: str, nocturne_hints: str = ""
) -> str:
    """Build complete prompt for Implement"""
    nocturne_section = f"\n{nocturne_hints}\n" if nocturne_hints else ""
    return f"""# Implement Agent Task

You are the Implement Agent in the Multi-Agent Pipeline.

## Your Context

All the information you need has been prepared for you:

{context}
{nocturne_section}
---

## Your Task

{original_prompt}

---

## Workflow

1. **Understand specs** - All dev specs are injected above, understand them
2. **Understand requirements** - Read requirements document and technical design
3. **Implement feature** - Implement following specs and design
4. **Self-check** - Ensure code quality against check specs

## Important Constraints

- Do NOT execute git commit, only code modifications
- Follow all dev specs injected above
- Report list of modified/created files when done"""


def build_check_prompt(
    original_prompt: str, context: str, nocturne_hints: str = ""
) -> str:
    """Build complete prompt for Check"""
    nocturne_section = f"\n{nocturne_hints}\n" if nocturne_hints else ""
    return f"""# Check Agent Task

You are the Check Agent in the Multi-Agent Pipeline (code and cross-layer checker).

## Your Context

All check specs and dev specs you need:

{context}
{nocturne_section}
---

## Your Task

{original_prompt}

---

## Workflow

1. **Get changes** - Run `git diff --name-only` and `git diff` to get code changes
2. **Check against specs** - Check item by item against specs above
3. **Self-fix** - Fix issues directly, don't just report
4. **Run verification** - Run project's lint and typecheck commands

## Important Constraints

- Fix issues yourself, don't just report
- Must execute complete checklist in check specs
- Pay special attention to impact radius analysis (L1-L5)"""


def build_review_prompt(
    original_prompt: str, context: str, nocturne_hints: str = ""
) -> str:
    """Build complete prompt for Review"""
    nocturne_section = f"\n{nocturne_hints}\n" if nocturne_hints else ""
    return f"""# Review Agent Task

You are the Review Agent in the Multi-Agent Pipeline (semantic code reviewer).

## Your Context

All review specs you need:

{context}
{nocturne_section}
---

## Your Task

{original_prompt}

---

## Workflow

1. **Get changes** - Run `git diff --name-only` and `git diff` to get code changes
2. **Review 4 dimensions** - D1 Scientific, D2 Cross-Layer, D4 Performance, D5 Data Integrity
3. **Self-fix** - Fix issues directly, don't just report
4. **Output markers** - Output all 4 completion markers when verified

## Important Constraints

- Fix issues yourself, don't just report
- Output SCIENTIFIC_FINISH, CROSSLAYER_FINISH, PERFORMANCE_FINISH, DATAINTEGRITY_FINISH when done
- If a dimension is N/A, still output the marker with a note"""


def build_finish_prompt(original_prompt: str, context: str) -> str:
    """Build complete prompt for Finish (final check before PR)"""
    return f"""# Finish Agent Task

You are performing the final check before creating a PR.

## Your Context

Finish checklist and requirements:

{context}

---

## Your Task

{original_prompt}

---

## Workflow

1. **Review changes** - Run `git diff --name-only` to see all changed files
2. **Verify requirements** - Check each requirement in prd.md is implemented
3. **Spec sync** - Analyze whether changes introduce new patterns, contracts, or conventions
   - If new pattern/convention found: read target spec file -> update it -> update index.md
   - If infra/cross-layer change: follow the 7-section mandatory template from update-spec.md
   - If pure code fix with no new patterns: skip this step
4. **Run final checks** - Execute finish-work.md checklist
5. **Confirm ready** - Ensure code is ready for PR

## Important Constraints

- You MAY update spec files when gaps are detected (use update-spec.md as guide)
- MUST read the target file BEFORE editing (avoid duplicating existing content)
- Do NOT update specs for trivial changes (typos, formatting, obvious fixes)
- If critical CODE issues found, report them clearly (fix specs, not code)
- Verify all acceptance criteria in prd.md are met"""


def build_debug_prompt(
    original_prompt: str, context: str, nocturne_hints: str = ""
) -> str:
    """Build complete prompt for Debug"""
    nocturne_section = f"\n{nocturne_hints}\n" if nocturne_hints else ""
    return f"""# Debug Agent Task

You are the Debug Agent in the Multi-Agent Pipeline (issue fixer).

## Your Context

Dev specs and Codex Review results:

{context}
{nocturne_section}
---

## Your Task

{original_prompt}

---

## Workflow

1. **Understand issues** - Analyze issues pointed out in Codex Review
2. **Locate code** - Find positions that need fixing
3. **Fix against specs** - Fix issues following dev specs
4. **Verify fixes** - Run typecheck to ensure no new issues

## Important Constraints

- Do NOT execute git commit, only code modifications
- Run typecheck after each fix to verify
- Report which issues were fixed and which files were modified"""


def build_research_prompt(original_prompt: str, context: str) -> str:
    """Build complete prompt for Research"""
    return f"""# Research Agent Task

You are the Research Agent in the Multi-Agent Pipeline (search researcher).

## Core Principle

**You do one thing: find and explain information.**

You are a documenter, not a reviewer.

## Project Info

{context}

---

## Your Task

{original_prompt}

---

## Workflow

1. **Understand query** - Determine search type (internal/external) and scope
2. **Plan search** - List search steps for complex queries
3. **Execute search** - Execute multiple independent searches in parallel
4. **Organize results** - Output structured report

## Search Tools (Three-Layer External Search)

| Tool | Purpose | Layer | Fallback if Unavailable |
|------|---------|-------|------------------------|
| Glob | Search by filename pattern | Local | — |
| Grep | Search by content (exact match) | Local | — |
| Read | Read file content | Local | — |
| mcp__morph-mcp__warpgrep_codebase_search | Broad semantic code search (multi-turn parallel) | Local | mcp__augment-context-engine__codebase-retrieval |
| mcp__augment-context-engine__codebase-retrieval | Deep semantic code understanding | Local | Grep + Read (manual) |
| mcp__context7__resolve-library-id | Resolve library name to Context7 ID | 0 | mcp__grok-search__web_search |
| mcp__context7__query-docs | Query library documentation and examples | 0 | mcp__grok-search__web_search |
| mcp__grok-search__web_search | Quick answer, platform-targeted web search, multi-source discovery | 1-2 | Bash("python3 .trellis/scripts/search/web_search.py '<query>'") |
| mcp__grok-search__get_sources | Inspect cached source list for citation verification | 1-2 | Use URLs embedded in search response |
| Bash("python3 .trellis/scripts/search/web_fetch.py '<url>'") | Fetch full webpage content as Markdown | 2 | (no equivalent - try all tiers) |
| Bash("python3 ~/.claude/skills/with-codex/scripts/codex_bridge.py ...") | Cross-model analysis (slow, 300s timeout) | Codex | Own analysis (skip Codex) |

Escalation: Layer 0 → 1 → 2 → 3. Start at lowest sufficient layer.
Tool Selection: Exact identifier → Grep. Broad semantic → warpgrep. Deep understanding → codebase-retrieval.

## Strict Boundaries

**Only allowed**: Describe what exists, where it is, how it works

**Forbidden** (unless explicitly asked):
- Suggest improvements
- Criticize implementation
- Recommend refactoring
- Modify any files

## Report Format

Provide structured search results including:
- List of files found (with paths)
- Code pattern analysis (if applicable)
- Related spec documents
- External references (if any)"""


def build_plan_prompt(original_prompt: str, context: str) -> str:
    """Build complete prompt for Plan Agent."""
    return f"""# Plan Agent Task

You are the Plan Agent in the Multi-Agent Pipeline (requirement evaluator & task configurator).

## Project Info

{context}

---

## Your Task

{original_prompt}

---

## Workflow

1. **Evaluate requirement** - Check if the requirement is clear, specific, and feasible
2. **Reject or accept** - Reject if vague, too large, or harmful; accept if actionable
3. **Research codebase** - Call research agent to find relevant specs and patterns
4. **Configure task** - Create jsonl files, prd.md, and set metadata
5. **Validate** - Ensure all referenced files exist

## Important Constraints

- You have the power to REJECT unclear requirements
- Do NOT execute git commit
- Always call research agent before configuring context
- Validate all file paths in jsonl entries"""


# =============================================================================
# Codex context getter mapping (base_type → getter function)
# =============================================================================

CODEX_CONTEXT_GETTERS: dict[str, object] = {}  # populated after function defs


def _init_codex_context_getters() -> None:
    """Populate CODEX_CONTEXT_GETTERS after all getter functions are defined."""
    CODEX_CONTEXT_GETTERS.update(
        {
            AGENT_IMPLEMENT: get_implement_context,
            AGENT_CHECK: get_check_context,
            AGENT_DEBUG: get_debug_context,
            AGENT_REVIEW: get_review_context,
        }
    )


_init_codex_context_getters()


def build_codex_prompt(
    base_type: str, original_prompt: str, context: str, nocturne_hints: str = ""
) -> str:
    """Build prompt for codex-{base} wrapper agents.

    Scheme C: Hook pre-assembles full context into temp file, wrapper passes
    it via --context-file. Codex receives complete context (specs + prd + memory).
    """
    base_constraints = {
        "implement": "Do NOT execute git commit. Only code modifications.",
        "check": "Fix issues found by linting/formatting. Run ruff check + format.",
        "debug": "Precise fixes only. Do not refactor unrelated code.",
        "review": "Review for correctness and consistency. Fix issues directly.",
    }
    base_mode = {
        "implement": "exec",
        "check": "exec",
        "debug": "exec",
        "review": "review",
    }

    constraint = base_constraints.get(base_type, "")
    mode = base_mode.get(base_type, "exec")

    # Assemble full context content (including Nocturne hints)
    ctx_content = context
    if nocturne_hints:
        ctx_content += f"\n\n{nocturne_hints}"

    # Write to temp file with PID + timestamp for concurrency safety
    import time as _time

    ctx_path = f"/tmp/trellis-codex-ctx-{os.getpid()}-{int(_time.time())}.md"
    with open(ctx_path, "w", encoding="utf-8") as f:
        f.write(ctx_content)

    return f"""# Codex {base_type.title()} Agent Task

You are a Codex Wrapper Agent. Your job is to delegate the task to Codex CLI
via codex_bridge.py, then report the results.

## How It Works

1. Hook has pre-assembled full context (specs + prd + memory) into a temp file
2. Your prompt includes the --context-file path below
3. You call codex_bridge.py with that path — Codex receives complete context
4. You collect results and report back

## Context File Location

**{ctx_path}**

This file contains the complete assembled context. Do NOT modify it.

## Execution Steps

1. **Understand the task** from the context file and original request below
2. **Call codex_bridge.py** using Bash (note the --context-file):

```bash
python3 ~/.claude/skills/with-codex/scripts/codex_bridge.py \\
  --mode {mode} \\
  --cd "$(pwd)" \\
  --full-auto \\
  --context-file {ctx_path} \\
  --timeout 600 \\
  --PROMPT "<summarize the task from original request below>"
```

3. **Parse the JSON output** — check `success`, `agent_messages`, `partial`
4. **Verify file changes** — run `git diff --stat` to see what Codex modified
5. **Report results** using the format below
6. **Cleanup** — remove the temp context file

## Original Request

{original_prompt}

## Constraints

- {constraint}
- If Codex fails (success=false), report the error — do NOT retry automatically
- If Codex returns partial results (partial=true), report what was completed
- If codex_bridge.py is not found or Codex CLI is not installed, report the error clearly

## Cleanup (Required)

After Codex completes, remove the temp context file:

```bash
rm -f {ctx_path}
```

## Report Format

```markdown
## Codex {base_type.title()} Complete

### Codex Output Summary
<brief summary of agent_messages>

### Files Modified
- `path/to/file.py` - description

### Verification
- git diff stat: <output>

### Cleanup
- Context file removed: {ctx_path}

### Issues (if any)
- <any problems encountered>
```"""


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")

    if tool_name not in ("Task", "Agent"):
        sys.exit(0)

    tool_input = input_data.get("tool_input", {})
    subagent_type = tool_input.get("subagent_type", "")
    original_prompt = tool_input.get("prompt", "")
    cwd = input_data.get("cwd", os.getcwd())

    # Check for codex-* prefix first
    codex_base = parse_codex_agent(subagent_type)

    # Only handle known subagent types or codex-* agents
    if subagent_type not in AGENTS_ALL and codex_base is None:
        sys.exit(0)

    # Find repo root
    repo_root = find_repo_root(cwd)
    if not repo_root:
        sys.exit(0)

    # Get current task directory (research/plan don't require it)
    task_dir = get_current_task(repo_root)

    # Determine effective agent type for task/phase/status checks
    effective_type = codex_base or subagent_type

    # implement/check/debug need task directory (codex-* inherits from base)
    if effective_type in AGENTS_REQUIRE_TASK:
        if not task_dir or not os.path.exists(os.path.join(repo_root, task_dir)):
            # No task dir — still inject CCR model tag if configured, then exit
            ccr_tag = get_ccr_model_tag(repo_root, subagent_type)
            if ccr_tag:
                output = {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "allow",
                        "updatedInput": {
                            **tool_input,
                            "prompt": ccr_tag + original_prompt,
                        },
                    }
                }
                print(json.dumps(output, ensure_ascii=False))
            sys.exit(0)
        # Update current_phase in task.json (system-level enforcement)
        update_current_phase(repo_root, task_dir, effective_type)

        # Validate and update status (Mod 5: State Machine)
        validate_status_transition(repo_root, task_dir, effective_type)

    # --- Codex agent path: use base agent's context + codex prompt builder ---
    if codex_base is not None:
        assert task_dir is not None  # codex agents always require task
        getter = CODEX_CONTEXT_GETTERS.get(codex_base)
        if getter is None:
            sys.exit(0)
        context = getter(repo_root, task_dir)
        nocturne_hints = get_nocturne_hints(codex_base)
        new_prompt = build_codex_prompt(
            codex_base, original_prompt, context, nocturne_hints
        )
    else:
        # --- Standard agent path (unchanged) ---

        # Check for [finish] marker in prompt (check agent with finish context)
        is_finish_phase = "[finish]" in original_prompt.lower()

        # Get Nocturne hints for relevant agents
        nocturne_hints = get_nocturne_hints(subagent_type)

        # Get context and build prompt based on subagent type
        if subagent_type == AGENT_IMPLEMENT:
            assert task_dir is not None  # validated above
            context = get_implement_context(repo_root, task_dir)
            new_prompt = build_implement_prompt(
                original_prompt, context, nocturne_hints
            )
        elif subagent_type == AGENT_CHECK:
            assert task_dir is not None  # validated above
            if is_finish_phase:
                context = get_finish_context(repo_root, task_dir)
                new_prompt = build_finish_prompt(original_prompt, context)
            else:
                context = get_check_context(repo_root, task_dir)
                new_prompt = build_check_prompt(
                    original_prompt, context, nocturne_hints
                )
        elif subagent_type == AGENT_DEBUG:
            assert task_dir is not None  # validated above
            context = get_debug_context(repo_root, task_dir)
            new_prompt = build_debug_prompt(original_prompt, context, nocturne_hints)
        elif subagent_type == AGENT_REVIEW:
            assert task_dir is not None  # validated above
            context = get_review_context(repo_root, task_dir)
            new_prompt = build_review_prompt(original_prompt, context, nocturne_hints)
        elif subagent_type == AGENT_RESEARCH:
            context = get_research_context(repo_root, task_dir)
            new_prompt = build_research_prompt(original_prompt, context)
        elif subagent_type == AGENT_PLAN:
            context = get_plan_context(repo_root, task_dir)
            new_prompt = build_plan_prompt(original_prompt, context)
        else:
            sys.exit(0)

    # Empty context check: for standard agents, exit early. For codex agents,
    # proceed with empty context (temp file already written; PRD edge case #2).
    if not context and codex_base is None:
        sys.exit(0)

    # Prepend CCR subagent model tag if configured
    ccr_tag = get_ccr_model_tag(repo_root, subagent_type)
    if ccr_tag:
        new_prompt = ccr_tag + new_prompt

    # Return updated input
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "updatedInput": {**tool_input, "prompt": new_prompt},
        }
    }

    # Append audit trail for agents that have a task directory
    if task_dir and effective_type in AGENTS_REQUIRE_TASK:
        try:
            task_json_path = os.path.join(repo_root, task_dir, FILE_TASK_JSON)
            phase = 0
            if os.path.exists(task_json_path):
                with open(task_json_path, "r", encoding="utf-8") as _f:
                    _td = json.load(_f)
                phase = _td.get("current_phase", 0)
        except Exception:
            phase = 0
        _append_audit_trail(repo_root, task_dir, effective_type, phase)

    print(json.dumps(output, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
