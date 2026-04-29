---
name: check-matlab
description: "Verify MATLAB code follows project guidelines"
---

Check if the code you just wrote follows the MATLAB development guidelines.

Execute these steps:
1. Run `git status` to see modified files
2. Discover packages and their spec layers:
   - `uv run python ./.trellis/scripts/get_context.py --mode packages`
3. Read the relevant package-scoped spec index:
   - `.trellis/spec/<package>/matlab/index.md`
4. Based on what you changed, read the relevant guideline files:
   - Code style changes → `.trellis/spec/<package>/matlab/code-style.md`
   - Docstring changes → `.trellis/spec/<package>/matlab/docstring.md`
   - Any changes → `.trellis/spec/<package>/matlab/quality-guidelines.md`
5. If the change affects MATLAB↔Python interaction, also read `.trellis/spec/<package>/python/index.md`
6. Review your code against the guidelines
7. Report any violations and fix them if found

In single-repo projects, replace `.trellis/spec/<package>/...` with `.trellis/spec/...`.
