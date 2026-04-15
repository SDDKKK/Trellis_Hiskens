# Fork Upstream Sync Guide

> **Purpose**: Safely sync a long-lived fork (e.g., `Trellis_Hiskens`) with an upstream that has its own ongoing development, while preserving fork-specific customizations (overlays, hooks, hiskens features).

This guide captures the workflow battle-tested during the v0.4.0 sync. Use it whenever upstream releases a new version, or when you suspect overlay drift.

---

## When to Use

- [ ] Upstream Trellis just released a new version (beta, rc, or stable)
- [ ] Periodic maintenance check: how far has the fork drifted?
- [ ] You suspect a fork file is silently behind upstream (e.g., bug fixed upstream that we missed)
- [ ] User reports a bug that "works on upstream" but not on the fork
- [ ] Onboarding a new project to the fork ecosystem

If the answer to any is yes — read this guide before touching git.

---

## Three-Phase Workflow

```
Phase A: Safe Merge      → bring upstream into a sync branch
   ↓
Phase B: Drift Detection → find what to port (DUAL SCOPE!)
   ↓
Phase C: Surgical Port   → graft fixes preserving guardrails
```

**Never skip a phase. Never do them out of order.** Phase B is the one most likely to be done sloppily and is the one most likely to leave silent drift.

---

## Phase A: Safe Merge

### Steps

```bash
# 1. Fetch upstream — verify network actually delivers new refs
git fetch upstream --prune
# (If TLS errors or proxy issues, retry until "ok fetched (N new refs)")

# 2. Compare divergence to know the scope
git rev-list --left-right --count HEAD...upstream/main
# left = ours ahead, right = upstream ahead
# If "right" >> 0, you have real work to do.

# 3. Make a safety branch — NEVER merge directly on main
git checkout -b sync/upstream-<version>

# 4. Merge (NOT rebase) — preserves fork's big commits intact
git merge upstream/main --no-ff -m "merge: sync upstream <version> into <fork> fork

<longer description noting incoming feature highlights and notable
conflict areas>"
```

### Why merge, not rebase

Fork big commits like `feat: add hiskens overlay templates and loader` may touch hundreds of files and tens of thousands of lines. **Rebasing replays them onto each upstream commit one by one**, multiplying conflict surface and obliterating the hiskens commit history's narrative. **Merge concentrates conflict into one merge commit** that you resolve once.

### Conflict resolution principles

- **Conflicts in fork "side-additions"** (e.g., overlay loader injection points): keep BOTH fork additions AND upstream additions, just place them adjacent.
- **Upstream-pure new files** (e.g., new platform `templates/droid/**`): accept upstream verbatim.
- **Files where both sides modified the same lines** (rare): manual merge using research, not auto-tools.
- If git auto-merges with no conflict but the result needs a missing entry (e.g., a new `Record<AITool, OverlayTarget[]>` is missing the new platform key), **TypeScript or test failures will surface it**. Run `tsc --noEmit` and the test suite immediately after the merge commit.

### Verification after merge

```bash
# TypeScript
npx tsc --noEmit

# Tests
cd packages/cli && npm test 2>&1 | tail -20
# Expect: 624/624 (or whatever the current full count is)
```

If tests fail, check whether the failure is **environmental** (e.g., line endings — see Pitfall 3 below) before assuming the merge is bad.

---

## Phase B: Drift Detection (DUAL SCOPE!)

> **The single most important rule in this guide:** Always use BOTH narrow and broad scope. Using only one will leave silent drift.

### Narrow scope: "what changed in the merge window"

```bash
MERGE_BASE=$(git merge-base HEAD^1 HEAD^2)  # parents of merge commit
git diff --name-only $MERGE_BASE upstream/main
```

This gives the file delta of the N upstream commits you just absorbed. For each of those files, check if there's an overlay mirror at the same relative path:

```bash
while read f; do
  rel="${f#packages/cli/src/templates/}"
  overlay="overlays/<fork>/templates/$rel"
  if [ -f "$overlay" ]; then
    echo "MIRROR_HIT  $rel"
  fi
done < <(git diff --name-only $MERGE_BASE upstream/main)
```

The hits are **active drift candidates** — these need surgical port (Phase C).

### Broad scope: "what's the total divergence right now"

