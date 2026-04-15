---
name: before-matlab-dev
description: "Read MATLAB development guidelines before coding"
---

Read the package-scoped MATLAB development guidelines before starting your development task.

Execute these steps:
1. Discover packages and their spec layers:
   - `uv run python ./.trellis/scripts/get_context.py --mode packages`
2. Identify the package you will modify. For Hiskens scientific work, MATLAB guidance is package-scoped:
   - `.trellis/spec/<package>/matlab/index.md`
3. Read the relevant package-scoped spec index and follow its Pre-Development Checklist
4. Based on your task, read the relevant guideline files:
   - Code style → `.trellis/spec/<package>/matlab/code-style.md`
   - Docstring → `.trellis/spec/<package>/matlab/docstring.md`
   - Quality → `.trellis/spec/<package>/matlab/quality-guidelines.md`
5. If the task crosses the MATLAB↔Python boundary, also read `.trellis/spec/<package>/python/index.md`
6. Always read `.trellis/spec/guides/index.md`
7. Understand the coding standards and patterns you need to follow, then proceed with your development plan

In single-repo projects, replace `.trellis/spec/<package>/...` with `.trellis/spec/...`.

This step is **mandatory** before writing any MATLAB code.
