# Research: npm Publish Mechanism for `@mindfoldhq/trellis@hiskens`

- **Query**: How can the Trellis_Hiskens fork be published to `@mindfoldhq` npm scope under the `hiskens` dist-tag?
- **Scope**: internal (repo-only)
- **Date**: 2026-05-02

---

## TL;DR

- Package name is **already** `@mindfoldhq/trellis` (same as upstream). The fork inherits the upstream identity.
- The user **cannot publish to `@mindfoldhq` unless they are added as a member of that npm org** (or rename the package to a scope they control, e.g. `@hiskens/trellis`).
- The npm `files` field is `["dist", "bin", "README.md", "LICENSE"]`. Repo-root `overlays/` is **not** listed, but the build step **copies `overlays/` into `dist/overlays/`** (via `scripts/copy-templates.js`), so overlays **are** shipped in the tarball as `dist/overlays/hiskens/...`.
- `BUILTIN_OVERLAY_DIRS[0] = path.resolve(__dirname, "../overlays")` resolves correctly when installed globally because at runtime `__dirname = .../node_modules/@mindfoldhq/trellis/dist/utils` and `../overlays = .../dist/overlays/`.
- Standard publish workflow (after build): `cd packages/cli && npm publish --tag hiskens --access public --no-git-checks`.

---

## Findings

### Files Inspected

| File Path | Description |
|---|---|
| `/home/hcx/github/Trellis_Hiskens/packages/cli/package.json` | Package manifest (name, version, files, scripts, publishConfig) |
| `/home/hcx/github/Trellis_Hiskens/package.json` | Root workspace orchestration scripts |
| `/home/hcx/github/Trellis_Hiskens/pnpm-workspace.yaml` | pnpm workspace declaration (`packages/*`) |
| `/home/hcx/github/Trellis_Hiskens/packages/cli/.npmrc` | `ignore-workspace-root-check=true` (per-package npm config) |
| `/home/hcx/github/Trellis_Hiskens/.github/workflows/publish.yml` | CI publish pipeline triggered by `release` events and `v*` tag pushes |
| `/home/hcx/github/Trellis_Hiskens/.github/workflows/ci.yml` | Build verification on `packages/cli/**` changes |
| `/home/hcx/github/Trellis_Hiskens/.github/workflows/upstream-sync.yml` | Automated upstream sync (separate from publish) |
| `/home/hcx/github/Trellis_Hiskens/packages/cli/scripts/copy-templates.js` | Build asset copier (templates, manifests, **overlays**) |
| `/home/hcx/github/Trellis_Hiskens/packages/cli/scripts/check-manifest-continuity.js` | Pre-release migration-manifest gate vs npm |
| `/home/hcx/github/Trellis_Hiskens/packages/cli/tsconfig.json` | TS build config (`outDir: ./dist`, `rootDir: ./src`) |
| `/home/hcx/github/Trellis_Hiskens/packages/cli/src/utils/overlay.ts` | `BUILTIN_OVERLAY_DIRS` and `resolveOverlayPath()` |
| `/home/hcx/github/Trellis_Hiskens/packages/cli/bin/trellis.js` | Entry shim: `import("../dist/cli/index.js")` |
| `/home/hcx/github/Trellis_Hiskens/HISKENS.md` | Fork purpose, layout, validation commands |
| `/home/hcx/github/Trellis_Hiskens/.upstream-version` | Tracked upstream tag: `v0.5.0-beta.18` |

No `.npmignore` exists (verified via `find -name .npmignore`). The `files` allowlist in `package.json` is the sole inclusion filter.

---

### 1. Current Package Identity

`/home/hcx/github/Trellis_Hiskens/packages/cli/package.json`:

```json
{
  "name": "@mindfoldhq/trellis",
  "version": "0.5.0-beta.18",
  "type": "module",
  "main": "./dist/index.js",
  "types": "./dist/index.d.ts",
  "bin": {
    "trellis": "./bin/trellis.js",
    "tl": "./bin/trellis.js"
  },
  "publishConfig": { "access": "public" },
  "files": ["dist", "bin", "README.md", "LICENSE"]
}
```

