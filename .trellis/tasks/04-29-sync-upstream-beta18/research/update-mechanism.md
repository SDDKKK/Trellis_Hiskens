# Research: trellis update --overlay hiskens mechanism

- **Query**: How does `trellis update --overlay hiskens` work, and can this repo run it on itself?
- **Scope**: internal
- **Date**: 2026-04-29

---

## Q1: How does `trellis update` decide which files to write/delete/skip?

### `collectTemplateFiles()` — `packages/cli/src/commands/update.ts:478`

Builds a `Map<relativePath, content>` of everything that *should* exist.
Sources in order:

1. All Python scripts from `getAllScripts()` → `.trellis/scripts/**`
2. Core trellis files: `config.yaml`, `.gitignore`, `workflow.md`
3. `AGENTS.md` (preserves the existing `<!-- TRELLIS:START … END -->` block if present)
4. Workflow overlay templates via `collectWorkflowOverlayTemplates(overlayName)` — e.g. `.trellis/` files from `overlays/hiskens/templates/trellis/`
5. Platform templates for **every platform whose configDir already exists on disk** (detected by `getConfiguredPlatforms(cwd)`)
6. Each platform's overlay templates merged on top via `applyOverlayToTemplateMap()`
7. `update.skip` paths from `.trellis/config.yaml` are deleted from the map after all the above

### `analyzeChanges()` — `packages/cli/src/commands/update.ts:568`

For every entry in the template map, classifies it into one of:

| Bucket | Condition |
|---|---|
| `newFiles` | File doesn't exist on disk AND no hash in `.template-hashes.json` |
| `userDeletedFiles` | File doesn't exist on disk BUT hash IS in hashes file → user intentionally deleted, respected, NOT re-created |
| `unchangedFiles` | Disk content == template content (already up to date) |
| `autoUpdateFiles` | Disk ≠ template, but stored hash == current disk hash (user never touched it) → auto-overwrites |
| `changedFiles` | Disk ≠ template, stored hash ≠ current disk hash (user modified) → asks for confirmation |

**Files NOT in the template map are never touched by this logic.** There is no "legacy cleanup" from `analyzeChanges` alone; old files that have been removed from the template set are simply ignored.

### Legacy cleanup: `safe-file-delete` migrations

The only mechanism that actually *deletes* files is `collectSafeFileDeletes()` (line 201), which runs against **all migration manifests** (not just version-gated ones). It auto-deletes a file if and only if:

- The file exists on disk
- The file's SHA256 hash matches one of the listed `allowed_hashes` in the manifest entry
- The path is not in `PROTECTED_PATHS` and not in `update.skip`

This is the "legacy cleanup" path. If a template was retired between versions, it must have a `safe-file-delete` manifest entry to be removed.

---

## Q2: How does `--overlay` affect the update?

### Workflow overlay (`.trellis/` files)

`collectWorkflowOverlayTemplates(overlayName)` calls `applyOverlayToTemplateMap()` with `WORKFLOW_OVERLAY_TARGETS = [{ overlayDir: "trellis", outputDir: ".trellis" }]`.

Inside `applyOverlayToTemplateMap()` (configurators/index.ts:574):

1. Reads `overlays/hiskens/exclude.yaml` → any listed paths are **deleted from the template map** first
2. Reads all files under `overlays/hiskens/templates/trellis/` → each is added to the map at the corresponding `.trellis/<rest>` project path
3. If the file is `settings.overlay.json` and the target has a `settingsTargetPath`, it JSON-merges the overlay into the base settings file instead of replacing it

### Platform overlay (`.claude/`, `.codex/`, `.agents/` etc.)

`collectPlatformTemplates(platformId, overlayName)` calls `applyOverlayToTemplateMap()` with `PLATFORM_OVERLAY_TARGETS[platformId]`. For `claude-code`:

```
{ overlayDir: "claude", outputDir: ".claude", settingsTargetPath: ".claude/settings.json" }
```

For `codex`:
```
{ overlayDir: "codex", outputDir: ".codex" },
{ overlayDir: "agents", outputDir: ".agents" }
```

**Does overlay-aware update remove non-overlay legacy files?**
No. The exclude list in `exclude.yaml` only removes entries from the *template map* being built. It does NOT cause existing on-disk files to be deleted. Legacy file removal still requires a `safe-file-delete` migration manifest entry.

---

## Q3: Can this repo run `trellis update` on itself?

**Prerequisites checked by `update()`:**

