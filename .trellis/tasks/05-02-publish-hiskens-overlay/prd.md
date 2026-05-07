# Publish @hiskens/trellis Customized Overlay Package

## Goal

Rebuild the Trellis_Hiskens fork as a minimal, publishable `@hiskens/trellis` npm package with a slim overlay (~15 files vs current 134), CLI enhancements (`-u` alias + overlay persistence), synced to upstream v0.5.0-rc.1. Consumers install via `npm install -g @hiskens/trellis@hiskens` and use `trellis init -u Hiskens` for one-command setup.

## What I already know

**From 5 parallel research agents (2026-05-02):**

- Overlay mechanism: files in `overlays/hiskens/templates/` **replace** upstream wholesale (no merge except `settings.overlay.json`). Every kept file = hard fork.
- Current overlay: 134 files, only 8 CORE needed for the 3 customizations (CCR hook + MCP agent swap + config).
- CCR hook: already fully implemented in active `.claude/hooks/inject-subagent-context.py` (841 lines, 3 functions + main() integration), but **NOT in overlay template** — consumer projects don't get it.
- npm publishing: `copy-templates.js` copies `overlays/` → `dist/overlays/`, `BUILTIN_OVERLAY_DIRS[0]` resolves correctly after global install.
- CLI flags: `-u` is `--user` (developer identity), NOT overlay alias. `--overlay` has no short form.
- Overlay name NOT persisted — every `trellis update` must re-pass `--overlay`.
- ZZ_KKX reference (rc.1): confirms minimal surface is 9 overlay-deliverable files.
- Fork has 47 overlay commits on top of beta.18; upstream delta beta.18→rc.1 is 38 commits (init bugfix, workflow-state breadcrumb system, opencode refactor). `overlay.ts` and `configurators/index.ts` unchanged in rc.1.
- `common/` module is broken — stale v0.4 fork missing `worktree.py`, causes `ModuleNotFoundError`.

**Research artifacts:**
- `.trellis/tasks/research/overlay-surface-audit.md`
- `.trellis/tasks/research/npm-publish-mechanism.md`
- `.trellis/tasks/research/ccr-hook-analysis.md`
- `.trellis/tasks/research/init-update-flow.md`
- `.trellis/tasks/research/zzkkx-reference-audit.md`

## User Decisions (2026-05-02)

1. **npm scope**: `@hiskens/trellis` (not `@mindfoldhq`)
2. **NICE-TO-HAVE keep**: python/matlab spec packs + Nocturne scripts → keep; extra hooks (statusline, intent-gate, todo-enforcer, context-monitor, ralph-loop) → **drop**
3. **-u alias**: `trellis init -u Hiskens` = `--user Hiskens --overlay hiskens` (dual semantics)
4. **Overlay persistence**: implement `overlay:` field in config.yaml, auto-read on `trellis update`
5. **Version strategy**: sync to rc.1 first, then publish

## Requirements

### R1: Sync to upstream v0.5.0-rc.1
- New branch from `v0.5.0-rc.1` tag
- Cherry-pick only structural CLI commits (overlay loader): `8cb5d21`, `f5b3636`, `df8500c`
- Cherry-pick test commit: `e3462f5`
- Cherry-pick overlay settings placeholder fix: `0734cb6`
- Resolve conflicts against rc.1 base
- Do NOT rebase the full 47-commit history

