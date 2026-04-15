Check if the code you just wrote follows the Python development guidelines.

Execute these steps:
1. Run `git status` to see modified files
2. Discover packages and their spec layers:
   - `uv run python ./.trellis/scripts/get_context.py --mode packages`
3. Read the relevant package-scoped spec index:
   - `.trellis/spec/<package>/python/index.md`
4. Based on what you changed, read the relevant guideline files:
   - Data processing changes → `.trellis/spec/<package>/python/data-processing.md`
   - Code style changes → `.trellis/spec/<package>/python/code-style.md`
   - Docstring changes → `.trellis/spec/<package>/python/docstring.md`
   - Any changes → `.trellis/spec/<package>/python/quality-guidelines.md`
5. If the change affects Python↔MATLAB interaction, also read `.trellis/spec/<package>/matlab/index.md`
6. Review your code against the guidelines
7. Report any violations and fix them if found

In single-repo projects, replace `.trellis/spec/<package>/...` with `.trellis/spec/...`.
