#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/upstream-diff.sh <base-ref> <target-ref> [overlay-dir]

Generate a markdown report for upstream sync review.

Arguments:
  base-ref     Previously tracked upstream ref/tag
  target-ref   New upstream ref/tag to review
  overlay-dir  Overlay root to inspect for references (default: overlays/hiskens)
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -lt 2 || $# -gt 3 ]]; then
  usage >&2
  exit 1
fi

BASE_REF="$1"
TARGET_REF="$2"
OVERLAY_DIR="${3:-overlays/hiskens}"

if ! git rev-parse --verify --quiet "$BASE_REF^{commit}" >/dev/null; then
  echo "Base ref not found: $BASE_REF" >&2
  exit 1
fi

if ! git rev-parse --verify --quiet "$TARGET_REF^{commit}" >/dev/null; then
  echo "Target ref not found: $TARGET_REF" >&2
  exit 1
fi

mapfile -t ADDED_FILES < <(git diff --name-only --diff-filter=A "$BASE_REF" "$TARGET_REF" | sort)
mapfile -t DELETED_FILES < <(git diff --name-only --diff-filter=D "$BASE_REF" "$TARGET_REF" | sort)
mapfile -t MODIFIED_FILES < <(git diff --name-only --diff-filter=MRT "$BASE_REF" "$TARGET_REF" | sort)

timestamp="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

print_list_or_none() {
  local -n files_ref="$1"
  if [[ ${#files_ref[@]} -eq 0 ]]; then
    echo "- None"
    return
  fi

  for file in "${files_ref[@]}"; do
    echo "- \`$file\`"
  done
}

check_overlay_reference() {
  local file="$1"

  if [[ ! -d "$OVERLAY_DIR" ]]; then
    echo "overlay dir missing"
    return
  fi

  if git grep -n -F -- "$file" -- "$OVERLAY_DIR" >/tmp/upstream-diff-overlay.$$ 2>/dev/null; then
    local first_match
    first_match="$(head -n 1 /tmp/upstream-diff-overlay.$$)"
    rm -f /tmp/upstream-diff-overlay.$$
    echo "reference found: \`$first_match\`"
    return
  fi

  rm -f /tmp/upstream-diff-overlay.$$ 2>/dev/null || true
  echo "no overlay reference found"
}

classify_modified_file() {
  local file="$1"

  case "$file" in
    packages/cli/src/templates/claude/hooks/*)
      local hook_name overlay_path
      hook_name="$(basename "$file")"
      overlay_path="$OVERLAY_DIR/templates/claude/hooks/$hook_name"
      if [[ -f "$overlay_path" ]]; then
        printf 'manual review: hook override `%s` must be compared with `%s`' "$overlay_path" "$file"
      else
        printf 'manual review: upstream hook changed (`%s`), no overlay override exists yet' "$file"
      fi
      ;;
    packages/cli/src/commands/*|packages/cli/src/configurators/*|packages/cli/src/utils/overlay.ts)
      printf 'manual review: overlay-loader compatibility must be checked for `%s`' "$file"
      ;;
    *)
      printf 'standard upstream change'
      ;;
  esac
}

echo "# Upstream Diff Report"
echo
echo "- Generated: $timestamp"
echo "- Base ref: \`$BASE_REF\`"
echo "- Target ref: \`$TARGET_REF\`"
echo "- Overlay root: \`$OVERLAY_DIR\`"
echo
echo "## Summary"
echo
echo "- Added files: ${#ADDED_FILES[@]}"
echo "- Deleted files: ${#DELETED_FILES[@]}"
echo "- Modified files: ${#MODIFIED_FILES[@]}"
echo
echo "## Added Files"
echo
print_list_or_none ADDED_FILES
echo
echo "## Deleted Files"
echo
if [[ ${#DELETED_FILES[@]} -eq 0 ]]; then
  echo "- None"
else
  for file in "${DELETED_FILES[@]}"; do
    echo "- \`$file\`"
    echo "  Overlay reference check: $(check_overlay_reference "$file")"
  done
fi
echo
echo "## Modified Files"
echo
if [[ ${#MODIFIED_FILES[@]} -eq 0 ]]; then
  echo "- None"
else
  for file in "${MODIFIED_FILES[@]}"; do
    echo "- \`$file\`"
    echo "  Classification: $(classify_modified_file "$file")"
  done
fi
