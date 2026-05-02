# Python Directory Structure

## Default Layout

Prefer a flat scientific-computing layout over deep abstractions.

- `src/`: importable Python modules
- `scripts/`: thin entry scripts
- `tests/`: pytest coverage when the project has tests
- `data/` or domain-specific input folders: external data, not Python code

## Rules

- Keep computational logic in modules, not in CLI wrappers.
- Avoid spreading one algorithm across too many tiny files.
- Group files by scientific domain or pipeline stage, not by abstract layers.
- Do not create framework-style folders unless the project already uses them.
