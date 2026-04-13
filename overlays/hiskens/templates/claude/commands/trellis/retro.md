# Retrospective Analysis

Analyze recent development activity and produce a metrics report with improvement suggestions.

**Usage**:
- `/trellis:retro` — last 7 days (default)
- `/trellis:retro 14d` — last 14 days
- `/trellis:retro 30d` — last 30 days

---

## Operation Types

| Marker | Meaning | Executor |
|--------|---------|----------|
| `[AI]` | Bash scripts or file reads executed by AI | You (AI) |
| `[USER]` | Slash commands executed by user | User |

---

## Step 1: Determine Time Window `[AI]`

Parse the argument from the command invocation. Default to 7 days if not specified.

```bash
# Determine the date boundary (example for 7 days)
SINCE=$(date -d "7 days ago" "+%Y-%m-%d" 2>/dev/null || date -v-7d "+%Y-%m-%d")
echo "Analyzing since: $SINCE"
```

---

## Step 2: Gather Git Metrics `[AI]`

```bash
# Commits in window
git log --since="$SINCE" --oneline --no-merges

# Net LOC change (insertions/deletions)
git log --since="$SINCE" --numstat --no-merges --pretty="" | \
  awk 'NF==3 {ins+=$1; del+=$2} END {print "insertions:", ins, "deletions:", del}'

# Commit time distribution (hour of day)
git log --since="$SINCE" --format="%ad" --date=format:"%H" --no-merges | \
  sort | uniq -c | sort -k2 -n

# Most frequently changed files
git log --since="$SINCE" --name-only --no-merges --pretty="" | \
  grep -v "^$" | sort | uniq -c | sort -rn | head -10

# Active days count
git log --since="$SINCE" --format="%ad" --date=format:"%Y-%m-%d" --no-merges | \
  sort -u | wc -l

# Test file ratio
git log --since="$SINCE" --name-only --no-merges --pretty="" | \
  grep -v "^$" | sort -u | \
  awk '/test/{t++} {total++} END {printf "test files changed: %d/%d\n", t, total}'
```

---

## Step 3: Gather Task Metrics `[AI]`

```bash
# Completed tasks in window
find .trellis/tasks/archive -name "task.json" -newer /tmp/retro-sentinel 2>/dev/null || \
  find .trellis/tasks/archive -name "task.json" | \
  xargs grep -l '"status": "completed"' 2>/dev/null | head -20

# Active tasks
python3 .trellis/scripts/task.py list 2>/dev/null || \
  find .trellis/tasks -maxdepth 2 -name "task.json" ! -path "*/archive/*" | \
  xargs grep -l '"status"' 2>/dev/null

# Count completed vs total tasks
echo "Completed tasks in archive:"
find .trellis/tasks/archive -name "task.json" 2>/dev/null | wc -l
echo "Active tasks:"
find .trellis/tasks -maxdepth 2 -name "task.json" ! -path "*/archive/*" 2>/dev/null | wc -l
```

---

## Step 4: Gather Session & Learning Metrics `[AI]`

```bash
# Count journal entries in window (approximate)
find .trellis/workspace -name "journal-*.md" | \
  xargs grep -l "## Session" 2>/dev/null | head -5

# Count new learnings in window
grep -c "^##" .trellis/memory/learnings.md 2>/dev/null || echo "0"

# Open issues count
grep -c "^## Issue:" .trellis/memory/known-issues.md 2>/dev/null || echo "0"
```

---

## Step 5: Ralph Loop Metrics `[AI]`

```bash
# Read Ralph Loop state (if exists)
cat .trellis/.ralph-state.json 2>/dev/null || echo "No Ralph state found"
```

---

## Step 6: Check for Prior Retro Snapshots `[AI]`

```bash
# List prior retro snapshots for trend comparison
ls .trellis/workspace/retros/ 2>/dev/null | tail -5 || echo "No prior retros found"

# If prior snapshots exist, read the most recent one for comparison
LAST_RETRO=$(ls .trellis/workspace/retros/*.json 2>/dev/null | tail -1)
if [ -n "$LAST_RETRO" ]; then
  cat "$LAST_RETRO"
fi
```

---

## Step 7: Produce Report `[AI]`

Using the data gathered above, produce a structured report in this format:

---

### Retrospective Report — [DATE_RANGE]

#### Summary

| Metric | Value | vs Last Retro |
|--------|-------|---------------|
| Commits | N | +/-N |
| Net LOC | +N / -N | — |
| Active days | N | — |
| Test file ratio | N% | — |
| Completed tasks | N | — |
| New learnings | N | — |
| Open issues | N | — |
| Ralph avg iterations | N | — |

#### Commit Time Distribution

Show hourly histogram (identify peak productivity hours):

```
00h  |
06h  | ***
09h  | **********
12h  | *******
15h  | ************
18h  | ****
21h  |
```

Peak hours: [list top 3 hours]

#### Hotspot Files (Most Changed)

| File | Changes | Flag |
|------|---------|------|
| path/to/file | N | CHURN if >5 |
| ... | | |

Files with >5 changes in window are flagged as potential churn candidates.

#### Task Completion Metrics

- Completed: N / Total N (N%)
- Average cycle time: N days (if data available)
- Currently blocked: N tasks

#### Trends vs Last Retro

| Metric | Last | This | Delta |
|--------|------|------|-------|
| Commits/day | N | N | +/-% |
| Net LOC/commit | N | N | +/-% |
| Completed tasks | N | N | +/- |

(Skip this section if no prior retro snapshot exists)

#### Improvement Suggestions

Based on the data above, provide exactly 3 actionable suggestions. Examples:

1. **[Pattern]** If hotspot files have high churn: "Consider refactoring `path/to/file` — changed N times in N days, indicating instability."
2. **[Timing]** If commits cluster outside working hours: "Commits concentrated at [hour] — consider scheduling complex work during [peak hour] for better focus."
3. **[Quality]** If test ratio is low: "Test files represent only N% of changes — consider adding regression tests for recently changed modules."

Suggestions must reference actual data from the metrics, not generic advice.

---

## Step 8: Save Snapshot `[AI]`

Save the metrics as a JSON snapshot for future trend comparison:

```bash
mkdir -p .trellis/workspace/retros

SNAPSHOT_DATE=$(date "+%Y-%m-%d")
SNAPSHOT_N=$(ls .trellis/workspace/retros/${SNAPSHOT_DATE}-*.json 2>/dev/null | wc -l)
SNAPSHOT_FILE=".trellis/workspace/retros/${SNAPSHOT_DATE}-$((SNAPSHOT_N + 1)).json"

# Write snapshot (populate values from gathered metrics above)
cat > "$SNAPSHOT_FILE" << EOF
{
  "date": "$SNAPSHOT_DATE",
  "window_days": WINDOW_DAYS,
  "commits": COMMITS_COUNT,
  "net_loc_insertions": INSERTIONS,
  "net_loc_deletions": DELETIONS,
  "active_days": ACTIVE_DAYS,
  "completed_tasks": COMPLETED_TASKS,
  "new_learnings": NEW_LEARNINGS,
  "open_issues": OPEN_ISSUES,
  "ralph_avg_iterations": RALPH_AVG
}
EOF

echo "Snapshot saved: $SNAPSHOT_FILE"
```

Replace the ALL_CAPS placeholders with actual numeric values from the gathered data.

---

## Notes

- All data sources are local — no network calls required
- If a data source is unavailable (e.g., no `.trellis/.ralph-state.json`), skip that metric and note it
- The report is informational, not prescriptive — present data, then suggest
- `/trellis:retro` complements `/trellis:finish-work` (per-session) with period-level trends