```bash
# For every overlay file, check how it compares to current upstream
find overlays/<fork>/templates -type f \( -name '*.py' -o -name '*.md' -o -name '*.js' -o -name '*.json' \) | while read overlay; do
  rel="${overlay#overlays/<fork>/templates/}"
  upstream="packages/cli/src/templates/$rel"
  [ -f "$upstream" ] || continue
  diff -q "$overlay" "$upstream" >/dev/null && continue
  delta=$(diff "$overlay" "$upstream" | grep -cE '^[<>]')
  ovly=$(wc -l < "$overlay")
  ups=$(wc -l < "$upstream")
  echo "DRIFT  $rel  (overlay=${ovly}L  upstream=${ups}L  diff-lines=$delta)"
done
```

This catches drift that the narrow scope misses, including:

- **Forks based on older upstream eras** — overlay was derived from `v0.4.0-beta.7` but upstream has gone through `beta.8`, `beta.9`, etc. between then and merge-base.
- **Cumulative tiny upstream changes** that fall outside the immediate merge window but still left the overlay behind.
- **Files the fork rewrote then never re-checked** (e.g., heavy customizations that may have absorbed a now-fixed upstream bug into themselves).

### Drift triage: 3-tier classification

For each drifted file, classify before acting:

| Tier | Symptom | Action |
|---|---|---|
| **🟢 Customization** | overlay ≫ upstream (many added lines) | KEEP — this is intentional fork work |
| **🟡 Attribution noise** | 1–10 line diff, often `"""Ported from upstream v0.4.0-beta.X."""` headers, blank lines, import order | KEEP — pure cosmetic, no functional drift |
| **🟠 Real missed sync** | overlay < upstream (fewer lines), OR overlay ≈ upstream with semantic delta | INVESTIGATE — likely needs port |

> **Don't trust the "drifted file count" metric alone.** A "52 drifted files" headline often decomposes to "3 real, 49 customization or noise" once you triage.

### When in doubt, spawn a research agent

For >10 ambiguous mid-tier files, delegate to a research subagent rather than reading them yourself. Give the research agent:

- The exact file list
- The fork's "philosophy" doc (must-keep features, must-not-port concepts)
- Instruction to classify each file as `keep | port-small-fix | port-major-rework | investigate-further`

The research agent's structured output becomes the input to Phase C.

---

## Phase C: Surgical Port

### Guardrails: write them DOWN before editing

For each file you're going to modify in Phase C, list the **must-preserve** customizations BEFORE opening the editor. Hiskens example for `claude/hooks/session-start.py`:

```
MUST KEEP:
- Plain print() to stdout (NOT JSON envelope) — hiskens hook protocol expects raw text
- get_nocturne_context() / get_memory_summary() / get_stale_session_warning()
- <thinking-framework> block injection
- Local _get_task_status replacement = get_stale_session_warning (do not add upstream's _get_task_status)

MUST PORT:
- _build_workflow_toc() helper from upstream (replaces full workflow.md injection)
- <ready> banner new wording
- Drop the inlined <instructions> block reading start.md
```

Without this list, the implementer (you or an agent) will silently destroy load-bearing fork features. **Write the list inside the task PRD or in a checklist comment in the implement agent prompt.**

### Patterns for porting

**Pattern 1: Mechanical insertion** (e.g., adding a new platform branch to an `if/elif` chain)
- Mirror upstream's structure exactly
- Hit ALL touch points, not just the obvious 5 (e.g., for cli_adapter Droid port, 13 touch points: type literal, config dir, command path, env, run, resume, name, factory validation, error msg, all-config-dirs tuple, detect_platform env tuple, detect_platform body, detect_platform docstring)
- Verification: `grep -c "<new_thing>"` should return a count matching upstream

**Pattern 2: Helper port** (e.g., `_build_workflow_toc` into hiskens session-start)
- Copy the helper function verbatim from upstream
- Replace the call site (1 line) — DO NOT touch surrounding orchestration
- Verify the rest of the function body is byte-identical to before

**Pattern 3: Full base rewrite** (e.g., `start.md` rewrite on upstream v0.4.0)
- Write the upstream file as the new base, in full
- Apply terminology renames (search/replace)
- Apply each graft from the must-keep list as a separate Edit
- Final verification: grep for keywords that MUST be present (e.g., `execute ALL steps below without stopping`) and keywords that MUST be absent (e.g., `frontend|backend|fullstack` if hiskens uses python+matlab)

### After every Phase C file edit

```bash
python3 -m py_compile <edited_file>     # for Python
# (no compile step for .md, just visual review)

cd packages/cli && npm test 2>&1 | tail -20     # tests stay green
```

---

## Common Pitfalls

### Pitfall 0: `trellis update` downstream false-positive conflicts

