# Debug Methodology for Scientific Computing

> Systematic five-phase debugging process adapted for Java/Python/MATLAB scientific computing.

## Iron Law

**NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST.**

### Why This Rule Exists

Fixing symptoms creates whack-a-mole debugging:
- Each symptom fix makes the next bug harder to find
- Root cause remains, manifesting in new ways
- Technical debt accumulates (band-aids on band-aids)
- Team loses confidence in codebase stability

**Example of symptom fixing**:
```
Bug: NullPointerException in report generator
Symptom fix: Add null check → bug moves to next line
Symptom fix: Add another null check → bug moves to calculation
Symptom fix: Return default value → wrong results, silent failure
Root cause: Database query returns NULL, should use COALESCE
```

---

## Phase 1: Root Cause Investigation

**Goal**: Understand what is actually wrong, not just what appears wrong.

### Step 1: Collect Symptoms

Gather all observable evidence:
- Error messages (full stack trace, not just first line)
- Reproduction steps (exact sequence, input data)
- Environment (OS, Java/Python/MATLAB version, data files)
- Frequency (always, intermittent, specific conditions)

### Step 2: Read Code

Trace the call chain from symptom to potential causes:
- Start at the error location
- Work backwards through the call stack
- Identify data flow: where does the bad value come from?
- Check assumptions: what preconditions are violated?

### Step 3: Check Recent Changes

```bash
git log --oneline -20 -- <affected-files>
git diff <commit-before-bug> <commit-after-bug> -- <affected-files>
```

Look for:
- Recent changes to affected code
- Related changes in dependencies
- Configuration changes
- Data format changes

### Step 4: Reproduce Deterministically

Can you trigger the bug on demand?
- **Yes**: Proceed to Phase 2
- **No**: Gather more evidence (logs, core dumps, user reports)

### Output

Write a specific, testable root cause hypothesis:

```
Root cause hypothesis:
The FMEA calculator divides by totalCustomers without checking for zero.
When a feeder has no customers (new construction), totalCustomers=0,
causing ArithmeticException.

Prediction: Adding a feeder with customerCount=0 will trigger the bug.
```

---

## Phase 2: Pattern Analysis

**Goal**: Match the bug to known patterns to accelerate diagnosis.

### Step 1: Check Known Issues

Read `.trellis/memory/known-issues.md` for similar problems.

### Step 2: Domain-Specific Pattern Table

| Pattern | Signature | Where to Look | Common Fix |
|---------|-----------|---------------|------------|
| **Floating-point precision** | Small numerical deviation, convergence failure | `assertEquals` without epsilon, `==` comparison | Use epsilon tolerance (1e-9) |
| **Array index out of bounds** | `ArrayIndexOutOfBoundsException`, off-by-one | 0-based ↔ 1-based conversion (Java/Python ↔ MATLAB) | Add/subtract 1 at boundary |
| **Topology inconsistency** | FMEA result is 0 or NaN | `line[][]` construction, digraph building | Check FN/TN semantic (device vs CN) |
| **SQLite lock** | "database is locked" error | Concurrent access, long transactions | Enable WAL mode, reduce transaction scope |
| **Encoding issue** | Garbled text, `???` characters | Chinese character handling, file I/O | Specify UTF-8 explicitly |
| **Null propagation** | `NullPointerException`, unexpected null | Optional values, missing DB records | Use `COALESCE` in SQL, `Optional` in Java |
| **FMEA calculation error** | Unexpected SAIDI/SAIFI values | Component parameters, switching time | Verify formula against standard, check units |
| **Matrix dimension mismatch** | Wrong result shape, runtime error | Matrix multiplication, array operations | Add dimension assertions |
| **Division by zero** | `ArithmeticException`, `Infinity`, `NaN` | Aggregation over empty set, edge cases | Check denominator before division |
| **File not found** | `FileNotFoundException`, silent failure | Path construction, relative vs absolute | Use `Path.resolve()`, log missing files |

### Step 3: Check Git History

Search for prior fixes in the same area:

```bash
git log --all --grep="<keyword>" --oneline
git log --all -- <file> | grep -i "fix\|bug"
```

Recurring bugs in the same area = architectural smell (consider refactoring).

---

## Phase 3: Hypothesis Testing (3-Strike Rule)

**Goal**: Verify the root cause hypothesis with evidence.

### Step 1: Make Hypothesis Testable

Each hypothesis must have a verifiable prediction:

```
Hypothesis: Division by zero when customerCount=0
Prediction: Adding log before division will show customerCount=0
Verification: Add `System.out.println("customerCount=" + customerCount);`
```

### Step 2: Test the Hypothesis

Add temporary instrumentation:
- Log statements at suspected root cause
- Assertions to catch violations
- Debugger breakpoints with conditional expressions

Run the reproduction case and observe.

### Step 3: Evaluate Result

- **Hypothesis confirmed**: Proceed to Phase 4
- **Hypothesis wrong**: Return to Phase 1, gather more evidence

