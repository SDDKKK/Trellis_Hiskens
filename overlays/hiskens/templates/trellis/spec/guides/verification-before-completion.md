# Verification Before Completion

> Adapted from [Superpowers](https://github.com/obra/superpowers) for Trellis workflow.

## Iron Law

**NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE.**

Every claim that something "works" or "passes" must be backed by a command you ran
in the current message, with output you read and confirmed.

## Gate Function

BEFORE claiming any status (lint passes, tests pass, feature works):

1. **IDENTIFY** -- What command proves this claim?
2. **RUN** -- Execute the FULL command right now (not from memory)
3. **READ** -- Read the complete output, check exit code
4. **VERIFY** -- Does the output actually confirm the claim?
5. **ONLY THEN** -- Make the claim, citing the output

## Trellis-Specific Verification Commands

| Claim | Required Command |
|-------|-----------------|
| Lint passes | `rtk ruff check .` |
| Format passes | `rtk ruff format --check .` |
| Tests pass | `rtk pytest tests/ -q` |
| No type errors | `mcp__ide__getDiagnostics` |
| Feature works | Run the actual feature and show output |

## Red Flags (Prohibited Patterns)

These phrases indicate a verification gap. Do NOT use them:

- "should pass now" / "should be fixed"
- "looks correct" / "appears to work"
- "based on the previous run..."
- "the tests passed earlier"
- "I believe this is correct"
- Expressing satisfaction or confidence before running verification
- Trusting a previous run's output instead of re-running
- Trusting another agent's success report without independent verification
- **Trusting a dispatcher's "failure" report without checking the filesystem** (see Gotcha: Dispatcher Truth below)
- **Testing a reader/parser with hand-crafted input that matches your mental model of the format** (see Pattern: Reader/Writer Format Alignment below)

## Correct Patterns

- "Running `rtk ruff check .` now... Output: `All checks passed.` Exit code 0."
- "Verified: `rtk pytest tests/test_x.py -q` shows 5 passed, 0 failed."
- "getDiagnostics returned 0 errors for `src/module.py`."

## When This Applies

- Before claiming implementation is complete (implement agent)
- Before claiming all checks pass (check agent)
- Before outputting completion markers
- Before marking a task as done (finish phase)
- After every fix -- re-run the failing command to confirm

## Integration with Trellis v0.5 Workflow

Trellis v0.5 verification combines command exit codes, `trellis-check`, and
explicit completion evidence. This guide applies to every phase: implementation,
checking, review, and finish.

## Framework Change Verification (L1-L4)

When modifying `~/.trellis/shared/` (scripts, hooks, agents, config), use this 4-layer check:

| Layer | What | Command | Catches |
|-------|------|---------|---------|
| **L1** | Compile | `py_compile` all .py files | Broken imports, syntax errors |
| **L2** | Runtime | Run core scripts, check output sections | Silent degradation, missing context |
| **L3** | Integration | Full task lifecycle create→init→start→finish→archive | Workflow regressions |
| **L4** | Cross-project | `trellis-link.py verify` all projects | Broken symlinks, stale copies |

```bash
# L1: All scripts compile (0 FAIL required)
for f in ~/.trellis/shared/.trellis/scripts/common/*.py \
         ~/.trellis/shared/.trellis/scripts/*.py \
                  ~/.trellis/shared/.claude/hooks/*.py; do
  python3 -m py_compile "$f" || echo "FAIL: $f"
done

# L2: get_context.py outputs 5 sections
OUTPUT=$(python3 .trellis/scripts/get_context.py 2>&1)
for s in "DEVELOPER" "GIT STATUS" "ACTIVE TASKS" "JOURNAL" "MEMORY"; do
  echo "$OUTPUT" | grep -q "$s" || echo "FAIL: $s missing"
done

# L3: Task lifecycle
TASK_DIR=$(python3 .trellis/scripts/task.py create 'verify-test' --slug vt 2>&1 | tail -1)
python3 .trellis/scripts/task.py init-context "$TASK_DIR" python
python3 .trellis/scripts/task.py start "$TASK_DIR"
python3 .trellis/scripts/task.py finish
python3 .trellis/scripts/task.py archive vt

# L4: Symlink integrity
python3 ~/.trellis/trellis-link.py verify /path/to/project
```

**When to use**: After any change to common/ modules, hooks, task.py, config.yaml, or agent definitions. L1 is mandatory for every change; L2-L4 scale with risk.

## Pattern: Reader/Writer Format Alignment (End-to-End Verification)

**Problem**: When fixing a parser/reader bug, it is tempting to test the fix with hand-crafted input that looks "obviously right". But if the reader and writer disagree on format (whitespace, separators, quoting, encoding), the reader will silently fail on real data while your synthetic test passes.

**Real incident** (2026-04-11, /meta-optimize install): `check_ready.sh` had a regex `"ts":"[^"]+"` to extract the timestamp from JSON records. The fix passed hand-crafted tests. But the writer (`log_event.sh`'s inline Python) used `json.dumps(record)` with **default separators** — producing `"ts": "..."` with a space after the colon. The strict regex never matched the real writer output, and `SINCE_LAST` stayed 0 forever. Caught only after the third cross-review round asked "what does the writer actually emit?"

**Rule**: When verifying a reader/parser fix, the test input must come from the **actual writer**, not from your fingers.

```bash
# Wrong — synthetic input matching the spec/template
echo '{"ts":"2026-04-11T10:00:00Z","event":"skill_invoke"}' | bash check_ready.sh
# Passes because it happens to match your mental model of the format

# Correct — drive the writer, then run the reader
export CLAUDE_PROJECT_DIR=$(pwd)
echo '{"hook_event_name":"PostToolUse","tool_name":"Skill","tool_input":{"skill":"x"}}' \
    | bash tools/meta_opt/log_event.sh
bash tools/meta_opt/check_ready.sh
# Exercises the real writer→reader pipeline end-to-end
```

**Applies to**: any pair where one component produces data and another consumes it — JSON logs (this case), CSV dumps, binary formats, MAT files (Python↔MATLAB), API request/response, hook payloads.

**Also**: when the reader has conditional branches (e.g. `if .last_optimize exists`), build a **branch-coverage regression matrix** up front — enumerate all `(conditional branch) × (input format) × (tool type)` intersections and exercise each one. A "passing" test with synthetic happy-path input is a false green.

## Gotcha: Dispatcher Truth — Agent Reports Are Not Ground Truth

> **Warning**: When a Trellis subagent (implement, check, review, finish) returns "failed", the **filesystem is the authoritative source**, not the agent's final report.

A subagent can complete all its tool calls successfully (files written, commands run, state mutated) but then hit an LLM provider error (429, 500, timeout) while generating its **summary text**. The dispatcher sees the summary call failed and reports "pipeline blocked". But the actual work has already landed on disk.

**Real incident** (2026-04-11, /meta-optimize install via Trellis `start.py`): the implement subagent completed all 29 tool calls including `Write` for `.claude/settings.json`, 3 scripts, 3 memory files, and `.gitignore` edits. Then its final-summary LLM call hit a CCR/GLM 429. The dispatcher retried twice on opus then sonnet, all 3 hit the same provider layer, and reported "Phase 1 failed — pipeline blocked". A manual `git status` revealed all 29 tool calls' outputs were present and correct. The "failure" was a summary-generation failure, not a work failure.

**When a subagent reports failure, run this sanity check before retrying**:

```bash
# 1. Is the intended file list on disk?
git status --short
ls -la <expected-created-paths>

# 2. Is the intended content correct?
grep -c <expected-marker> <created-file>  # or diff against a reference

# 3. Was the subagent's last tool call a Write/Edit/Bash?
tail -c 4000 <worktree>/.agent-log | grep -oE '"description":"[^"]*"' | tail -5
```

If the answers are "yes / yes / yes", the work is likely complete and the failure is cosmetic. Re-dispatching the same subagent will either (a) succeed with the same provider trouble waiting for it, or (b) double-apply the work and corrupt state (especially dangerous for merge operations). Prefer manual verification + manual completion over blind retry.

**Corollary**: track dispatcher retries carefully. Three consecutive retries of the same subagent hitting the same provider error is a strong signal to stop and inspect disk state rather than escalate.

## Gotcha: Tool Runner Exit Codes Can Reflect Cache Environment, Not Script Logic

> **Warning**: A non-zero exit from `python3 ./.trellis/scripts/task.py ...` is not automatically evidence that `task.py` itself failed.

In restricted or sandboxed environments, `uv` can try to use the default cache under `~/.cache/uv`. If that path is read-only, `uv` may surface an error even when the Python script already executed its own side effects correctly.

**Real failure pattern**:

- `python3 ./.trellis/scripts/task.py finish` returns `2`
- `.trellis/.current-task` is still cleared
- scratchpad/task cleanup already happened

That combination points to a `uv` runtime/cache problem, not a `cmd_finish()` contract failure.

**Verification rule**:

1. Isolate script semantics with direct Python:
   `python3 ./.trellis/scripts/task.py finish`
2. Verify the real workflow path with writable uv cache:
   `UV_CACHE_DIR=.cache/uv python3 ./.trellis/scripts/task.py finish`
3. Only file a lifecycle-script regression if the direct-Python path is wrong too.

## Core Principle

> Trust nothing. Verify everything. Show your evidence.