1. `.trellis/` directory must exist → **exists** (`/home/hcx/github/Trellis_Hiskens/.trellis/`)
2. `.trellis/.version` must exist → **exists**, contains `0.5.0-beta.18`
3. CLI version must be >= project version (unless `--allow-downgrade`)

**CLI available:**

The globally installed `trellis` is v0.3.6 — older than the project's `0.5.0-beta.18`. Running `trellis update` with the global binary would be blocked as a downgrade.

The local build at `packages/cli/bin/trellis.js` is v0.5.0-beta.18. Running:

```bash
node packages/cli/bin/trellis.js update --overlay hiskens --dry-run
```

from the repo root would work. The `BUILTIN_OVERLAY_DIRS` search in `dist/utils/overlay.js` includes:

```js
path.resolve(__dirname, "../../../../overlays")
// dist/utils/ -> dist/ -> packages/cli/ -> packages/ -> repo-root/overlays/
```

So `overlays/hiskens` would be found at the 4th path level, which is exactly the repo root `overlays/hiskens/`.

**Platforms it would update:**
Only platforms whose configDir already exists. In this repo:
- `.claude/` exists → `claude-code` templates collected
- `.codex/` exists → `codex` templates collected  
- `.agents/` alone does NOT trigger detection (by design, line 783: "Detection uses only `configDir`")

---

## Q4: What about `.trellis/.template-hashes.json`?

**File exists** at `/home/hcx/github/Trellis_Hiskens/.trellis/.template-hashes.json`.

**Format** (schema v2):
```json
{
  "__version": 2,
  "hashes": {
    ".claude/skills/trellis-meta/...": "sha256hex...",
    ...
  }
}
```

**How it works:**
- At install/update time, for every written file, `updateHashes(cwd, filesToHash)` stores `SHA256(LF-normalized content)` keyed by POSIX path
- At next update, `analyzeChanges()` reads the stored hash and compares to `SHA256(current disk content)`
- If they match → file is unmodified → auto-update eligible
- If they differ → user modified → prompt for resolution

**Legacy file detection:**
`analyzeChanges()` only operates on files *in the template map*. Files that were once tracked in the hashes file but are no longer in the template set are simply not visited by `analyzeChanges()` — they are neither auto-deleted nor flagged. Only `safe-file-delete` migration entries cause deletion of such files.

**Stale hash entries** (hashes for files removed from the template set) accumulate silently. They don't cause errors, but they also don't trigger cleanup.

---

## Q5: Does `trellis update` have a `--dry-run` mode?

**Yes.** The flag is `--dry-run`.

Confirmed from CLI help output:
```
--dry-run    Preview changes without applying them
```

In `update()` at line 1949:
```typescript
if (options.dryRun) {
  console.log(chalk.gray("[Dry run] No changes made."));
  return;
}
```

The dry-run mode:
1. Runs the full version comparison
2. Runs `collectTemplateFiles()` (builds the template map including overlays)
3. Runs `analyzeChanges()` and `collectSafeFileDeletes()` (classifies all changes)
4. Prints the full summary (new files, auto-updates, conflicts, safe-deletes)
5. Then exits **without writing anything**

So the recommended preview command is:

```bash
node packages/cli/bin/trellis.js update --overlay hiskens --dry-run
```

---

## Caveats / Critical Notes

1. **Global trellis v0.3.6 is too old** to run against this project (v0.5.0-beta.18). Must use the local `node packages/cli/bin/trellis.js` entry point.

2. **`overlays/hiskens/` is NOT bundled in `dist/overlays/`** — the `dist/overlays/` directory is empty. The overlay is found only via the monorepo path (`../../../../overlays`). This means the local-build approach works in the repo, but downstream users would only get overlays bundled at build time.

3. **`spec/` is fully protected** — `PROTECTED_PATHS` includes `.trellis/spec/`, so no overlay template under `trellis/spec/` will be written by `update()`. This is by design; spec files are user-customized content. The hiskens overlay has many spec files under `templates/trellis/spec/` — **these will be silently skipped by update**.

4. **The `trellis/spec/` overlay files require manual installation** — they need to be copied manually or via `trellis init`, not via `update`.

5. **No "remove legacy files" without migration manifests** — overlay `exclude.yaml` removes files from the *template map*, which prevents the update from touching those paths. But files already on disk that are no longer needed must be in a `safe-file-delete` manifest to be cleaned up.

6. **`userDeletedFiles` are respected** — if a file was previously installed (hash tracked) but the user deleted it, `update` will NOT re-create it. This is intentional.