**Do NOT guess.** Each hypothesis must be based on evidence.

### 3-Strike Rule

If 3 hypotheses fail, **STOP** and choose:

**A) Continue with new hypothesis** (must describe it clearly):
```
Strike 1: Thought it was division by zero → customerCount is never 0
Strike 2: Thought it was null switching time → all values present
Strike 3: Thought it was matrix dimension → dimensions match
New hypothesis: The issue is in the digraph construction, not calculation
```

**B) Escalate for human review**:
```
After 3 failed hypotheses, I cannot determine root cause.
Evidence collected: [list]
Hypotheses tested: [list]
Recommendation: Pair debug with domain expert
```

**C) Add logging instrumentation and wait**:
```
Bug is intermittent, cannot reproduce reliably.
Added instrumentation at 5 suspected locations.
Will analyze logs from next occurrence.
```

### Red Flags (Slow Down)

If you see these, you're likely on the wrong track:

- **"Quick fix for now"** — There is no "for now", only permanent fixes
- **Proposing fix before tracing data flow** — You're guessing, not debugging
- **Each fix reveals new problem elsewhere** — Wrong layer, not wrong code
- **"This should work"** — Should ≠ does; verify with evidence

---

## Phase 4: Implementation (Minimal Diff)

**Goal**: Fix the root cause with minimal code changes.

### Principles

1. **Fix root cause, not symptom**
2. **Fewest files changed**
3. **Fewest lines changed**
4. **Add regression test** (fails without fix, passes with fix)

### Blast Radius Check

If fix touches >5 files, flag it:

```
WARNING: Fix touches 7 files
Files: [list]
Reason: [why so many files need changes]
Recommendation: Review with team before applying
```

### Regression Test Template

```python
def test_fmea_with_zero_customers():
    """Regression test for division by zero bug.

    Bug: FMEA calculator crashed when feeder had no customers.
    Root cause: Division by totalCustomers without zero check.
    Fix: Return 0.0 when totalCustomers == 0.
    """
    feeder = Feeder(id=1, customerCount=0)
    result = calculate_fmea(feeder)
    assert result.saidi == 0.0  # Should not crash
```

---

## Phase 5: Verification & Report

**Goal**: Confirm the fix works and document the investigation.

### Step 1: Verify Fix

1. **Reproduce original bug** → Confirm it's fixed
2. **Run regression test** → Should pass
3. **Run full test suite** → No new failures

### Step 2: Structured Debug Report

```
DEBUG REPORT
════════════════════════════════════════
Symptom:
  NullPointerException in ReportGenerator.java:145
  when generating reliability report for Feeder #23

Root cause:
  SQLite query "SELECT switching_time FROM components"
  returns NULL for components without switching_time value.
  NULL propagates through calculation, causing NPE.

Fix:
  src/data/ComponentRepository.java:67
  Changed: SELECT switching_time FROM components
  To: SELECT COALESCE(switching_time, 0.0) FROM components

Evidence:
  - Added logging: confirmed NULL values in database
  - Regression test: test_component_with_null_switching_time() passes
  - Full test suite: 127 passed, 0 failed

Regression test:
  src/test/java/ComponentRepositoryTest.java:89
  test_component_with_null_switching_time()

Related:
  - Similar issue fixed in commit abc1234 (different table)
  - Added to known-issues.md: "SQLite NULL handling"

Status: DONE
════════════════════════════════════════
```

---

## Completion Status Protocol

Use these status codes in your final report:

| Status | Meaning | When to Use |
|--------|---------|-------------|
| `DONE` | Root cause found, fix applied, regression test written, all tests pass | Normal case |
| `DONE_WITH_CONCERNS` | Fixed but cannot fully verify | Intermittent bug, requires staging environment, depends on external system |
| `BLOCKED` | Root cause unclear after investigation | After 3-Strike Rule, escalated to human |
| `NEEDS_CONTEXT` | Missing information to proceed | Need access to production data, need domain expert input |

### Examples

```
Status: DONE
All verification steps passed. Regression test added.
```

```
Status: DONE_WITH_CONCERNS
Fix applied and tested locally. However, bug only occurs in production
with specific data files we don't have access to. Recommend monitoring
after deployment.
```

```
Status: BLOCKED
After 3 failed hypotheses and 4 hours of investigation, root cause
remains unclear. Recommend pairing with MATLAB expert to review
digraph construction logic.
```

---

## Integration with Agent Workflow

1. **Receive bug report** → Phase 1 (Investigation)
2. **Form hypothesis** → Phase 2 (Pattern Analysis)
3. **Test hypothesis** → Phase 3 (Hypothesis Testing)
4. **Apply fix** → Phase 4 (Implementation)
5. **Verify and report** → Phase 5 (Verification)

If stuck at any phase, apply 3-Strike Rule.

---

## Core Principle

> **Understand first, fix second.**
>
> A fix without understanding is just a guess. Guesses accumulate into unmaintainable code.
