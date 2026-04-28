# Main Agent Thinking Framework

> Structured methodology for Think/Plan/Reflect phases in task development.
> Referenced by `/trellis:start`, `/trellis:brainstorm`, `/trellis:finish-work`.

---

## Overview

This framework provides structured thinking patterns for the main agent during task lifecycle:

- **Think Phase**: Challenge assumptions, map existing code, decide scope
- **Plan Phase**: Walk through implementation timeline, anticipate failures, sketch architecture
- **Reflect Phase**: Review process, extract reusable patterns

**Core Principle**: Structure reduces blind spots. Spending 10 minutes thinking saves 1 hour of rework.

---

## Think Phase: Challenge & Reframe

**When**: At task creation, before implementation starts.
**Skip**: When continuing an existing task.

### 1a. Restate Understanding

Paraphrase the user's request to confirm shared understanding:

```
"I understand you want to do X. Let me confirm a few premises first..."
```

### 1b. Premise Challenge

Extract 2-3 implicit assumptions from the user's description and validate each:

| Premise Type | Example Question |
|--------------|------------------|
| **Need** | "Premise 1: Current solver is insufficient — what's the evidence?" |
| **Approach** | "Premise 2: Need a new module — can existing code be extended?" |
| **Priority** | "Premise 3: This is the top priority — are there more urgent tasks?" |

**User Response**: For each premise, user can:
- **Agree**: Premise confirmed
- **Disagree**: Premise rejected, adjust understanding
- **Adjust**: Refine the premise

**Record**: Add validated premises to `prd.md` under `## Premises`.

### 1c. What Already Exists (Code Mapping)

Coarse-grained mapping (research agent will refine later):

1. **Decompose**: What sub-problems does this requirement involve?
2. **Map**: For each sub-problem, does existing code partially cover it?
3. **Identify gaps**: What's truly new vs what's extension?

**Example**:
```
Requirement: Add rate limiting to API
Sub-problems:
  - Request counting → Existing: Redis client ✓
  - Time window logic → New
  - Response headers → Existing: middleware pattern ✓
```

### 1d. Scope Decision

Suggest a scope mode based on context:

| Context | Recommended Mode | Meaning |
|---------|------------------|---------|
| Brand new feature | EXPANSION | Add new capabilities freely |
| Enhance existing | SELECTIVE_EXPANSION | Extend carefully, preserve existing |
| Bug fix / refactor | HOLD_SCOPE | Fix only, no feature creep |
| Has deadline | REDUCTION | Minimal viable, defer nice-to-haves |

**Record**: Add scope mode to `prd.md` header.

---

## Plan Phase: Engineering Depth Check

**When**: During brainstorming, after requirements are clear but before final confirmation.
**Skip**: Trivial/Simple tasks. Required for Moderate/Complex tasks.

### 2a. Temporal Walk-through

Walk through the implementation timeline hour by hour:

| Time Window | Focus Question |
|-------------|----------------|
| **HOUR 1** (Foundation) | What does the implementer need to know first? |
| **HOUR 2-3** (Core) | What ambiguities will they encounter? |
| **HOUR 4-5** (Integration) | What will be surprising or unexpected? |
| **HOUR 6+** (Finish/Test) | What will they regret not planning earlier? |

**Output**: Add findings to `prd.md` under `## Temporal Notes`.

**Example**:
```
## Temporal Notes
- HOUR 1: Need Redis connection config, understand sliding window algorithm
- HOUR 2-3: Ambiguity: Should limit apply per endpoint or globally? (Clarify: globally)
- HOUR 4-5: Surprise: X-Forwarded-For can have multiple IPs (use first)
- HOUR 6+: Regret: Should have added monitoring hooks from start
```

### 2b. Error & Rescue Map

For each major operation, identify failure modes and rescue strategies:

