# Python Quality Guidelines

## Required Checks

Run Python code with `uv`.

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest tests/ -q
```

Use the pytest command when the project has a test suite relevant to the change.

## Validation Rules

- New or edited `.py` files must pass `ruff`.
- Typing syntax must satisfy the project lint configuration.
- Prefer inline `uv run python -c "..."` for temporary validation instead of throwaway files.
- Keep verification commands specific to the files or workflow you changed.
