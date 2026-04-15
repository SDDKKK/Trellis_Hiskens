[!] **Prerequisite**: This command should only be used AFTER the human has tested and committed the code.

**AI must NOT execute git commit** - only read history (`git log`, `git status`, `git diff`).

---

## Record Work Progress (Simplified - Only 2 Steps)

### Step 1: Get Context & Check Tasks

```bash
python3 ./.trellis/scripts/get_context.py --mode record
```

[!] Archive tasks whose work is **actually done** — judge by work status, not the `status` field in task.json:
- Code committed? → Archive it (don't wait for PR)
- All acceptance criteria met? → Archive it
- Don't skip archiving just because `status` still says `planning` or `in_progress`

```bash
python3 ./.trellis/scripts/task.py archive <task-name>
```

### Step 2: One-Click Add Session

```bash
# Method 1: Simple parameters
python3 ./.trellis/scripts/add_session.py \
  --title "Session Title" \
  --commit "hash1,hash2" \
  --summary "Brief summary of what was done"

# Method 2: With learning (captures knowledge for future sessions)
python3 ./.trellis/scripts/add_session.py \
  --title "Session Title" \
  --commit "hash1,hash2" \
  --summary "Brief summary" \
  --learning "Discovered that X must be done before Y because..."

# Method 3: Pass detailed content via stdin
cat << 'EOF' | python3 ./.trellis/scripts/add_session.py --stdin --title "Title" --commit "hash"
| Feature | Description |
|---------|-------------|
| New API | Added user authentication endpoint |
| Frontend | Updated login form |

**Updated Files**:
- `packages/api/modules/auth/router.ts`
- `apps/web/modules/auth/components/login-form.tsx`
EOF
```

**Auto-completes**:
- [OK] Appends session to journal-N.md
- [OK] Auto-detects line count, creates new file if >2000 lines
- [OK] Updates index.md (Total Sessions +1, Last Active, line stats, history)
- [OK] Auto-commits `.trellis/workspace` and `.trellis/tasks` changes

---

## Step 3: Nocturne Memory Check

> **Note**: Nocturne updates should have been done in `/trellis:finish-work` Step 6.
> Only run this if finish-work was skipped or you have additional learnings from the commit/test cycle.

If you still need to promote learnings:
1. Read: `read_memory("trellis://projects/<project-id>/learnings")`
2. Append: `update_memory(uri, append="## Title (Session N)\n\nContent...")`

---

## Archive Completed Task (if any)

[!] Archive tasks whose work is **actually done** — judge by work status, not the `status` field in task.json:
- Code committed? → Archive it (don't wait for PR)
- All acceptance criteria met? → Archive it
- Don't skip archiving just because `status` still says `planning` or `in_progress`

If a task was completed this session:

```bash
python3 ./.trellis/scripts/task.py archive <task-name>
```

---

## Script Command Reference

| Command | Purpose |
|---------|---------|
| `get_context.py` | Get all context info |
| `add_session.py --title "..." --commit "..."` | **One-click add session (recommended)** |
| `task.py create "<title>" [--slug <name>]` | Create new task directory |
| `task.py archive <name>` | Archive completed task |
| `task.py list` | List active tasks |
