---
name: trellis-publish
description: Build, publish @hiskens/trellis to npm, install globally, and dogfood via `trellis update`. Use after any template/script change in packages/cli/src/ that should be distributed. Triggered by "publish trellis", "发布 trellis", "npm publish", "dogfood", "trellis publish", "发布并更新", "打包发布".
---

# Trellis Publish — Build, Publish & Dogfood

---

## Step 1: Bump Version

Determine the new version. Format: `{upstream-version}-hiskens` (e.g., `0.5.0-rc.3.2-hiskens`).

```bash
# Check current
grep '"version"' packages/cli/package.json
cat .trellis/.version
```

Bump in both files:
- `packages/cli/package.json` → `"version": "<new>"`
- `.trellis/.version` → `<new>`

If already bumped this session (e.g., after upstream sync set the version), skip.

## Step 2: Build

```bash
pnpm install && pnpm build
```

Verify output includes `Template copy complete.`

## Step 3: Publish to npm

```bash
cd packages/cli && npm publish --access public --ignore-scripts --tag rc
```

- `--ignore-scripts` skips `prepublishOnly` (tests already validated)
- `--tag rc` avoids accidentally overwriting `latest` on a bad publish

Then promote to `latest`:

```bash
npm dist-tag add @hiskens/trellis@<version> latest
```

**Verify:**
```bash
npm info @hiskens/trellis version  # should show new version
```

## Step 4: Install Published CLI

```bash
npm install -g @hiskens/trellis
```

Verify:
```bash
trellis --version  # should show new version
```

## Step 5: Dogfood — Self-Update This Repo

```bash
trellis update --dry-run   # preview changes
trellis update --force     # apply all
```

**Verify in dry-run output:**
- Updated template files appear (hooks, agents, scripts)
- No unexpected removals

## Step 6: Commit & Push

```bash
# Stage version bump + dogfood changes
git add packages/cli/package.json .trellis/.version \
       .claude/ .codex/ .cursor/ .opencode/ .pi/ \
       .trellis/.template-hashes.json .trellis/config.yaml \
       .trellis/scripts/ .trellis/config/

git commit -m "chore: bump version to <new>"
git push origin main
```

If the version bump was already committed separately (e.g., during an overlay sync), only commit the dogfood diff:

```bash
git add .claude/ .codex/ .cursor/ .opencode/ .pi/ \
       .trellis/.template-hashes.json .trellis/.version .trellis/config.yaml \
       .trellis/scripts/ .trellis/config/
git commit -m "chore: trellis self-update — <summary>"
git push origin main
```

---

## Pitfalls

| Issue | Fix |
|-------|-----|
| `npm publish` fails: "must specify --tag for prerelease" | Already using `--tag rc` — check version string has prerelease segment |
| `trellis update` shows no changes | Forgot `pnpm build` before publish, or npm cache stale — run `npm cache clean --force` |
| `trellis: command not found` after install | Check `npm prefix -g` is in PATH |
| Dogfood reverts a local-only customization | Those files should be in `.trellis/workspace/` (preserved) not template-managed paths |
| `npm install -g` installs old version | `latest` tag not promoted — run `npm dist-tag add ...` |

---

## Quick Reference

```bash
# Full sequence (copy-paste)
pnpm build
cd packages/cli && npm publish --access public --ignore-scripts --tag rc && cd ../..
npm dist-tag add @hiskens/trellis@<VER> latest
npm install -g @hiskens/trellis
trellis update --force
```