**Symptom**: `trellis update --overlay hiskens --dry-run` reports 20+ "Modified by you" files, but `git diff HEAD -- <file>` shows most are byte-identical to HEAD.

**Cause**: `.template-hashes.json` records hashes at install time. After a multi-round resync (e.g., Round 1 accepted upstream, Round 2 re-accepted after further overlay changes), the hash tracker becomes stale even though the working-tree file already matches the latest overlay version. The next dry-run sees "stored hash ≠ current overlay hash" and flags it.

**Measured rates**: Anhui Round 3: 20/23 = 87% false positive. Topo Phase 2: 2/12 = 17%. The difference: Anhui had already absorbed changes in Round 2; Topo was a fresh beta.10→0.4.0 jump.

**Rule**: After `--create-new` generates `.new` files, verify EACH against HEAD before making accept/reject decisions:

```bash
for f in $(find . -name '*.new' -not -path './.git/*'); do
  real="${f%.new}"
  git_hash=$(git ls-tree HEAD -- "$real" 2>/dev/null | awk '{print $3}')
  new_hash=$(git hash-object "$f")
  if [ "$git_hash" = "$new_hash" ]; then
    echo "FALSE-POSITIVE (rm .new): $real"
    rm "$f"
  else
    echo "REAL-DIFF (decide): $real"
  fi
done
```

### Pitfall 0b: `trellis update` hangs in scripted/agent contexts

**Symptom**: `node .../trellis.js update --overlay hiskens` hangs indefinitely when run by a Claude Code implement agent or in a background Bash command.

**Cause**: The update command prompts `"Proceed? (Y/n)"` on stdin. In non-interactive contexts, stdin is `/dev/null` or a pipe, so the prompt never resolves.

**Fix**: Always pipe `yes` into the command:

```bash
yes | node /path/to/trellis.js update --overlay hiskens --create-new > /tmp/update.log 2>&1
```

The `yes` command outputs `"y\n"` indefinitely, satisfying all prompts (the initial "Proceed?" and any per-file conflict prompts if `--create-new` is not used).

**Symptom**: "I greped for `--mode record` in `get_context.py` and found nothing, so the fork doesn't support it."

**Reality**: `get_context.py` may be a 15-line wrapper that imports `main` from `common/git_context.py`. The `--mode` argparse lives in the deeper module. **The flag IS supported.**

**Rule**: When verifying whether a feature exists, **follow the import chain to the leaf**. Don't stop at the entry point. Practical heuristic:

```bash
# WRONG
grep -n "mode" overlays/<fork>/templates/trellis/scripts/get_context.py

# RIGHT
# 1. Read the entry file
# 2. Note its imports
# 3. Recursively grep the imported modules
grep -rn "mode" overlays/<fork>/templates/trellis/scripts/common/
```

**Even better**: just *run the command* in a sandbox to verify. `python3 ./.trellis/scripts/get_context.py --mode record 2>&1; echo "exit=$?"` is a 2-second empirical test that beats any grep argument.

### Pitfall 2: Confusing overlay templates with installed templates

The fork repo has TWO different file trees that look similar but serve opposite purposes:

| Path | Purpose | When loaded |
|---|---|---|
| `overlays/<fork>/templates/<rel>` | **Source of truth shipped to downstream consumer projects** that opt into the overlay | Read by overlay loader at `trellis init` time of the consumer project |
| `.claude/commands/<rel>`, `.trellis/scripts/<rel>` | **Installed-into-this-repo copies** used by the publishing repo's own dev workflow | Read directly by Claude Code, scripts, hooks during local development |

**Practical consequence**: When you `/trellis:record-session` in the publisher repo, the skill loader reads `.claude/commands/trellis/record-session.md` — the installed UPSTREAM version, NOT the overlay edit you just made. Your overlay edit affects only DOWNSTREAM consumers.

This means:
- Editing `overlays/<fork>/templates/<x>` does NOT change the local skill behavior. To test the overlay, install it in a separate sandbox project.
- Conversely, `.template-hashes.json` in the publisher repo tracks the INSTALLED files, not overlay sources. Editing overlay files does not invalidate any hash.

### Pitfall 3: `core.autocrlf=true` × YAML frontmatter test assertions

**Symptom**: After fetching upstream and merging, tests fail with assertions like `expect(content.startsWith("---\n")).toBe(true)` returning false. Pre-existing tests for OTHER files pass.

