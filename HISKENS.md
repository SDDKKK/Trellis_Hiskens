# Trellis_Hiskens — Customized Fork

**Fork source**: https://github.com/mindfold-ai/Trellis
**Based on**: v0.4.0-beta.10 (commit: 737f750)
**Forked at**: 2026-04-13
**Maintainer**: Hiskens (SDDKKK)

## Purpose

This is a non-destructive customization fork of Trellis, using the overlay mechanism (`overlays/hiskens/`) to layer custom templates on top of upstream base templates.

See `.trellis/tasks/` in the consumer projects for the migration plan.

## Upstream Sync

```bash
git fetch upstream --tags
git merge upstream/main  # or a specific tag
```

Customizations live entirely in `overlays/hiskens/` and should never conflict with upstream.

## Upstream Remote

```bash
git remote add upstream https://github.com/mindfold-ai/Trellis.git
```
