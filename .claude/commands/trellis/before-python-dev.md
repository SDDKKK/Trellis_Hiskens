Read the package-scoped Python development guidelines before starting your development task.

Execute these steps:
1. Discover packages and their spec layers:
   - `uv run python ./.trellis/scripts/get_context.py --mode packages`
2. Identify the package you will modify. For Hiskens scientific work, Python guidance is package-scoped:
   - `.trellis/spec/<package>/python/index.md`
3. Read the relevant package-scoped spec index and follow its Pre-Development Checklist
4. Based on your task, read the relevant guideline files:
   - Data processing → `.trellis/spec/<package>/python/data-processing.md`
   - Code style → `.trellis/spec/<package>/python/code-style.md`
   - Docstring → `.trellis/spec/<package>/python/docstring.md`
   - Quality → `.trellis/spec/<package>/python/quality-guidelines.md`
5. If the task crosses the Python↔MATLAB boundary, also read `.trellis/spec/<package>/matlab/index.md`
6. Always read `.trellis/spec/guides/index.md`
7. Understand the coding standards and patterns you need to follow, then proceed with your development plan

In single-repo projects, replace `.trellis/spec/<package>/...` with `.trellis/spec/...`.

This step is **mandatory** before writing any Python code.