- `repository.url`: `https://github.com/mindfold-ai/trellis.git` (still points at upstream — not the fork at `SDDKKK/Trellis_Hiskens`).
- `publishConfig.access = public` makes scoped packages public (otherwise `@mindfoldhq/...` would default to private and fail without a paid plan).

### 2. npm Scope Ownership Implications

The scope `@mindfoldhq` belongs to the upstream maintainers (Mindfold LLC). To publish under that exact name:

- The user (`SDDKKK`) must be invited to the `mindfoldhq` npm organization with at least **Developer** role (write access to `@mindfoldhq/trellis`).
- Without that membership, `npm publish` will return `403 Forbidden — You do not have permission to publish "@mindfoldhq/trellis"`.
- An NPM access token (`NPM_TOKEN` repo secret in CI) for a user with publish rights is required either way.

If the user does **not** have publish rights on `@mindfoldhq`, the only way to ship under the same import surface for consumers is:

1. Get added to the `@mindfoldhq` org (preferred — keeps the install command identical), **or**
2. Rename the package (e.g. `@hiskens/trellis` or `@sddkkk/trellis`) and instruct consumers to install that name. This requires changing `name` in `package.json` and most likely `repository.url`, and consumers would run `npm install -g @hiskens/trellis@hiskens` instead.

The user's stated install command `npm install -g @mindfoldhq/trellis@hiskens` therefore **assumes** they have `@mindfoldhq` publish rights — this is the gating prerequisite.

### 3. `npm publish --tag hiskens` Workflow

Once permissions are in place, the dist-tag `hiskens` is just a label that decouples this fork's releases from the `latest` / `beta` channels used by upstream. Manual publish steps:

```bash
# from repo root
pnpm install --frozen-lockfile
pnpm --filter @mindfoldhq/trellis build      # runs clean + tsc + copy-templates
cd packages/cli
# prepublishOnly auto-runs: pnpm test && pnpm run build && cp ../../README.md ../../LICENSE .
npm publish --tag hiskens --access public --no-git-checks
```

Key flags / notes:

