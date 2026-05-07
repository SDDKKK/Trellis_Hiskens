# Research: trellis init / update + overlay flow

- **Query**: How `trellis init` and `trellis update` handle overlays; option parsing; config persistence; hash tracking.
- **Scope**: Internal (CLI source code).
- **Date**: 2026-05-02
- **Repo**: `/home/hcx/github/Trellis_Hiskens` (fork of upstream Trellis, currently at v0.5.0-beta.18)

---

## 1. `trellis init` — `--overlay` parsing

### CLI option registration

File: `packages/cli/src/cli/index.ts:99`

```ts
.option("--overlay <name>", "Apply a built-in or absolute-path overlay")
```

- Option name: `--overlay <name>`
- **No short alias.** `-u` is NOT an alias for `--overlay`.
- Argument is a string (overlay name OR absolute path).

### `-u` is the developer flag

File: `packages/cli/src/cli/index.ts:78-81`

```ts
.option(
  "-u, --user <name>",
  "Initialize developer identity with specified name",
)
```

- `-u` ↔ `--user <name>` — sets the developer identity (writes `.trellis/.developer`).
- This is unrelated to overlays.

### `InitOptions` type

File: `packages/cli/src/commands/init.ts:829-854`

```ts
interface InitOptions {
  cursor?: boolean; claude?: boolean; opencode?: boolean; codex?: boolean;
  // ... other platform booleans ...
  yes?: boolean;
  user?: string;          // <- -u value
  force?: boolean;
  skipExisting?: boolean;
  template?: string;
  overwrite?: boolean;
  append?: boolean;
  registry?: string;
  monorepo?: boolean;
  overlay?: string;       // <- --overlay value
}
```

So `options.user` and `options.overlay` are independent fields.

### Call sequence inside `init()`

There are two code paths, both call the same overlay helpers:

#### Path A — fresh init (`init()` main function)

File: `packages/cli/src/commands/init.ts:1631-1656`

```ts
await createWorkflowStructure(cwd, { ... });
await applyWorkflowOverlay(cwd, options.overlay);   // 1637

// ...write .version, monorepo config...

for (const tool of tools) {
  const platformId = resolveCliFlag(tool);
  if (platformId) {
    await configurePlatform(platformId, cwd, options.overlay);  // 1654
  }
}
```

`configurePlatform` (in `configurators/index.ts:836-844`) chains:
```ts
PLATFORM_FUNCTIONS[platformId].configure(cwd)
  .then(() => applyPlatformOverlay(cwd, platformId, overlayName));
```

So the overlay is applied AFTER each platform's own configurator runs.

Effective sequence on fresh init:
1. `applyWorkflowOverlay(cwd, options.overlay)` — overlays the `.trellis/` (`trellis` → `.trellis`) layer.
2. For each selected platform: `configurePlatform(...)` runs base configurator, then `applyPlatformOverlay(cwd, platformId, options.overlay)`.
3. `initializeHashes(cwd)` is called at line 1670 — AFTER overlays have written files, so overlay outputs are hashed.

#### Path B — re-init (`handleReinit()`)

File: `packages/cli/src/commands/init.ts:610-826`

Inner closures (lines 631-659) wrap the same calls:

```ts
const applyRequestedWorkflowOverlay = async () => {
  if (!options.overlay) return;
  await applyWorkflowOverlay(cwd, options.overlay);  // 638
};

const applyRequestedPlatformOverlay = async (platformId) => {
  if (!options.overlay) return;
  await applyPlatformOverlay(cwd, platformId, options.overlay);  // 652
};
```

When the only thing the user passes is `--overlay <name>` (no platform flag, no `-u`):

File: `packages/cli/src/commands/init.ts:662-673`

```ts
if (!doAddPlatforms && !doAddDeveloper) {
  if (options.overlay) {
    await applyRequestedWorkflowOverlay();
    await applyRequestedConfiguredPlatformOverlays();   // loops platforms
    const hashedCount = initializeHashes(cwd);
    return true;
  }
  // ...
}
```

So `trellis init --overlay hiskens` on an already-initialized project will:
1. Apply the `hiskens` workflow overlay.
2. Apply the `hiskens` platform overlay for every already-configured platform.
3. Re-run `initializeHashes()` so post-overlay file hashes become the new baseline.

---

## 2. `trellis update`

### CLI option registration

File: `packages/cli/src/cli/index.ts:115-135`