**Cause**: Global `git config core.autocrlf=true` (default on Windows/WSL git installs) silently converts LF to CRLF on checkout for text files. Files with YAML frontmatter (`---\n...`) become `---\r\n...`, breaking assertions that compare against `---\n`. The blob in the repo is correct LF; only the working tree is wrong.

**Fix** (3 steps, all repo-local — do NOT touch global git config without permission):

```bash
# 1. Add .gitattributes enforcing LF in this repo
cat > .gitattributes <<'EOF'
* text=auto eol=lf
*.png binary
*.jpg binary
# (other binary types as needed)
EOF

# 2. Set autocrlf=false locally (does not affect global)
git config --local core.autocrlf false

# 3. Force re-checkout to refresh working tree to LF
git rm --cached -rq .
git reset --hard HEAD
```

After this, tests should pass. If `.gitattributes` already exists with `eol=lf`, only steps 2 and 3 are needed.

> **Why this is a fork sync gotcha**: Upstream may add new template files that depend on LF (e.g., new platform like Droid with YAML-frontmatter command files). Until you sync, you never have those files locally, so the bug is invisible. After sync, they appear and immediately break.

### Pitfall 4: Workflow file rewrites silently dropping behavioral directives

**Symptom**: After a fork rewrites `start.md` (or any other agent-facing workflow file) with reorderings or new steps, agents start pausing more often, asking for confirmation between steps, or otherwise behaving more cautiously than before.

**Cause**: Upstream workflow files often contain critical **behavioral directives** like:
> If yes: execute ALL steps below without stopping. Do NOT ask for additional confirmation between steps.

When the fork rewrites the file (e.g., to insert custom steps, change ordering, change terminology), it's easy to drop these directives by accident — they look like generic prose but they are load-bearing instructions to the agent.

**Rule**: When rewriting any workflow file (`start.md`, `brainstorm.md`, agent prompts), **before saving, search the upstream version for imperative sentences** like:
- `execute ALL steps`
- `Do NOT ask`
- `without stopping`
- `Skip directly to`
- `Wait for the user`

For each one, decide explicitly: **port verbatim** or **deliberately drop with reason logged**. Never silent-drop.

### Pitfall 5: Narrow drift scope on its own

**Symptom**: "I diffed `merge-base..upstream/main`, found 3 mirror hits, ported them, declared victory." Later the user asks "did you check XYZ?" and you find 49 more drifted files you missed.

**Cause**: Narrow scope only catches drift in the recent merge window. If the fork was based on an older upstream era and has been falling behind for multiple cycles, the bulk of drift is OUTSIDE the immediate window.

**Fix**: Always run BOTH narrow AND broad scope (Phase B above). Treat the narrow scope hits as "definitely action-required" and the broad scope hits as "needs triage". Never skip the broad pass.

### Pitfall 6: Misreading `uv run` sandbox noise as a `task.py finish` bug

**Symptom**: Lifecycle smoke shows `uv run python ./.trellis/scripts/task.py finish` exiting with `2`, but `.trellis/.current-task` is cleared and the script side effects already happened.

**Cause**: The non-zero exit can come from `uv` itself trying to touch the default cache under `~/.cache/uv` in a read-only or sandboxed environment. That is an environment/runtime artifact, not necessarily a `cmd_finish()` logic bug.

**Rule**:

- When validating `task.py` semantics, run the script directly with `python3` to isolate the script's own exit behavior.
- When validating the real workflow path with `uv run`, make the cache writable first: `UV_CACHE_DIR=.cache/uv uv run python ...`
- Do not file a lifecycle-script regression until you have separated `uv` runtime noise from script logic.

**Practical check**:

```bash
# Script semantics
python3 ./.trellis/scripts/task.py finish; echo "exit=$?"

# Real workflow path with writable cache
UV_CACHE_DIR=.cache/uv uv run python ./.trellis/scripts/task.py finish; echo "exit=$?"
```

If the first command returns `0` but the second one fails only when `UV_CACHE_DIR` is missing, the problem is the `uv` environment, not `task.py`.

### Pitfall 7: Using research agent to verify task-jsonl injection

**Symptom**: You run a smoke test through `research` and conclude "hook injection is broken" because the agent cannot see `implement.jsonl` / `check.jsonl`.

**Cause**: This is by design. `get_research_context()` is intentionally lightweight: it loads only the project structure overview plus optional `research.jsonl`. It does not load task-specific implement/check/debug/review jsonl files.

**Rule**: To verify PreToolUse task-context injection, use `implement`, `check`, `debug`, or `review`. Use `research` only for codebase discovery and optional extra search scope.