### R2: Slim overlay (134 → ~15 files)
Target tree:
```
overlays/hiskens/
├── overlay.yaml
├── templates/
│   ├── claude/
│   │   ├── agents/
│   │   │   ├── trellis-check.md
│   │   │   ├── trellis-implement.md
│   │   │   └── trellis-research.md
│   │   ├── hooks/
│   │   │   ├── inject-subagent-context.py    (CCR functions)
│   │   │   └── session-start.py              (FIRST_REPLY_NOTICE)
│   │   └── settings.overlay.json
│   ├── trellis/
│   │   ├── config.yaml                       (features.ccr_routing)
│   │   ├── config/
│   │   │   └── agent-models.example.json
│   │   ├── spec/
│   │   │   ├── python/  (8 files)            [KEEP]
│   │   │   └── matlab/  (6 files)            [KEEP]
│   │   └── scripts/
│   │       ├── init-nocturne-namespace.py     [KEEP]
│   │       ├── nocturne_client.py             [KEEP]
│   │       ├── promote-to-nocturne.py         [KEEP]
│   │       └── sync-trellis-to-nocturne.py    [KEEP]
│   └── codex/
│       └── agents/
│           ├── trellis-implement.toml         (context-load preamble)
│           └── trellis-check.toml             (context-load preamble)
```
**~25 files** (8 CORE + 14 spec + 4 Nocturne + 2 codex = 28, plus overlay.yaml)

DELETE everything else: `scripts/common/` (18), `commands/trellis/` (20), codex v0.4 agents (3), hooks (statusline/intent-gate/todo-enforcer/context-monitor/ralph-loop/statusline-bridge/parse_sub2api_usage = 7), skills (4), agents/skills (10), search scripts (5), prd-template, worktree.yaml, MAINTENANCE.md, RTK-INTEGRATION.md.

Fix `settings.overlay.json`: remove wiring for dropped hooks, keep only model/thinking/env/RTK.

### R3: CLI `-u` overlay alias
- In `packages/cli/src/commands/init.ts`: if `options.user` is set and `options.overlay` is not, auto-set `options.overlay = options.user.toLowerCase()`
- In `packages/cli/src/commands/update.ts`: add `-u, --user <name>` option that auto-fills `--overlay`
- `trellis init -u Hiskens` = developer identity "Hiskens" + overlay "hiskens"

### R4: Overlay persistence in config.yaml
- After `trellis init --overlay X`, write `overlay: X` to `.trellis/config.yaml`
- In `trellis update`, if `!options.overlay`, read `overlay` from config.yaml
- Add `writeOverlayToConfig(cwd, name)` and `readOverlayFromConfig(cwd)` helpers
- Use the existing `parseSimpleYaml` for reading; for writing, append/replace the `overlay:` line

### R5: Package scope change
- `packages/cli/package.json`: name → `@hiskens/trellis`, repository.url → `SDDKKK/Trellis_Hiskens`
- Root `package.json`: update `--filter` references
- `.github/workflows/publish.yml`: add `*"-hiskens"*` tag detection → `tag=hiskens`
- Version: `0.5.0-rc.1-hiskens.1`
- `scripts/check-manifest-continuity.js`: update package name in `npm view`

## Acceptance Criteria

- [ ] `pnpm build` succeeds, `dist/overlays/hiskens/` has ~28 files (not 134)
- [ ] `pnpm typecheck` passes
- [ ] `pnpm test` passes (vitest)
- [ ] Smoke: `trellis init --claude --codex -u Hiskens -y` in temp dir produces ZZ_KKX-equivalent surface
- [ ] Smoke: `trellis update` (no --overlay) auto-reads overlay from config.yaml
- [ ] Smoke: `trellis update --overlay hiskens --dry-run` works
- [ ] `python3 -m py_compile` passes on all overlay .py files
- [ ] `npm pack` in packages/cli shows @hiskens/trellis with correct files
- [ ] inject-subagent-context.py has CCR functions at correct insertion points
- [ ] agent MDs have augment + grok-search tools (not exa)
- [ ] config.yaml template has features.ccr_routing: true

## Definition of Done

- All acceptance criteria green
- No TypeScript type errors
- No lint errors
- Overlay .py files compile
- HISKENS.md updated to reflect new structure

## Out of Scope

- Actual npm publish (only verify `npm pack`)
- Upstream PR to persist overlay (fork-only feature)
- Hooks: statusline, intent-gate, todo-enforcer, context-monitor, ralph-loop
- Skills: fork-sync-strategy, github-explorer, grok-search, with-codex
- Commands: all 20 custom command overrides
- scripts/common/ fork (use upstream common/)
- agents/skills/ platform-agnostic skills (use upstream)

## Technical Approach