- `--tag hiskens` writes the `hiskens` dist-tag pointing at the just-uploaded version. It does **not** move `latest` (so upstream's `latest` is unaffected).
- `--access public` is redundant given `publishConfig.access = public` but harmless and matches the existing CI step.
- `--no-git-checks` skips pnpm's clean-tree assertion; the existing CI uses it because the GitHub-Actions checkout sets `fetch-depth: 0` but doesn't guarantee a clean working tree.
- `pnpm publish` and `npm publish` both honour `files` and `publishConfig`. The CI workflow uses `pnpm publish ... --tag ${{ steps.npm-tag.outputs.tag }}`.
- After publishing, consumers install with: `npm install -g @mindfoldhq/trellis@hiskens` — npm resolves the `hiskens` dist-tag to the fork's version.
- To later move the tag without re-publishing: `npm dist-tag add @mindfoldhq/trellis@<version> hiskens`.

#### Existing CI auto-detection (`.github/workflows/publish.yml`, lines 38–54)

The workflow auto-derives the tag from the version string:

```yaml
if [[ "$VERSION" == *"-beta"* ]]; then
  echo "tag=beta" >> $GITHUB_OUTPUT
elif [[ "$VERSION" == *"-alpha"* ]]; then
  echo "tag=alpha" >> $GITHUB_OUTPUT
elif [[ "$VERSION" == *"-rc"* ]]; then
  echo "tag=rc" >> $GITHUB_OUTPUT
else
  echo "tag=latest" >> $GITHUB_OUTPUT
fi
```

There is **no branch** for the `hiskens` dist-tag. To make the existing workflow publish under `hiskens`, one of these is needed:

- Use a version preid like `0.5.0-hiskens.1` and add an `*"-hiskens"*` branch above, **or**
- Override the tag detection unconditionally on this fork (e.g. always `tag=hiskens`), **or**
- Bypass the workflow and run `npm publish --tag hiskens` manually / from a local script.

The publish workflow triggers on `release` events and any `v*` tag push (lines 4–8), so any tag like `v0.5.0-hiskens.1` would also fire CI.

### 4. Does the CLI Package Include `overlays/`?

**Yes — but indirectly, via `dist/overlays/`, not the repo-root `overlays/`.**

`packages/cli/package.json` `files` field (lines 78–83):

```json
"files": ["dist", "bin", "README.md", "LICENSE"]
```

This excludes the repo-root `overlays/` directly. However, `scripts/copy-templates.js` (lines 76–82) copies it into the build output:

```js
const repoOverlaysDir = join("..", "..", "overlays");
if (existsSync(repoOverlaysDir)) {
  copyDir(repoOverlaysDir, "dist/overlays");
  console.log("Copied ../../overlays/ to dist/overlays/");
}
```

Verified on disk: `/home/hcx/github/Trellis_Hiskens/packages/cli/dist/overlays/hiskens/` exists with `overlay.yaml`, `templates/`, `migrations/`, `exclude.yaml`, `MAINTENANCE.md`, `RTK-INTEGRATION.md`. Since `dist/` is in `files`, all of `dist/overlays/**` ships in the npm tarball.

There is **no `.npmignore`** in the repo (`find -maxdepth 3 -name .npmignore` returned nothing).

### 5. Build → Package → Publish Pipeline

```
src/                                 (TypeScript + templates + manifests)
overlays/hiskens/                    (overlay metadata + templates + migrations)

  pnpm build  =  pnpm clean
              + tsc                            (src/**/*.ts → dist/**/*.js)
              + node scripts/copy-templates.js
                  ├─ copy src/templates/         → dist/templates/        (excludes .ts, __pycache__, *.pyc)
                  ├─ copy src/migrations/manifests/ → dist/migrations/manifests/
                  └─ copy ../../overlays/        → dist/overlays/         (only if it exists)

  prepublishOnly  =  pnpm test && pnpm run build && cp ../../README.md ../../LICENSE .

  pnpm publish --tag <tag> --access public --no-git-checks
                ├─ honours `files`: dist/, bin/, README.md, LICENSE
                └─ tarball uploaded to https://registry.npmjs.org

  consumer:  npm install -g @mindfoldhq/trellis@hiskens
                ├─ tarball expanded to ~/.../node_modules/@mindfoldhq/trellis/
                └─ bin "trellis" linked from <prefix>/bin/trellis → bin/trellis.js
                                          → import("../dist/cli/index.js")
```

Pre-release gates (in `release:*` scripts at `packages/cli/package.json` lines 32–37):

1. `node scripts/check-manifest-continuity.js` — fails if any npm-published version is missing a local migration manifest (KNOWN_GAPS list of historical exceptions exists; do not extend).
2. `node scripts/check-docs-changelog.js --type {beta|rc|promote}` — verifies docs changelog entry (only for beta/rc/promote tracks).
3. `pnpm test` — vitest run.
4. `pnpm version --no-git-tag-version <bump>` — bumps `package.json` only.
5. `git commit` + `git tag v$V` + `git push origin <branch> --tags`.

The `release` script does **not** itself call `npm publish`; it pushes the tag and CI's `publish.yml` reacts to the tag push and runs `pnpm publish`.

`prepublishOnly` (line 31) auto-runs locally before any direct `npm publish` and copies repo-root `README.md` and `LICENSE` into `packages/cli/`, so they end up in the tarball via the `files` allowlist.

### 6. `BUILTIN_OVERLAY_DIRS` Resolution When Installed Globally

`packages/cli/src/utils/overlay.ts` lines 24–33:

```ts
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const BUILTIN_OVERLAY_DIRS = [
  // Packaged CLI layout after build: dist/utils/overlay.js -> dist/overlays/
  path.resolve(__dirname, "../overlays"),
  // Optional package-root layout for local development or future packaging.
  path.resolve(__dirname, "../../overlays"),
  // Monorepo source layout: packages/cli/src/utils/overlay.ts -> repo overlays/
  path.resolve(__dirname, "../../../../overlays"),
];
```

After `npm install -g @mindfoldhq/trellis@hiskens`, the layout under the npm prefix becomes:

```
<prefix>/lib/node_modules/@mindfoldhq/trellis/
├── bin/trellis.js
├── dist/
│   ├── cli/index.js
│   ├── utils/overlay.js     ← __dirname = <prefix>/lib/node_modules/@mindfoldhq/trellis/dist/utils
│   ├── overlays/hiskens/    ← matches BUILTIN_OVERLAY_DIRS[0] = "../overlays"
│   ├── templates/
│   └── ...
├── README.md
├── LICENSE
└── package.json
```

Resolution at runtime:

| Index | Expression | Resolves to (global install) | Exists? |
|---|---|---|---|
| 0 | `path.resolve(__dirname, "../overlays")` | `<pkg>/dist/overlays` | YES (built by `copy-templates.js`) |
| 1 | `path.resolve(__dirname, "../../overlays")` | `<pkg>/overlays` | NO (not in `files`) |
| 2 | `path.resolve(__dirname, "../../../../overlays")` | `<prefix>/lib/overlays` or higher | NO |

`resolveOverlayPath("hiskens")` (line 162) iterates these in order and returns the first directory that exists, so it returns `<pkg>/dist/overlays/hiskens` for a globally-installed CLI. **The `--overlay hiskens` flag works after global install.**

The other two entries are local-development fallbacks (monorepo source layout and an unused package-root layout), neither of which applies to a tarball install.

### 7. Other Hiskens-Specific Considerations

- **`repository.url` still points at upstream** (`https://github.com/mindfold-ai/trellis.git`). npm shows this URL on the registry page; consumers clicking "Repository" would land on the upstream repo, not the fork. Update to `https://github.com/SDDKKK/Trellis_Hiskens.git` if you want users to find the fork's source.
- **`prepublishOnly` script** (`cp ../../README.md ../../LICENSE .`) copies the repo-root files into `packages/cli/`. The fork has a customized `README.md` and the inherited upstream `LICENSE` (AGPL-3.0-only). Both will ship in the tarball.
- **Manifest continuity check** (`check-manifest-continuity.js`) queries the public `npm view @mindfoldhq/trellis versions` and compares to local `src/migrations/manifests/*.json`. If the fork pushes a version that overlaps with what upstream has already published, the check expects the matching local manifests. For a `hiskens`-suffixed version (e.g. `0.5.0-beta.18-hiskens.1`), there is no name collision with upstream beta numbers, but a same-name same-version publish would fail at `npm publish` itself with `403 Forbidden — cannot publish over existing version`.
- **Version strategy choice**: published version must be unique per name. To coexist with upstream `0.5.0-beta.18`, use a longer prerelease tail like `0.5.0-beta.18-hiskens.1` or jump to a fork-distinct major like `0.5.100`. Using bare `0.5.0-beta.18` would conflict if upstream already published it (and the manifest-continuity gate confirms upstream has).

---

## Caveats / Not Found

- No fork-specific publish workflow exists; `.github/workflows/publish.yml` is upstream-shaped and assumes `beta`/`alpha`/`rc`/`latest` dist-tags only. Adding a `hiskens` branch (or hard-overriding the tag) is required for CI-driven publishes.
- No `.npmrc` at the repo root that scopes `@mindfoldhq` to a specific registry (only `packages/cli/.npmrc` with `ignore-workspace-root-check=true`). For org auth on a CI runner, the existing workflow relies on `actions/setup-node@v4` setting `registry-url` and `NODE_AUTH_TOKEN` from `secrets.NPM_TOKEN`.
- The npm org access question (whether SDDKKK is a member of `@mindfoldhq`) cannot be answered from the repo alone — it's an external permission question. If the user is **not** a member, the publish command fails with 403 regardless of the tag flag.
- I did not query the live npm registry to confirm whether `0.5.0-beta.18` (or any version) is already published — verify with `npm view @mindfoldhq/trellis versions` before picking a fork version number.