| Operation | Failure Mode | Impact | Rescue Strategy |
|-----------|--------------|--------|-----------------|
| XML parsing | File not found | Missing feeder data | Skip + log warning |
| FMEA calculation | Singular matrix | NaN results | Fallback to zero |
| Solver iteration | No solution within budget | Empty result list | Return partial solution |

**Output**: Add table to `prd.md` under `## Error & Rescue Map`.

**Trigger**: Required for Moderate/Complex tasks involving I/O, computation, or external dependencies.

### 2c. Architecture Sketch

**Trigger**: Required when task involves 3+ modules or significant data flow.

Create a lightweight architecture snapshot:

1. **Data Flow Diagram** (ASCII):
   ```
   Input → Processing Steps → Output
   ```

2. **Dependency Map**:
   - What existing components does the new code depend on?
   - What new components are being added?

3. **Boundary Conditions**:
   - Empty input behavior
   - Large input behavior (performance)
   - Invalid input behavior (error handling)

**Output**: Add to `prd.md` under `## Architecture`.

**Example**:
```
## Architecture

Data Flow:
  HTTP Request → Rate Limiter Middleware → Redis (check count)
                                        → Handler (if allowed)
                                        → 429 Response (if exceeded)

Dependencies:
  - Existing: Redis client, middleware framework
  - New: RateLimiter class, sliding window logic

Boundary Conditions:
  - Empty IP (X-Forwarded-For missing): Use request.remote_addr
  - Redis unavailable: Fail open (allow request, log error)
  - Clock skew: Use server time, not client time
```

---

## Reflect Phase: Session Reflection

**When**: After code changes are complete, before commit.
**Skip**: Pure research/discussion sessions with no code changes.

### 3a. Process Review

Reflect on how the process went:

| Phase | Reflection Question |
|-------|---------------------|
| **Think** | Were the premise assumptions consistent with reality? |
| **Plan** | Was the Temporal prediction accurate? What was unexpected? |
| **Build** | How many implement agent iterations? What caused rework? |
| **Review** | What did review find that implement should have caught? |

### 3b. Pattern Extraction

Identify reusable patterns from this session:

| Discovery Type | Action |
|----------------|--------|
| New gotcha or pitfall | Add to `.trellis/memory/learnings.md` |
| Effective work pattern | Add to `.trellis/memory/learnings.md` |
| Convention worth standardizing | Remind to run `/trellis:update-spec` |
| Implement agent gap found by review | Note for future agent improvement |

### 3c. Output Format

Write a brief structured reflection (3-5 lines) to record in journal:

```
Session Reflection:
- What went right: [1-2 items]
- What to improve next time: [1-2 items]
- Key learning: [1 sentence]
```

**Not a checklist** — this is about "what we did well, what to change next time."

---

## Integration Points

| Command | Uses Which Phase |
|---------|------------------|
| `/trellis:start` | Think Phase (Step 1) |
| `/trellis:brainstorm` | Plan Phase (Step 7b) |
| `/trellis:finish-work` | Reflect Phase (Step 9) |

---

## Anti-Patterns

| Wrong | Right |
|-------|-------|
| Accept user request at face value | Challenge premises first |
| Plan without timeline walk-through | Use Temporal method for Moderate+ tasks |
| Commit without reflection | Extract patterns before closing |
| Apply all phases to trivial tasks | Skip appropriately based on complexity |

---

## Complexity-Based Application

| Task Complexity | Think | Plan | Reflect |
|-----------------|-------|------|---------|
| **Trivial** | Skip | Skip | Skip |
| **Simple** | 1b only (quick premise check) | Skip | Skip |
| **Moderate** | Full 1a-1d | 2a + 2b | Full 3a-3c |
| **Complex** | Full 1a-1d | Full 2a-2c | Full 3a-3c |

---

## Core Principle

> **Structure expands thinking, not restricts it.**
>
> These frameworks catch blind spots that free-form thinking misses.
> Use them as checklists, not as rigid procedures.
