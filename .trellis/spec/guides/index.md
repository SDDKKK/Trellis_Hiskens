# Hiskens Guide Index

Thinking guides carried by this fork. Each entry below resolves to a file that
actually exists — if you add a guide, add it here; if you remove one, remove the
line.

> Pruned at the v0.6.14 sync. The previous version of this index was imported
> from an older Hiskens v0.5 overlay project and listed 14 guides that were
> never brought into this repository, plus `spec/python/` and `spec/matlab/`
> directories that do not exist here. Those dead links are gone.

## Development methodology

- [Code Reuse Thinking Guide](./code-reuse-thinking-guide.md) — find the existing helper before writing a new one; includes the two-script-tree sync convention.

## Architecture and boundaries

- [Cross Layer Thinking Guide](./cross-layer-thinking-guide.md) — contracts between layers, and the failure modes that only show up at a boundary.

## Platform notes

- [Cross Platform Thinking Guide](./cross-platform-thinking-guide.md) — platform-specific assumptions to catch before they ship. Carries the fork-authored **Claude Code Subprocess Environment Visibility** section (overlay point 9 in the `trellis-overlay` skill); preserve it when merging upstream.
