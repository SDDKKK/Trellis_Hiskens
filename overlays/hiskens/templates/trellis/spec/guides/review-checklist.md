# Review Checklist for Scientific Computing

> Structured two-pass review methodology adapted for Java/Python/MATLAB scientific computing projects.

## Overview

Review proceeds in two passes:

1. **Pass 1 (CRITICAL)** — Correctness-first. Focus on bugs that produce wrong results or data corruption.
2. **Pass 2 (INFORMATIONAL)** — Engineering quality. Focus on performance, maintainability, and spec compliance.

**Philosophy**: Pass 1 findings block merge. Pass 2 findings are advisory and can be deferred.

---

## Pass 1 — CRITICAL (Correctness-First)

### C1: Scientific Correctness

Issues that cause incorrect numerical results or violate domain specifications.

| Issue | Example | Impact |
|-------|---------|--------|
| **Floating-point comparison without epsilon** | `if (value == 0.0)` instead of `Math.abs(value) < 1e-9` | False negatives in convergence checks |
| **Matrix dimension mismatch** | `A (m×n) * B (p×q)` where n ≠ p | Runtime error or silent wrong result |
| **Physical unit inconsistency** | Mixing per-unit and absolute values without conversion | Wrong reliability indices (off by 100×) |
| **Formula diverging from spec** | Implementing SAIDI with wrong denominator | Results don't match standard definition |
| **Array index off-by-one** | Java 0-based → MATLAB 1-based without +1 | Accessing wrong element, boundary errors |
| **Division by zero in edge cases** | `totalLoad / customerCount` when customerCount=0 | NaN propagation, crash |

**Examples**:

```python
# BAD: Direct float comparison
if reliability_index == 0.0:
    return "perfect"

# GOOD: Epsilon tolerance
if abs(reliability_index) < 1e-9:
    return "perfect"
```

```java
// BAD: No dimension check
double[][] result = multiply(matrixA, matrixB);

// GOOD: Validate dimensions
if (matrixA[0].length != matrixB.length) {
    throw new IllegalArgumentException("Dimension mismatch");
}
```

```matlab
% BAD: Direct port from Python (0-based)
node = nodes(index);

% GOOD: Adjust for 1-based indexing
node = nodes(index + 1);
```

---

### C2: Data Integrity

Issues that cause data loss, corruption, or incorrect data handling.

| Issue | Example | Impact |
|-------|---------|--------|
| **SQLite NULL without COALESCE** | `SELECT switching_time FROM components WHERE id=?` | NULL propagates, calculations fail |
| **File parsing without validation** | Reading CSV without checking column count | Silent data corruption, wrong field mapping |
| **Type coercion at boundaries** | Java int → Python without range check | Overflow, negative values become huge |
| **Missing database index** | Query on `type` field without index | 100× slowdown on large tables |

**Examples**:

```sql
-- BAD: NULL propagates
SELECT AVG(switching_time) FROM components;

-- GOOD: Handle NULL explicitly
SELECT AVG(COALESCE(switching_time, 0.0)) FROM components;
```

```python
# BAD: No validation
data = pd.read_csv(path)
feeder_id = data.iloc[0, 2]

# GOOD: Validate structure
data = pd.read_csv(path)
if len(data.columns) < 3:
    raise ValueError(f"Expected ≥3 columns, got {len(data.columns)}")
feeder_id = data.iloc[0, 2]
```

---

### C3: Cross-Layer Consistency

Issues at language boundaries (Python↔MATLAB, Java↔Python).

| Issue | Example | Impact |
|-------|---------|--------|
| **Data format mismatch** | Python writes JSON, MATLAB expects .mat | Data not loaded, silent failure |
| **Naming convention divergence** | Java `busId`, Python `bus_id`, MATLAB `BusID` | Manual mapping required, error-prone |
| **Topology model semantic gap** | FMEACal: FN/TN = device; AutoRetrofit: FN/TN = CN | Wrong FMEA results, optimization fails |
| **Index convention mismatch** | Python 0-based array passed to MATLAB | Off-by-one errors throughout |

**Examples**:

```python
# BAD: Inconsistent with MATLAB consumer
data = {"busId": 123, "voltage": 10.0}
savemat("output.mat", data)

# GOOD: Match MATLAB naming
data = {"BusID": 123, "Voltage": 10.0}
savemat("output.mat", data)
```

```java
// BAD: Assumes Python uses same topology model
int fromNode = edge.getFromNode();  // FN = device ID

// GOOD: Document semantic difference
// NOTE: FMEACal FN = device ID, but Python expects CN (connection node)
int fromNode = edge.getFromNode();
int connectionNode = deviceToCN.get(fromNode);
```

---

## Pass 2 — INFORMATIONAL (Engineering Quality)

### I1: Performance

Opportunities for optimization. Not blocking unless severe (>10× slowdown).

| Issue | Example | Impact |
|-------|---------|--------|
| **N+1 query** | Loop with DB query per iteration | 1000× slower than batch query |
| **Repeated computation in loop** | Calculating `sqrt(x)` every iteration | Unnecessary CPU usage |
| **Missed vectorization** | Python loop over DataFrame rows | 100× slower than vectorized ops |
| **Unnecessary object creation** | `new ArrayList<>()` in hot path | GC pressure, allocation overhead |

**Examples**:

```python
# INFORMATIONAL: N+1 query
for bus_id in bus_ids:
    bus = session.query(Bus).filter_by(id=bus_id).first()

# BETTER: Batch query
buses = session.query(Bus).filter(Bus.id.in_(bus_ids)).all()
```

---

### I2: Spec Compliance

Violations of project coding standards.

