# Python Code Style

## Core Principle

精简高效、毫无冗余。Scientific computing code with simple architecture.

## Ruff Enforcement

All Python code must pass `ruff check`. Config in `pyproject.toml`:
- Rules: E, W, F, I, C, N, B, A, COM, T20
- Line length: 88
- Target: Python 3.9

```bash
uv run ruff check .
uv run ruff format --check .
```

## Typing Annotations

- Must strictly comply with ruff typing rules
- Use `from __future__ import annotations` for modern syntax when needed
- Prefer built-in generics: `list[str]` over `List[str]`

## Architecture

- No complex design patterns — this is scientific computing
- No deep try-except nesting (max 1 level unless absolutely necessary)
- Flat is better than nested
- Only make targeted changes for the requirement, never affect existing functionality

## Forbidden Patterns

```python
# BAD: deep try-except nesting
try:
    try:
        try:
            ...
        except:
            ...
    except:
        ...
except:
    ...

# BAD: over-engineering for scientific code
class AbstractBaseFactoryStrategyPattern:
    ...
```

## Examples

```python
# src/core/reliability.py — actual project style
def calculate_saidi(outage_data: pl.DataFrame, total_users: int) -> float:
    """
    计算 SAIDI 指标

    输入：
        outage_data: pl.DataFrame, 停电事件数据
        total_users: int, 总用户数

    输出：
        float: SAIDI 值（小时/户）
    """
    total_duration = outage_data["duration_hours"].sum()
    affected = outage_data["affected_users"].sum()
    return (total_duration * affected) / total_users
```