---

## Decision Heuristics

| Situation | Default action |
|---|---|
| `overlay > upstream + 50 lines`, lots of new logic | KEEP — heavy customization |
| `overlay > upstream + 2 lines`, just a docstring header | KEEP — attribution noise |
| `overlay < upstream`, fewer lines than upstream | INVESTIGATE — fork may have missed an upstream addition |
| `overlay ≈ upstream`, same size, scattered tiny diffs | LIKELY noise (whitespace, import order) — verify and KEEP |
| `overlay diverges in named function bodies (e.g., main)` | INVESTIGATE — could be drifted bug fix or intentional rewrite |
| `Upstream introduced a new platform/feature, fork file lists platforms` | PORT — extend the fork's enumeration to include the new one |
| `Upstream refactored a helper, fork uses the helper differently` | INVESTIGATE — read both sides before deciding |

---

## Anti-checklist (don't do these)

- ❌ Don't merge upstream directly on `main`
- ❌ Don't rebase fork commits onto upstream (use merge)
- ❌ Don't trust narrow scope alone
- ❌ Don't grep top-level files only (follow imports)
- ❌ Don't edit overlay files expecting local skill behavior to change
- ❌ Don't change `git config --global` to fix line endings (use repo-local)
- ❌ Don't rewrite workflow files without listing their imperative directives first
- ❌ Don't blindly copy upstream's new patterns into fork files that have their own protocol (e.g., JSON envelope vs plain print)
- ❌ Don't `--force-push` the sync branch under any circumstances

---

## Related guides

- `cross-platform-thinking-guide.md` — line endings and shell vs python details (see also Pitfall 3 above)
- `code-reuse-thinking-guide.md` — when overlay drift overlaps with reusable utility design
- `cross-layer-thinking-guide.md` — when upstream changes data contracts that the fork has its own version of

---

**Core Principle**: Fork sync is not a rebase or a merge — it is a *negotiation* between upstream's evolution and the fork's intentional divergence. Phase A handles the merge mechanics; Phase B catches the drift; Phase C resolves the negotiation surgically. **Skipping any phase guarantees silent regression.**

---

## Downstream Update Flow (Consumer Projects)

> **Scope**: Propagating hiskens overlay changes to downstream consumer projects (e.g., Anhui_CIM, Topo-Reliability) using `trellis update --overlay hiskens`. This is SEPARATE from Phase A/B/C above (which handle upstream merge into the fork itself).

### Prerequisites

1. **Rebuild the CLI** if `packages/cli/src/**` has been modified since last build:
   ```bash
   cd packages/cli && pnpm run build
   ```
   Verify dist freshness by comparing a recently modified src template against its dist counterpart. If they differ, dist is stale.

2. **Consumer project must be git-clean** (or at least have no changes in `.trellis/` or `.claude/` paths).

### Execution pattern

```bash
cd /path/to/consumer-project

# 1. Pre-update digest (verify user data survives)
find .trellis/tasks .trellis/workspace -type f \
  \( -name "*.md" -o -name "*.json" -o -name "*.jsonl" -o -name "*.yaml" \) \
  -print0 | sort -z | xargs -0 sha256sum > /tmp/pre.sha256

# 2. Safety branch
git checkout -b trellis-update-v<version>

# 3. Dry-run → review
yes | node /path/to/trellis.js update --overlay hiskens --dry-run

# 4. Execute with --create-new (non-destructive conflict strategy)
yes | node /path/to/trellis.js update --overlay hiskens --create-new

# 5. Per-file verification + conflict resolution (see Pitfall 0 above)
# 6. Post-update digest check (diff pre vs post, expect empty)
# 7. Validation (project-specific: ruff, pytest, etc.)
# 8. Commit + FF merge to main
```

### Known Topo/Anhui local customizations (ALWAYS keep local)

| File | Reason |
|---|---|
| `.trellis/worktree.yaml` | Project-specific `verify:` hooks and `copy:` entries |
| `.trellis/.gitignore` | Project-specific ignore rules (`.link-state.json`, `tasks/`, `workspace/`, etc.) |

### Overlay model convention

**Decision**: All hiskens overlay agents default to `model: opus`.

Upstream v0.4.0+ drifts some agents toward `model: sonnet`. The overlay source-of-truth (`overlays/hiskens/templates/claude/agents/*.md`) pins `opus` to prevent recurring drift during downstream updates.

If a downstream project wants `sonnet` for a specific agent, it can override locally. But the overlay default is `opus`.
