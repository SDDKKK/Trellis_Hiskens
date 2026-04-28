#!/usr/bin/env bash
# Overlay-asset -> upstream-conflict classifier
# Run from repo root
set -euo pipefail

REPO="/home/hcx/github/Trellis_Hiskens"
FINDINGS="$REPO/.trellis/tasks/04-26-research-v0-5-0-beta-sync/findings"
OVERLAY_DIR="$REPO/overlays/hiskens/templates"

cd "$REPO"

# Get all overlay files (sorted)
find "$OVERLAY_DIR" -type f -not -name '*.pyc' | sort > "$FINDINGS/overlay-files.txt"

# Header for results
echo "overlay_path|upstream_path|upstream_exists_v5|upstream_status|upstream_changed_v4_to_v5|overlay_vs_v4_identical|classification|risk|recommended_action" > "$FINDINGS/classification.csv"

while IFS= read -r overlay_path; do
    rel="${overlay_path#$OVERLAY_DIR/}"
    upstream_path="packages/cli/src/templates/$rel"
    
    # Check if upstream still has this file at v0.5.0-beta.14
    upstream_exists_v5="NO"
    upstream_status="REMOVED"
    if rtk proxy git show "v0.5.0-beta.14:$upstream_path" > /dev/null 2>&1; then
        upstream_exists_v5="YES"
        upstream_status="PRESENT"
    else
        # Check if it was renamed
        rename_log=$(rtk proxy git log --oneline --diff-filter=DR "v0.4.0-beta.10..v0.5.0-beta.14" -- "$upstream_path" 2>/dev/null | head -1)
        if [ -n "$rename_log" ]; then
            upstream_status="RENAMED"
        fi
    fi
    
    # Check if upstream changed the file between v0.4.0-beta.10 and v0.5.0-beta.14
    upstream_changed="NO"
    if [ "$upstream_exists_v5" = "YES" ]; then
        diffstat=$(rtk proxy git diff --stat "v0.4.0-beta.10..v0.5.0-beta.14" -- "$upstream_path" 2>/dev/null | tail -1)
        if [ -n "$diffstat" ] && echo "$diffstat" | grep -q '[0-9]'; then
            upstream_changed="YES"
        fi
    fi
    
    # Check if overlay is identical to upstream v0.4.0-beta.10
    overlay_vs_v4_identical="UNKNOWN"
    if rtk proxy git show "v0.4.0-beta.10:$upstream_path" > /dev/null 2>&1; then
        # Compare using diff (LF-normalized)
        if diff -q <(rtk proxy git show "v0.4.0-beta.10:$upstream_path" | sed 's/\r$//') <(sed 's/\r$//' "$overlay_path") > /dev/null 2>&1; then
            overlay_vs_v4_identical="IDENTICAL"
        else
            overlay_vs_v4_identical="DIVERGED"
        fi
    else
        overlay_vs_v4_identical="NOT_IN_UPSTREAM"
    fi
    
    # Classification
    classification="UNKNOWN"
    if [ "$overlay_vs_v4_identical" = "NOT_IN_UPSTREAM" ]; then
        classification="OVERLAY-ONLY"
    elif [ "$overlay_vs_v4_identical" = "IDENTICAL" ]; then
        classification="BASELINE"
    else
        # Diverged from v0.4 - need to determine APPEND vs EXCLUDE
        # For now, mark as APPEND (most common for hiskens)
        # EXCLUDE is typically for files that deliberately replace upstream
        classification="APPEND"
    fi
    
    # Risk assessment
    risk="LOW"
    if [ "$upstream_status" = "REMOVED" ] || [ "$upstream_status" = "RENAMED" ]; then
        risk="CRITICAL"
    elif [ "$classification" = "APPEND" ] && [ "$upstream_changed" = "YES" ]; then
        risk="HIGH"
    elif [ "$classification" = "APPEND" ] && [ "$upstream_changed" = "NO" ]; then
        risk="MEDIUM"
    elif [ "$classification" = "BASELINE" ] && [ "$upstream_changed" = "YES" ]; then
        risk="MEDIUM"
    elif [ "$classification" = "OVERLAY-ONLY" ]; then
        risk="LOW"
    fi
    
    # Recommended action
    action=""
    case "$risk|$classification" in
        "CRITICAL|*")
            action="Investigate upstream removal/rename; update overlay or exclude rule"
            ;;
        "HIGH|APPEND")
            action="Manual port required: merge upstream changes while preserving overlay additions"
            ;;
        "MEDIUM|APPEND")
            action="Review: upstream unchanged, overlay diverges - verify overlay still needed"
            ;;
        "MEDIUM|BASELINE")
            action="Accept upstream v0.5.0 version (overlay is identical to v0.4, upstream changed)"
            ;;
        "LOW|OVERLAY-ONLY")
            action="No action needed - hiskens-only content"
            ;;
        "LOW|BASELINE")
            action="Consider removing from overlay to reduce maintenance burden"
            ;;
        *)
            action="Review manually"
            ;;
    esac
    
    echo "$rel|$upstream_path|$upstream_exists_v5|$upstream_status|$upstream_changed|$overlay_vs_v4_identical|$classification|$risk|$action"
    
done < "$FINDINGS/overlay-files.txt" >> "$FINDINGS/classification.csv"

echo "Classification complete. Results in $FINDINGS/classification.csv"
