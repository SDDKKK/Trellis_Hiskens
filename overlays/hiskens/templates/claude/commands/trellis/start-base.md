# Start Session

> **Base document** -- universal session initialization workflow. Project-specific extensions (if any) are loaded via `{project}-topo.md` files and appended after this content by the hook.

Initialize your AI development session and begin working on tasks.

---

## Operation Types

| Marker | Meaning | Executor |
|--------|---------|----------|
| `[AI]` | Bash scripts or Task calls executed by AI | You (AI) |
| `[USER]` | Slash commands executed by user | User |

---

## Initialization `[AI]`

### Step 1: Understand Development Workflow

First, read the workflow guide to understand the development process:

```bash
cat .trellis/workflow.md
```

**Follow the instructions in workflow.md** - it contains:
- Core principles (Read Before Write, Follow Standards, etc.)
- File system structure
- Development process
- Best practices

### Step 2: Get Current Context

```bash
python3 ./.trellis/scripts/get_context.py
```

This shows: developer identity, git status, current task (if any), active tasks, memory status, session freshness.

### Step 3: Read Guidelines Index

```bash
cat .trellis/spec/matlab/index.md    # MATLAB guidelines
cat .trellis/spec/python/index.md    # Python guidelines
cat .trellis/spec/guides/index.md    # Thinking guides
```

### Step 4: Report and Ask

Report what you learned and ask: "What would you like to work on?"

---

## Task Classification

When user describes a task, classify it:

| Type | Criteria | Workflow |
|------|----------|----------|
| **Question** | User asks about code, architecture, or how something works | Answer directly |
| **Trivial Fix** | Typo fix, comment update, single-line change, < 5 minutes | Direct Edit |
| **Development Task** | Any code change that: modifies logic, adds features, fixes bugs, touches multiple files | **Task Workflow** |
| **Complex Task** | Vague goal, unclear scope, multiple valid approaches, architectural decisions | **Brainstorm → Task Workflow** |

### Decision Rule

> **If in doubt, use Task Workflow.**
>
> Task Workflow ensures specs are injected to agents, resulting in higher quality code.
> The overhead is minimal, but the benefit is significant.

---

## Question / Trivial Fix

For questions or trivial fixes, work directly:

1. Answer question or make the fix
2. If code was changed, remind user to run `/trellis:finish-work`

---

## Complex Task — Brainstorm First

If the task is complex (vague requirements, multiple approaches, architectural decisions):

1. Use `/trellis:brainstorm` to discover and refine requirements
2. Brainstorm produces a validated PRD with clear acceptance criteria
3. Then proceed to Task Workflow below with the refined requirements

> **When in doubt**: If you'd need to ask 3+ clarifying questions, use brainstorm.

---

## Task Workflow (Development Tasks)

**Why this workflow?**
- Research Agent analyzes what specs are needed
- Specs are configured in jsonl files
- Implement Agent receives specs via Hook injection
- Check Agent verifies against specs
- Result: Code that follows project conventions automatically

### Step 1: Understand the Task `[AI]`

Before creating anything, understand what user wants:
- What is the goal?
- What type of development? (python / matlab / both)
- Any specific requirements or constraints?

If unclear, ask clarifying questions.

### Step 2: Research the Codebase `[AI]`

Call Research Agent to analyze:

```
Task(
  subagent_type: "research",
  prompt: "Analyze the codebase for this task:

  Task: <user's task description>
  Type: <python/matlab/both>

  Please find:
  1. Relevant spec files in .trellis/spec/
  2. Existing code patterns to follow (find 2-3 examples)
  3. Files that will likely need modification

  Output:
  ## Relevant Specs
  - <path>: <why it's relevant>

  ## Code Patterns Found
  - <pattern>: <example file path>

  ## Files to Modify
  - <path>: <what change>

  ## Suggested Task Name
  - <short-slug-name>",
  model: "opus"
)
```

### Step 3: Create Task Directory `[AI]`

Based on research results:

```bash
TASK_DIR=$(python3 ./.trellis/scripts/task.py create "<title from research>" --slug <suggested-slug>)
```

### Step 4: Configure Context `[AI]`

Initialize default context:

```bash
python3 ./.trellis/scripts/task.py init-context "$TASK_DIR" <type>
# type: python | matlab | both
```

