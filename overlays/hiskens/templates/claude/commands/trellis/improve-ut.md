# Improve Unit Tests

Analyze and improve unit test coverage for recent changes or specified modules.

**Timing**: After implementing a feature or fixing a bug, before commit

---

## Execution Flow

### Step 1: Identify Test Scope

Determine what needs testing:

```bash
# Option A: Recent changes (default)
git diff --name-only HEAD~1 -- '*.py'

# Option B: Specific module
# User specifies: "improve tests for scripts/停电事件分析/"
```

### Step 2: Analyze Current Coverage

```bash
# Run existing tests with coverage
uv run pytest --cov --cov-report=term-missing

# Or for specific module
uv run pytest tests/ --cov=scripts/ --cov-report=term-missing
```

### Step 3: Identify Gaps

For each changed file, check:

1. **Pure functions** — Do they have unit tests?
2. **Edge cases** — Are boundary conditions tested?
3. **Error paths** — Are exceptions tested?
4. **Data transformations** — Are input/output shapes verified?

### Step 4: Generate Tests

Follow conventions from `.trellis/spec/unit-test/conventions.md`:

```python
# File: tests/test_<module_name>.py

import pytest
from <module> import <function>


class TestFunctionName:
    """Tests for function_name."""

    def test_basic_case(self):
        """Normal input produces expected output."""
        result = function_name(valid_input)
        assert result == expected

    def test_edge_case(self):
        """Edge case: empty input."""
        result = function_name([])
        assert result == []

    def test_error_case(self):
        """Invalid input raises ValueError."""
        with pytest.raises(ValueError, match="expected message"):
            function_name(invalid_input)
```

### Step 5: Verify

```bash
# Run new tests
uv run pytest tests/test_<module>.py -v

# Check coverage improved
uv run pytest --cov --cov-report=term-missing
```

---

## Decision Flow: When to Write Tests

```
Changed a file?
  ├─ Pure function (no I/O, no side effects)
  │   └─ YES → Unit test required
  ├─ Data transformation (pandas/polars/numpy)
  │   └─ YES → Test with sample data
  ├─ Bug fix
  │   └─ YES → Regression test required
  ├─ Config/constant change only
  │   └─ NO → Skip
  └─ Script entry point (__main__)
      └─ MAYBE → Integration test if critical
```

---

## Anti-Patterns

| Anti-Pattern | Why It's Bad | Instead |
|-------------|-------------|---------|
| Testing implementation details | Breaks on refactor | Test behavior/output |
| Mocking everything | Tests prove nothing | Mock only external I/O |
| No assertion message | Hard to debug failures | Use `assert x == y, "context"` |
| Giant test functions | Hard to isolate failures | One concept per test |
| Copying production data into tests | Brittle, large fixtures | Use minimal synthetic data |

---

## Relationship to Other Commands

```
Development Flow:
  Implement → /trellis:improve-ut → /trellis:finish-work → commit
                    |
              Add/improve tests
```

- `/trellis:improve-ut` - Improve test coverage (this command)
- `/trellis:finish-work` - Pre-commit checklist (includes test check)
- `/trellis:check-python` - Verify code standards