| Issue | Tool | Severity |
|-------|------|----------|
| **Python: ruff errors** | `ruff check` | Fix required |
| **Python: format issues** | `ruff format --check` | Fix required |
| **MATLAB: checkcode L1-L3** | `checkcode` | Fix required |
| **Java: naming conventions** | Manual | Fix if public API |
| **Missing docstrings** | Manual | Fix for public functions |

---

### I3: Code Clarity

Readability issues. Advisory unless critical algorithm is undocumented.

| Issue | Example | When to flag |
|-------|---------|--------------|
| **Missing docstring** | Complex algorithm without explanation | Always flag for critical paths |
| **Complex branching** | Nested if/else >3 levels deep | Flag if logic is non-obvious |
| **Magic numbers** | `if (value > 0.85)` without context | Flag if threshold is tuned |

---

### I4: Enum Completeness

New enum values not handled everywhere. **Requires reading code OUTSIDE the diff.**

| Issue | Example | How to detect |
|-------|---------|---------------|
| **New MeasureType** | Added `EENS` but not in report generator | Search all `switch(measureType)` |
| **New DeviceType** | Added `TRANSFORMER_3W` but not in FMEA | Grep for `DeviceType` enum usage |
| **New config option** | Added `use_parallel` but not in CLI | Trace config object consumers |

**Process**:
1. Identify new enum value in diff
2. Search codebase for all consumers: `grep -r "MeasureType" --include="*.java"`
3. Check each switch/if chain for completeness
4. Flag if new value is missing

---

## Fix-First Heuristic

Classify each finding as AUTO-FIX or ASK.

### AUTO-FIX (Apply without asking)

- Dead code (unreachable, unused imports)
- Unused variables
- Magic numbers → named constants (if meaning is obvious)
- Formatting/lint issues (ruff, checkcode)
- Stale comments (contradicting code)
- Missing NULL handling in SQLite queries
- Trivial type coercion (int → long, float → double)

**Rule of thumb**: "Would a senior engineer apply this without discussion in code review?"

### ASK (Needs human judgment)

- Changes to scientific calculation logic
- Public interface modifications (API, function signatures)
- Removal of functionality
- Large fixes (>20 lines changed)
- Enum completeness across multiple files
- Anything changing numerical output
- Performance optimizations with trade-offs

---

## Scope Drift Detection

**Before starting the review**, check if implementation matches stated intent.

### Process

1. Read `prd.md` to understand stated requirements
2. Run `git diff --stat` to see changed files
3. Compare: Do the changes align with the PRD?

### Output

```
Scope Check: CLEAN
```

or

```
Scope Check: DRIFT DETECTED
- PRD says: "Add rate limiting to API"
- Diff shows: API changes + database schema migration + new caching layer
- Recommendation: Split caching into separate task
```

or

```
Scope Check: REQUIREMENTS MISSING
- PRD requirement: "Support CSV export"
- Diff: No CSV export code found
```

**Note**: This is INFORMATIONAL only. Does not block the review.

---

## Confidence Gate

Tag each finding with confidence level.

| Tag | Meaning | Action |
|-----|---------|--------|
| `[HIGH]` | Definite bug or violation | Always report |
| `[MEDIUM]` | Likely issue, needs verification | Report |
| `[LOW]` | Style suggestion, minor | Suppress, do not report |

**Examples**:

```
[HIGH] src/fmea/Calculator.java:45 — Division by zero when customerCount=0
[MEDIUM] src/data/Loader.py:120 — Missing NULL check, may fail on sparse data
[LOW] src/utils/Helper.java:30 — Variable name could be more descriptive
```

---

## Suppression List

**Do NOT flag these**:

1. **Reasonable redundancy** — Code duplication that aids readability (e.g., explicit error messages per case)
2. **"Add comment explaining why"** — Comments rot faster than code; prefer self-documenting code
3. **Pure style consistency** — Changes with no correctness impact (e.g., `if (x)` vs `if (x == true)`)
4. **Already fixed in diff** — Issue was introduced and fixed in the same PR
5. **MATLAB checkcode L4/L5** — Advisory warnings only (e.g., "Consider preallocating")
6. **Java unchecked cast** — In generic erasure scenarios where type is guaranteed by context
7. **Test code style** — Test readability > production style (e.g., long test names are OK)
8. **Empirically tuned thresholds** — Magic numbers that are evaluation thresholds (e.g., `if (score > 0.85)`)

---

## Output Format

```
Review: N findings (X critical, Y informational)
Scope Check: CLEAN

=== CRITICAL (Pass 1) ===

[AUTO-FIXED] src/fmea/Calculator.java:45 — Division by zero when customerCount=0
  Fixed: Added check `if (customerCount == 0) return 0.0;`

[ASK][HIGH] src/data/Loader.py:120 — Missing NULL handling in SQLite query
  Problem: `SELECT switching_time FROM components` returns NULL for some rows
  Recommended fix: Use COALESCE(switching_time, 0.0)

=== INFORMATIONAL (Pass 2) ===

[AUTO-FIXED] src/utils/Helper.java:30 — Unused import java.util.HashMap

[MEDIUM] src/processing/Pipeline.py:200 — N+1 query in loop (1000 iterations)
  Recommended: Batch query outside loop
```

---

## Integration with Agent Workflow

1. **Before review**: Run Scope Drift Detection
2. **Pass 1**: Review for C1/C2/C3, apply AUTO-FIX immediately
3. **Pass 2**: Review for I1/I2/I3/I4, apply AUTO-FIX immediately
4. **Report**: Output findings with confidence tags
5. **Verification**: Run `ruff check`, `ruff format --check`, `pytest` to confirm fixes

---

## Core Principle

> **Correctness first, quality second.**
>
> A slow correct program can be optimized. A fast wrong program is useless.
