#!/usr/bin/env bash
set -euo pipefail

REPO="/home/hcx/github/Trellis_Hiskens"
FINDINGS="$REPO/.trellis/tasks/04-26-research-v0-5-0-beta-sync/findings"
OVERLAY_DIR="$REPO/overlays/hiskens/templates"

cd "$REPO"

# Get all overlay files
find "$OVERLAY_DIR" -type f -not -name '*.pyc' | sort > "$FINDINGS/overlay-files-v2.txt"

# Function to map overlay path to upstream v4 and v5 paths
map_upstream() {
    local rel="$1"
    local v4_path="packages/cli/src/templates/$rel"
    local v5_path="packages/cli/src/templates/$rel"
    
    # Try to detect renames for v5
    # Agents: check.md -> trellis-check.md (but only for claude/cursor/codebuddy/qoder, not all)
    # Codex agents: check.toml -> trellis-check.toml
    
    echo "$v4_path|$v5_path"
}

echo "overlay_path|upstream_v4_path|upstream_v5_path|v4_exists|v5_exists|v5_status|upstream_changed_v4_v5|overlay_vs_v4|classification|risk|action" > "$FINDINGS/classification-v2.csv"

while IFS= read -r overlay_path; do
    rel="${overlay_path#$OVERLAY_DIR/}"
    v4_path="packages/cli/src/templates/$rel"
    v5_path="packages/cli/src/templates/$rel"
    
    # Check v4 existence
    v4_exists="NO"
    if rtk proxy git show "v0.4.0-beta.10:$v4_path" > /dev/null 2>&1; then
        v4_exists="YES"
    fi
    
    # Check v5 existence (at exact path)
    v5_exists="NO"
    v5_status="REMOVED"
    if rtk proxy git show "v0.5.0-beta.14:$v5_path" > /dev/null 2>&1; then
        v5_exists="YES"
        v5_status="PRESENT"
    fi
    
    # Check if upstream changed between v4 and v5 (only if both exist at same path)
    upstream_changed="N/A"
    if [ "$v4_exists" = "YES" ] && [ "$v5_exists" = "YES" ]; then
        diffstat=$(rtk proxy git diff --stat "v0.4.0-beta.10..v0.5.0-beta.14" -- "$v5_path" 2>/dev/null | tail -1)
        if [ -n "$diffstat" ] && echo "$diffstat" | grep -q '[0-9]'; then
            upstream_changed="YES"
        else
            upstream_changed="NO"
        fi
    fi
    
    # Compare overlay to v4
    overlay_vs_v4="N/A"
    if [ "$v4_exists" = "YES" ]; then
        if diff -q <(rtk proxy git show "v0.4.0-beta.10:$v4_path" | sed 's/\r$//') <(sed 's/\r$//' "$overlay_path") > /dev/null 2>&1; then
            overlay_vs_v4="IDENTICAL"
        else
            overlay_vs_v4="DIVERGED"
        fi
    else
        overlay_vs_v4="NOT_IN_V4"
    fi
    
    # Classification
    if [ "$v4_exists" = "NO" ] && [ "$v5_exists" = "NO" ]; then
        classification="OVERLAY-ONLY"
    elif [ "$overlay_vs_v4" = "IDENTICAL" ]; then
        classification="BASELINE"
    else
        classification="APPEND"
    fi
    
    # Risk
    risk="LOW"
    if [ "$v4_exists" = "YES" ] && [ "$v5_exists" = "NO" ]; then
        risk="CRITICAL"
    elif [ "$classification" = "APPEND" ] && [ "$upstream_changed" = "YES" ]; then
        risk="HIGH"
    elif [ "$classification" = "APPEND" ] && [ "$upstream_changed" = "NO" ]; then
        risk="MEDIUM"
    elif [ "$classification" = "BASELINE" ] && [ "$upstream_changed" = "YES" ]; then
        risk="MEDIUM"
    elif [ "$classification" = "OVERLAY-ONLY" ]; then
        risk="LOW"
    elif [ "$classification" = "BASELINE" ] && [ "$upstream_changed" = "NO" ]; then
        risk="LOW"
    fi
    
    # Action
    action=""
    case "$risk|$classification" in
        "CRITICAL|APPEND") action="Upstream removed/renamed path; investigate new upstream location or deprecate" ;;
        "CRITICAL|BASELINE") action="Upstream removed/renamed path; accept removal" ;;
        "CRITICAL|OVERLAY-ONLY") action="Verify this is truly hiskens-only; no upstream involvement" ;;
        "HIGH|APPEND") action="Manual port: merge upstream v0.5 changes while preserving overlay additions" ;;
        "MEDIUM|APPEND") action="Review: upstream unchanged at this path, overlay diverges from v0.4" ;;
        "MEDIUM|BASELINE") action="Accept upstream v0.5 version (overlay identical to v0.4, upstream changed)" ;;
        "LOW|OVERLAY-ONLY") action="No action - hiskens-only content" ;;
        "LOW|BASELINE") action="Consider removing from overlay (dead weight)" ;;
        *) action="Review manually" ;;
    esac
    
    echo "$rel|$v4_path|$v5_path|$v4_exists|$v5_exists|$v5_status|$upstream_changed|$overlay_vs_v4|$classification|$risk|$action"
    
done < "$FINDINGS/overlay-files-v2.txt" >> "$FINDINGS/classification-v2.csv"

echo "Done. Results in $FINDINGS/classification-v2.csv"