```ts
program
  .command("update")
  .option("--dry-run", ...)
  .option("-f, --force", ...)
  .option("-s, --skip-all", ...)
  .option("-n, --create-new", ...)
  .option("--allow-downgrade", ...)
  .option("--migrate", "Apply pending file migrations (renames/deletions)")
  .option("--overlay <name>", "Apply a built-in or absolute-path overlay")
  .action(...)
```

- **Yes**, `--overlay` exists on `trellis update`.
- **Yes**, `--migrate` exists on `trellis update`.

### `UpdateOptions`

File: `packages/cli/src/commands/update.ts:54-62`

```ts
export interface UpdateOptions {
  dryRun?: boolean;
  force?: boolean;
  skipAll?: boolean;
  createNew?: boolean;
  allowDowngrade?: boolean;
  migrate?: boolean;
  overlay?: string;
}
```

### What `--migrate` does

`--migrate` opts in to applying pending file rename / delete migrations declared in the migrations manifest.

Behaviour summary (from `update.ts` reading):

1. Without `--migrate`, `update` STILL:
   - Auto-deletes files matching `safe-file-delete` manifests when their hash matches `allowed_hashes` (line ~1693, `executeSafeFileDeletes`).
   - Updates auto-update files (template changed, user did not modify).
   - Prompts on `changedFiles` (user-modified templates).
   - Runs the regular template-write pass.
2. With `--migrate`, `update` ALSO runs `executeMigrations` for the classified `auto` and `confirm` migration items (file renames, dir renames, deletions of deprecated paths) — see `update.ts:1982-2019`.
3. **Hard gate** (`update.ts:1760-1786`): when crossing a version boundary that is `breaking` AND `recommendMigrate`, calling `update` WITHOUT `--migrate` exits with `process.exit(1)` and prints "MIGRATION REQUIRED" — so users are forced to opt in for breaking releases.
4. With `--migrate` AND a breaking release, `breakingBypass` is set (`update.ts:1664-1671`). This:
   - Bypasses `update.skip` paths from `config.yaml` for `safe-file-delete` (so deprecated files under skip-protected paths are still cleaned).
   - Bypasses `update.skip` for template collection so new templates land everywhere.
   - User customizations are still gated at write-time via the "Modified by you" conflict prompt.

### Hash comparison logic during update

#### Loading hashes
File: `packages/cli/src/commands/update.ts:1629`

```ts
const hashes = loadHashes(cwd);    // reads .trellis/.template-hashes.json
const isFirstHashTracking = Object.keys(hashes).length === 0;
```

#### Per-file classification
File: `packages/cli/src/commands/update.ts:582-630` (`analyzeChanges`)

For every `(relativePath, newContent)` in the templates map:

```text
exists?
├── no
│   └── stored hash present? -> userDeletedFiles (preserve deletion)
│       no                  -> newFiles
└── yes
    ├── existingContent === newContent       -> unchangedFiles
    └── differs:
        ├── storedHash && storedHash === currentHash
        │   OR (no storedHash && isKnownUntrackedTemplate(...))
        │     -> autoUpdateFiles (auto-write)
        └── otherwise -> changedFiles (user modified, prompt)
```

`computeHash` (in `template-hash.ts:43-46`) normalises CRLF→LF before SHA-256 so Windows checkouts hash the same as Linux ones.

#### Writing hashes back

File: `packages/cli/src/commands/update.ts:2113-2134`

After file writes, `updateHashes(cwd, filesToHash)` is called for:
- All `newFiles` content.
- All `autoUpdateFiles` content.
- Any `changedFiles` whose on-disk content matches `file.newContent` after the user chose "overwrite".

### Does update reapply overlay files?

**Yes — indirectly, via `collectTemplateFiles`.**

File: `packages/cli/src/commands/update.ts:1674-1679`

```ts
const templates = collectTemplateFiles(
  cwd,
  codexUpgradeNeeded ? new Set<AITool>(["codex"]) : undefined,
  breakingBypass,
  options.overlay,
);
```

`collectTemplateFiles` (`update.ts:478-558`) merges, in order:

1. Built-in Python scripts (`getAllScripts`).
2. Built-in workflow files (`config.yaml`, `.gitignore`, `workflow.md`).
3. `AGENTS.md` (rebuilt to preserve user content outside the TRELLIS block).
4. `collectWorkflowOverlayTemplates(overlayName)` — overlay layer for `.trellis/`.
5. For each configured platform: `collectPlatformTemplates(platformId, overlayName)` (also overlay-aware via `applyOverlayToTemplateMap`).