Add specs found by Research Agent:

```bash
# For each relevant spec and code pattern:
python3 ./.trellis/scripts/task.py add-context "$TASK_DIR" implement "<path>" "<reason>"
python3 ./.trellis/scripts/task.py add-context "$TASK_DIR" check "<path>" "<reason>"
```

### Step 5: Write Requirements `[AI]`

Create `prd.md` in the task directory with:

```markdown
# <Task Title>

## Goal
<What we're trying to achieve>

## Requirements
- <Requirement 1>
- <Requirement 2>

## Acceptance Criteria
- [ ] <Criterion 1>
- [ ] <Criterion 2>

## Technical Notes
<Any technical decisions or constraints>
```

### Step 6: Activate Task `[AI]`

```bash
python3 ./.trellis/scripts/task.py start "$TASK_DIR"
```

This sets `.current-task` so hooks can inject context.

### Step 6b: Code-Spec Depth Check `[AI]`

Before implementing, check if this task touches infrastructure or cross-layer contracts:

- New or changed Python↔MATLAB contracts (data file formats, variable naming)?
- New config schemas or shared constants?
- Changes to data interchange files (.mat, .csv, .json, .h5)?

If yes → read relevant spec files in `.trellis/spec/` before proceeding.
If no → proceed directly to implementation.

### Step 7: Implement `[AI]`

Call Implement Agent (specs are auto-injected by hook):

```
Task(
  subagent_type: "implement",
  prompt: "Implement the task described in prd.md.

  Follow all specs that have been injected into your context.
  Run lint and typecheck before finishing.",
  model: "opus"
)
```

### Step 8: Check Quality `[AI]`

Call Check Agent for programmatic verification (ruff check/format):

```
Task(
  subagent_type: "check",
  prompt: "Check code standards (D3). Fix any ruff issues.
  Ensure lint and format pass.",
  model: "opus"
)
```

### Step 9: Semantic Review `[AI]`

Call Review Agent for semantic review (D1/D2/D4/D5):

```
Task(
  subagent_type: "review",
  prompt: "Review all code changes for scientific correctness,
  cross-layer consistency, performance, and data integrity.
  Fix any issues you find directly.",
  model: "opus"
)
```

### Step 10: Complete `[AI]`

1. Verify lint and typecheck pass
2. Report what was implemented
3. Remind user to:
   - Test the changes
   - Commit when ready
   - Run `/trellis:record-session` to record this session

---

## Continuing Existing Task

If `get_context.py` shows a current task:

1. Read the task's `prd.md` to understand the goal
2. Check `task.json` for current status and phase
3. If a stale session warning appears, review the scratchpad and git diff before continuing
4. Ask user: "Continue working on <task-name>?"

If yes, resume from the appropriate step (usually Step 7 or 8).

---

## Commands Reference

### User Commands `[USER]`

| Command | When to Use |
|---------|-------------|
| `/trellis:start` | Begin a session (this command) |
| `/trellis:brainstorm` | Discover requirements for complex tasks |
| `/trellis:parallel` | Complex tasks needing isolated worktree |
| `/trellis:finish-work` | Before committing changes |
| `/trellis:record-session` | After completing a task |

### AI Scripts `[AI]`

| Script | Purpose |
|--------|---------|
| `get_context.py` | Get session context |
| `task.py create` | Create task directory |
| `task.py init-context` | Initialize jsonl files |
| `task.py add-context` | Add spec to jsonl |
| `task.py start` | Set current task |
| `task.py finish` | Clear current task |
| `task.py archive` | Archive completed task |

### Sub Agents `[AI]`

| Agent | Purpose | Hook Injection |
|-------|---------|----------------|
| research | Analyze codebase | No (reads directly) |
| implement | Write code | Yes (implement.jsonl) |
| check | Code standards (D3) | Yes (check.jsonl) |
| review | Semantic review (D1/D2/D4/D5) | Yes (review.jsonl) |
| debug | Fix specific issues | Yes (debug.jsonl) |

---

## Key Principle

> **Specs are injected, not remembered.**
>
> The Task Workflow ensures agents receive relevant specs automatically.
> This is more reliable than hoping the AI "remembers" conventions.
