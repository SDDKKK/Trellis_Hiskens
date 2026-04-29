# Python Quality Guidelines

## Required Checks

Run Python code with `uv`.

```bash
rtk ruff check .
rtk ruff format --check .
rtk pytest tests/ -q
```

Use the pytest command when the project has a test suite relevant to the change.

## Validation Rules

- New or edited `.py` files must pass `ruff`.
- Typing syntax must satisfy the project lint configuration.
- Prefer inline `python3 -c "..."` for temporary validation instead of throwaway files.
- Keep verification commands specific to the files or workflow you changed.