So `trellis update --overlay hiskens` rebuilds the in-memory template map WITH overlay files, then runs the same diff/conflict pipeline on those overlay-augmented contents.

`trellis update` WITHOUT `--overlay` will NOT include any overlay files — overlay-only files would then look "orphaned" (present on disk, not in templates) and simply be left alone (they are not in `templates`, so `analyzeChanges` never sees them).

There is also a separate runtime path (in `configurators/index.ts:639-752`, `applyOverlayToProject`) that writes overlay files directly to disk and emits a `.new` warning when the existing file is user-modified. This path is used by `applyWorkflowOverlay` / `applyPlatformOverlay` from `init`, NOT from `update` — `update` only consumes the overlay through `collectTemplateFiles`.

---

## 3. Config persistence: how does the CLI remember the overlay?

### Short answer: **It does not.**

There is NO field in `.trellis/config.yaml` and no other on-disk record of which overlay was used to init the project. Verified by:

- `grep -rn "options.overlay" packages/cli/src/` returns only:
  - `cli/index.ts:134` — flag forwarding.
  - `commands/init.ts` — overlay function calls.
  - `commands/update.ts:1678` — overlay function calls.
  - **No write back to disk.**
- `grep -rn "appendFileSync.*config\|writeFileSync.*config.yaml"` only finds `writeMonorepoConfig` (writes `packages:` / `default_package:`) — not overlay.
- The actual `.trellis/config.yaml` in this repo (lines 1-80) has NO `overlay:` key.
- `.template-hashes.json` (read above) is a flat `{ relativePath: sha256 }` map, with no overlay metadata. Files coming from an overlay are hashed identically to built-in templates.

### Practical consequence

Every overlay-aware command must be re-passed `--overlay <name>` explicitly. After `trellis init --overlay hiskens`:

- `trellis update` (no flag) — diffs against built-in templates ONLY. Overlay-only files become "untracked" and are left alone, but template files that the overlay had OVERRIDDEN will diff back to the upstream version (and likely show up as "Modified by you" because the on-disk content differs from the built-in template).
- `trellis update --overlay hiskens` — diffs against overlay-augmented templates, which is the intended path.

This is the primary friction point for fork maintenance: there is no `auto-overlay` field, so consumer projects must remember to pass `--overlay hiskens` on every `trellis update`.

---

## 4. Hash tracking: `initializeHashes` in `template-hash.ts`

File: `packages/cli/src/utils/template-hash.ts`

### Storage format (v2)

File: `packages/cli/src/utils/template-hash.ts:25-35`

```ts
const HASHES_FILE = ".template-hashes.json";
const HASHES_SCHEMA_VERSION = 2;

interface StoredHashesV2 {
  __version: number;
  hashes: TemplateHashes;     // { [relPosixPath: string]: sha256hex }
}
```

Path: `<cwd>/.trellis/.template-hashes.json`. Verified on disk:

```json
{
  "__version": 2,
  "hashes": {
    ".claude/skills/trellis-meta/references/customize-local/add-project-local-conventions.md":
      "86009ccb5d0373f...",
    ...
  }
}
```

Legacy flat-format (no `__version`) is silently dropped by `loadHashes` (line 99-100) — handles a Windows backslash-keys + CRLF migration.

### `computeHash`

File: `packages/cli/src/utils/template-hash.ts:43-46`

```ts
export function computeHash(content: string): string {
  const normalized = content.replace(/\r\n/g, "\n");
  return createHash("sha256").update(normalized, "utf-8").digest("hex");
}
```

### `loadHashes` / `saveHashes`

- `loadHashes(cwd)` (line 75-104): reads JSON, validates v2 shape, returns `TemplateHashes` with POSIX-normalised keys.
- `saveHashes(cwd, hashes)` (line 111-118): writes v2 shape, POSIX keys, two-space-indented JSON.

### `updateHashes`

File: `packages/cli/src/utils/template-hash.ts:126-134`

```ts
export function updateHashes(cwd: string, files: Map<string, string>): void {
  const hashes = loadHashes(cwd);
  for (const [relativePath, content] of files) {
    hashes[toPosix(relativePath)] = computeHash(content);
  }
  saveHashes(cwd, hashes);
}
```

Merge-style update — does NOT clear existing keys.

### `initializeHashes` (called by `init`)

File: `packages/cli/src/utils/template-hash.ts:343-383`

