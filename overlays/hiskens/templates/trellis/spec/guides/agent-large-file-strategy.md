# Agent Large File Strategy

> **When to use**: Generating or modifying files exceeding ~300 lines via implement/check agents

## Problem

When an agent attempts to Write a large file (>300 lines), the `content` parameter may be truncated or dropped due to output token limits, causing `InputValidationError: The required parameter 'content' is missing`. The agent then retries the same Write call repeatedly, entering an infinite loop.

## Root Cause

Each agent turn has a maximum output token budget. When file content exceeds this budget, the model cannot produce the complete `content` parameter in a single tool call.

## Strategies

### Strategy 1: Segmented Writing Inside Agent (Recommended)

The agent itself can use Write + Edit to build the file incrementally. This requires explicit instruction in the agent prompt:

```
Prompt addition:
"This file is expected to be large (~500+ lines).
 Do NOT attempt to Write the entire file at once.
 Instead: Write the skeleton first (imports, constants, class declaration, ~80 lines),
 then use Edit to append each method group (~50-100 lines per Edit call)."
```

The agent workflow becomes:
```
Write → skeleton (imports + constants + fields, ~80 lines)
Edit  → method group 1 (~80 lines)
Edit  → method group 2 (~80 lines)
...
Bash  → compile to verify
```

This works because Edit appends are small enough to fit within the output token budget. The key is that the agent must be told upfront to use this pattern — without explicit instruction, it will default to a single Write call.

### Strategy 2: Segmented Trellis Workflow

Split the file across multiple sequential agent calls from the main session:

```
Agent 1: Write skeleton + first half of methods
Agent 2: Edit to append remaining methods (resume or new agent with "continue from where agent 1 left off")
```

Use this when Strategy 1 fails or the file exceeds ~800 lines.

### Strategy 3: Main Session Manual Segmentation

The orchestrator (main session) writes the file directly using Write + Edit, bypassing agents entirely. Most control, but loses agent benefits (spec injection, autonomous decision-making).

### Strategy 4: Preventive Design

Design the PRD to split large classes into multiple smaller files (<200 lines each), so agents can handle each file naturally.

## Decision Table

| Estimated Size | Strategy |
|---------------|----------|
| <200 lines | Agent direct Write |
| 200-500 lines | Strategy 1: instruct agent to use Write + Edit |
| 500-800 lines | Strategy 1 with detailed method grouping in prompt |
| >800 lines | Strategy 2 (segmented workflow) or Strategy 4 (split files) |

## Prompt Template for Strategy 1

```
"Implement {filename} (~{N} lines expected).

IMPORTANT: Do NOT Write the entire file in one call — it will fail.
Use this approach:
1. Write: file skeleton (package, imports, constants, class declaration, fields) — ~80 lines
2. Edit: append methods in groups of 50-100 lines each
3. Bash: compile after all edits to verify

Method groups to implement in order:
- Group 1: {methodA}, {methodB} (~80 lines)
- Group 2: {methodC}, {methodD} (~100 lines)
..."
```

## Case Study

`CimXmlReader.java` (664 lines): implement agent attempted full-file Write 6+ times, each failing with missing `content` parameter. Resolved by stopping the agent and using main-session segmented writing (1 Write + 11 Edits). In hindsight, Strategy 1 (instructing the agent to segment) would have avoided the manual intervention.
