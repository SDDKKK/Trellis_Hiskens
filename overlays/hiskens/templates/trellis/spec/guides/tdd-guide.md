# Test-Driven Development Guide (Trellis)

> Adapted from [Superpowers](https://github.com/obra/superpowers) for Python scientific computing.
> This guide is conditionally injected when `task.json` has `"tdd": true`.

## When TDD Applies

TDD works well for:
- Pure functions (data transformation, calculation logic)
- Algorithm modules (FMEA, reliability indices, failure rates)
- Data pipeline unit logic (polars transforms, aggregations)
- Utility functions (path handling, config parsing)

## When TDD Does NOT Apply (Skip It)

- MATLAB migration (numerical consistency is the priority, not TDD cycle)
- Configuration files and script entry points
- Visualization code (matplotlib/seaborn plots)
- One-off data exploration scripts

## Red-Green-Refactor Cycle

### 1. RED: Write a Failing Test

```bash
# Write test first
# test_calculator.py
def test_failure_rate_basic():
    result = calculate_failure_rate(hours=8760, failures=2)
    assert result == pytest.approx(2.283e-4, rel=1e-3)
```

Run it and confirm it fails for the right reason (not implemented, not syntax error):

```bash
uv run pytest tests/test_calculator.py -q
```

### 2. GREEN: Write Minimal Code to Pass

Write the smallest amount of production code that makes the test pass.
Do not add extra features, error handling, or optimizations yet.

```bash
uv run pytest tests/test_calculator.py -q
# Expected: 1 passed
```

### 3. REFACTOR: Clean Up While Green

Improve code structure while keeping all tests passing:

```bash
uv run pytest tests/test_calculator.py -q
# Must still pass after refactoring
```

### 4. Repeat

Move to the next behavior. Write a new failing test first.

## Iron Law

**Write the test before the production code.**

If you accidentally wrote production code first:
1. Delete the production code
2. Write the test
3. Watch it fail
4. Re-implement

## Test Quality Rules

- Test behavior, not implementation details
- Each test should test ONE thing
- Test names describe the behavior: `test_empty_input_returns_zero`
- Use `pytest.approx()` for floating point comparisons
- Use fixtures for shared test data, not copy-paste

## Scientific Computing Specifics

### Numerical Tolerance

```python
# Good: explicit tolerance
assert result == pytest.approx(expected, rel=1e-6)

# Bad: exact equality for floats
assert result == 0.123456789
```

### Edge Cases to Always Test

- Empty input (empty DataFrame, empty list)
- Single element input
- Known reference values (from MATLAB or published papers)
- Boundary values (zero, negative, very large)

### Reference Data Tests

For MATLAB migration, use known MATLAB outputs as test fixtures:

```python
@pytest.fixture
def matlab_reference():
    """Reference values from MATLAB ReliabilityIndexCal.m"""
    return {
        "bus_count": 42,
        "branch_count": 41,
        "saifi": pytest.approx(0.1234, rel=1e-4),
    }
```

## Integration with Trellis

- When `tdd: true` in task.json, implement agent receives this guide
- PRD should include a `## Test Plan` section listing behaviors to test
- Tests go in `tests/` following existing project conventions
- Run `uv run pytest tests/ -q` to verify all tests pass

## Core Principle

> Tests are specifications written in code. Write the spec first, then make it real.