### Strategy: Clean Branch from rc.1

1. Create `hiskens-v1` branch from `v0.5.0-rc.1`
2. Cherry-pick 5 structural commits (overlay loader + tests + settings fix)
3. Build slim overlay as new commits
4. Apply CLI mods (R3, R4, R5) as separate commits
5. Build, test, validate

### Why not rebase 47 commits?

- Deleting 80% of overlay files makes most old commits empty/conflicting
- CLI source changes (R3, R4) would conflict with maintenance commits
- Clean branch is faster, auditable, and produces cleaner git history

## Decision (ADR-lite)

**Context**: Fork has 134 overlay files, most are stale/drifted. Need a publishable package.
**Decision**: Clean branch from rc.1 + cherry-pick structural commits + rebuild slim overlay.
**Consequences**: Lose detailed git history of individual overlay file additions. Gain: clean, auditable, minimal diff surface. Old branch preserved for reference.

## Error & Rescue Map

| Operation | Failure Mode | Impact | Rescue Strategy |
|-----------|--------------|--------|-----------------|
| Cherry-pick structural commits | Merge conflict with rc.1 | Blocked | Manual conflict resolution; commits are small (overlay.ts, configurators) |
| Slim overlay | Miss a CORE file | Broken init | ZZ_KKX reference as ground truth checklist |
| -u alias | Break existing -u/--user behavior | Developer identity lost | Guard: only auto-fill overlay when overlay not explicitly set |
| Overlay persistence | config.yaml write corruption | Broken config | Use append-only strategy; never rewrite full file |
| Package rename | npm publish collision | 403 error | Use unique scope @hiskens |
| inject-subagent-context.py | CCR functions on wrong base | Runtime error | Diff against ZZ_KKX version (rc.1 base + CCR) |

## Architecture

```
Consumer project
  ↓ npm install -g @hiskens/trellis@hiskens
  ↓ trellis init -u Hiskens --claude --codex -y
  ↓
  ├── applyWorkflowOverlay("hiskens")     → .trellis/ files
  ├── configurePlatform("claude-code")    → .claude/ base
  │   └── applyPlatformOverlay("hiskens") → .claude/ overlay (agents, hooks, settings merge)
  ├── configurePlatform("codex")          → .codex/ base
  │   └── applyPlatformOverlay("hiskens") → .codex/ overlay (agent toml preamble)
  ├── writeOverlayToConfig(cwd, "hiskens") → config.yaml overlay: hiskens  [NEW]
  └── initializeHashes()                  → .template-hashes.json

  ↓ trellis update (no --overlay needed!)
  ↓
  ├── readOverlayFromConfig(cwd)          → "hiskens"  [NEW]
  └── collectTemplateFiles(overlay="hiskens") → overlay-augmented diff
```

## Temporal Notes

| Time Window | Focus |
|-------------|-------|
| HOUR 1 | Cherry-pick structural commits onto rc.1, resolve conflicts |
| HOUR 2 | Build slim overlay: copy CORE files from current overlay, adapt to rc.1 base |
| HOUR 3 | CLI mods: -u alias (init.ts, update.ts), overlay persistence (init.ts, update.ts, config helper) |
| HOUR 4 | Package rename, version bump, CI workflow update |
| HOUR 5 | Build + typecheck + test + smoke tests |
| HOUR 6 | Fix failures, update HISKENS.md, final validation |

## Technical Notes

- `overlay.ts` and `configurators/index.ts` unchanged between beta.18 and rc.1 — cherry-picks should be clean
- `init.ts` changed in rc.1 (issue #204 fix) — cherry-pick may need manual resolution
- `update.ts` changed significantly in rc.1 (workflow-state breadcrumb) — cherry-pick of hash fix may conflict
- ZZ_KKX inject-subagent-context.py is 825 lines (rc.1 base + CCR), current overlay version is 841 lines (beta.18 base + CCR + extra platform code) — use ZZ_KKX version as reference
- `common/` module breakage: after slim overlay removes the forked `common/`, projects will use upstream's working version