```ts
export function initializeHashes(cwd: string): number {
  const hashes: TemplateHashes = {};

  for (const relativePath of TEMPLATE_FILES) {            // [AGENTS.md]
    if (shouldExcludeFromHash(relativePath)) continue;
    const fullPath = path.join(cwd, relativePath);
    if (!fs.existsSync(fullPath)) continue;
    try {
      const content = fs.readFileSync(fullPath, "utf-8");
      hashes[relativePath] = computeHash(content);
    } catch { /* skip binary */ }
  }

  for (const dir of TEMPLATE_DIRS) {            // ALL_MANAGED_DIRS
    const files = collectFiles(cwd, dir);
    for (const relativePath of files) {
      const fullPath = path.join(cwd, relativePath);
      try {
        const content = fs.readFileSync(fullPath, "utf-8");
        hashes[relativePath] = computeHash(content);
      } catch { /* skip binary */ }
    }
  }

  saveHashes(cwd, hashes);
  return Object.keys(hashes).length;
}
```

Key behaviours:
- **Whole-disk re-scan**: it OVERWRITES the entire hash file with the freshly-scanned set. Any old entry for a deleted file is wiped.
- Scans `ALL_MANAGED_DIRS` (every platform's configDir + `.trellis`) plus root `AGENTS.md`.
- `shouldExcludeFromHash` filters out `.template-hashes.json`, `.version`, `.gitignore`, `.developer`, `workspace/`, `tasks/`, `.current-task`, `.trellis/spec/`, `.backup-`.
- Returns the count of hashed files (used by `init` for the "Tracking N template files" log line).
- **Critical**: because `initializeHashes` reads from DISK, it captures files WRITTEN BY THE OVERLAY too. Overlay outputs become tracked templates indistinguishable from upstream ones in the hash set.

### Other helpers

- `removeHash(cwd, relativePath)` — drops a single key.
- `renameHash(cwd, oldPath, newPath)` — moves the value.
- `updateHashFromFile(cwd, relativePath)` — reads disk + writes one hash.
- `isTemplateModified(cwd, relativePath, hashes)` — true if no stored hash OR current sha mismatch. Conservative: returns `true` for unknown files.
- `matchesOriginalTemplate(cwd, relativePath, originalContent)` — exact-string compare (used by migration classifier).

---

## Files Found

| File Path | Relevance |
|---|---|
| `packages/cli/src/cli/index.ts` | CLI entry; option registration for `init` and `update` |
| `packages/cli/src/commands/init.ts` | `init()` and `handleReinit()`; overlay call sites |
| `packages/cli/src/commands/update.ts` | `update()` whole pipeline; hash diff; migration gating |
| `packages/cli/src/configurators/index.ts` | `applyWorkflowOverlay`, `applyPlatformOverlay`, `configurePlatform`, `applyOverlayToProject`, `applyOverlayToTemplateMap`, overlay target maps |
| `packages/cli/src/utils/overlay.ts` | `resolveOverlayPath`, `getOverlayTemplatePath`, `loadExcludeList`, `readOverlayFiles`, `mergeSettings` |
| `packages/cli/src/utils/template-hash.ts` | Hash schema v2, `computeHash`, `loadHashes/saveHashes/updateHashes`, `initializeHashes`, `isTemplateModified` |
| `.trellis/config.yaml` (this repo) | Verified: NO `overlay:` field |
| `.trellis/.template-hashes.json` (this repo) | Verified: v2 schema, flat hash map, no overlay metadata |
| `.trellis/.version` (this repo) | `0.5.0-beta.18` |

---

## Caveats / Not Found

- **Overlay name is not persisted anywhere** — confirmed by exhaustive grep, by reading `init`/`update` end-to-end, and by inspecting the actual `.trellis/config.yaml` and `.template-hashes.json` in this fork. Any tooling that wants to "remember" the overlay (e.g., to auto-apply on update) would need a NEW field — that work has not been done in upstream as of v0.5.0-beta.18.
- The existence of `.trellis/.ralph-state.json` was noted but is unrelated to overlays (likely related to Ralph the upstream sync helper) — not investigated.
- The overlay direct-write path (`applyOverlayToProject` in `configurators/index.ts:639-752`) ALREADY contains a `.new` fallback when overlay would clobber a user-modified template. So the "overlay safety" gate uses `.template-hashes.json` to detect modification — this means `init --overlay X` after init still respects the same hash-based "user customised" guarantee that `update` uses.
