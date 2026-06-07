# Research: Trellis Active Task Resolution Logic

- **Query**: Full logic of resolve_active_task, .current_task, task.json, .developer, task counting, fallback strategy
- **Scope**: internal
- **Date**: 2026-06-07

## Files Found

| File Path | Description |
|---|---|
| `.trellis/scripts/common/active_task.py` | Core active task resolution — `resolve_active_task()`, `set_active_task()`, `clear_active_task()`, session context key resolution, Cursor shell ticket handling |
| `.trellis/scripts/common/paths.py` | Path constants (`DIR_WORKFLOW`, `FILE_DEVELOPER`, `FILE_TASK_JSON`), `get_developer()`, `get_current_task()`, `normalize_task_ref()`, `resolve_task_ref()` |
| `.trellis/scripts/common/tasks.py` | Task data access — `load_task()`, `iter_active_tasks()`, `get_all_statuses()` |
| `.trellis/scripts/common/types.py` | `TaskData` TypedDict (task.json shape), `TaskInfo` frozen dataclass |
| `.trellis/scripts/common/developer.py` | `init_developer()`, `ensure_developer()`, `show_developer_info()` |
| `.trellis/scripts/common/io.py` | `read_json()`, `write_json()` — shared JSON I/O |
| `.trellis/scripts/common/task_store.py` | `cmd_create()` — shows task.json field defaults |
| `.trellis/scripts/common/task_utils.py` | `resolve_task_dir()`, `find_task_by_name()` — directory resolution helpers |
| `.trellis/scripts/common/session_context.py` | Session context generation — consumes `get_current_task()` and `resolve_active_task()` |
| `.trellis/scripts/task.py` | CLI entry — `cmd_start()`, `cmd_current()`, `cmd_finish()`, `cmd_list()` |

---

## 1. `resolve_active_task()` — Full Logic

**File**: `.trellis/scripts/common/active_task.py`, lines 468-494

```python
def resolve_active_task(
    repo_root: Path,
    platform_input: dict[str, Any] | None = None,
    platform: str | None = None,
) -> ActiveTask:
```

### Resolution algorithm (in order):

1. **Resolve context key** via `resolve_context_key(platform_input, platform)`.
2. **If context key exists**: read the session file at `.trellis/.runtime/sessions/{context_key}.json`, extract `current_task` field, build `ActiveTask` with `source_type="session"`.
3. **If no context key OR session file has no task**: fall back to `_resolve_single_session_fallback(repo_root)`.
4. **If fallback also fails**: return `ActiveTask(None, "none", context_key)`.

### Context key resolution (`resolve_context_key`, lines 380-415):

Priority order:
1. **`TRELLIS_CONTEXT_ID` env var** — explicit override for scripts/subprocesses
2. **Platform input dict** — looks for `session_id`/`sessionId`/`sessionID`, then `conversation_id`, then `transcript_path`
3. **Environment variables** — platform-specific env vars (e.g., `CLAUDE_SESSION_ID`, `CODEX_SESSION_ID`, `CURSOR_SESSION_ID`)
4. **Cursor shell ticket** — short-lived `.json` ticket files in `.trellis/.runtime/cursor-shell/` (TTL: 30 seconds)

### Single-session fallback (`_resolve_single_session_fallback`, lines 497-519):

- Scans `.trellis/.runtime/sessions/` directory
- If **exactly 1** `.json` file exists, reads its `current_task` field
- Returns `ActiveTask` with `source_type="session-fallback"`
- If **0 or >=2** session files exist, returns `None` (refuses to guess across windows)

### `ActiveTask` dataclass (lines 81-97):

```python
@dataclass(frozen=True)
class ActiveTask:
    task_path: str | None        # e.g., ".trellis/tasks/06-07-ccline-trellis-segment"
    source_type: str             # "session" | "session-fallback" | "none"
    context_key: str | None      # e.g., "claude_e1f4a0de-9ad3-48a1-8eca-32bdc82e6c74"
    stale: bool = False          # True if task directory no longer exists on disk
```

The `source` property returns human-readable labels like `"session:{context_key}"` or `"session-fallback:{context_key}"`.

---

## 2. Session Pointer (replaces `.current_task`)

**There is no `.current_task` file anymore.** The constant `FILE_CURRENT_TASK = ".current-task"` is defined in `paths.py` line 34 but is **not used** anywhere in the codebase. Active task state is stored per-session in runtime JSON files.

### Session file location

```
.trellis/.runtime/sessions/{context_key}.json
```

### Session file format (live example)

```json
{
  "platform": "claude",
  "last_seen_at": "2026-06-07T03:05:34Z",
  "current_task": ".trellis/tasks/06-07-ccline-trellis-segment",
  "current_run": null
}
```

### Fields in session file:
- `platform` — detected platform name (e.g., "claude", "cursor", "codex")
- `last_seen_at` — ISO 8601 UTC timestamp
- `current_task` — repo-relative POSIX path to task directory (the pointer)
- `current_run` — defaults to `null`, set to `null` on `set_active_task()`
- Additional identity fields may be present: `session_id`, `conversation_id`, `transcript_path`

### Context key naming convention

Format: `{platform}_{sanitized_session_id}` or `{platform}_transcript_{sha256_hash_24chars}`

Examples:
- `claude_e1f4a0de-9ad3-48a1-8eca-32bdc82e6c74`
- `cursor_abc123`
- `codex_transcript_a1b2c3d4e5f6g7h8i9j0k1l2`

Key sanitization (`_sanitize_key`): `re.sub(r"[^A-Za-z0-9._-]+", "_", raw)`, stripped of leading/trailing `._-`, truncated to 160 chars.

---

## 3. `task.json` Structure

**File**: `.trellis/scripts/common/types.py` (TypedDict) + `.trellis/scripts/common/task_store.py` (defaults)

### All fields (from `cmd_create` defaults, `task_store.py` lines 264-289):

```json
{
  "id": "slug-value",
  "name": "slug-value",
  "title": "Human readable title",
  "description": "",
  "status": "planning",
  "dev_type": null,
  "scope": null,
  "package": null,
  "priority": "P2",
  "creator": "DeveloperName",
  "assignee": "DeveloperName",
  "createdAt": "2026-06-07",
  "completedAt": null,
  "branch": null,
  "base_branch": "main",
  "worktree_path": null,
  "commit": null,
  "pr_url": null,
  "subtasks": [],
  "children": [],
  "parent": null,
  "relatedFiles": [],
  "notes": "",
  "meta": {}
}
```

### Field details:

| Field | Type | Description |
|---|---|---|
| `id` | `str` | Slug identifier (same as `name`) |
| `name` | `str` | Slug identifier |
| `title` | `str` | Human-readable title |
| `description` | `str` | Optional description |
| `status` | `str` | `"planning"` / `"in_progress"` / `"review"` / `"completed"` / `"done"` |
| `dev_type` | `str \| null` | Development type |
| `scope` | `str \| null` | Scope for PR title prefix |
| `package` | `str \| null` | Monorepo package name |
| `priority` | `str` | `"P0"` / `"P1"` / `"P2"` / `"P3"` |
| `creator` | `str` | Developer who created the task |
| `assignee` | `str` | Developer assigned to the task |
| `createdAt` | `str` | `"YYYY-MM-DD"` format |
| `completedAt` | `str \| null` | `"YYYY-MM-DD"` when archived |
| `branch` | `str \| null` | Git feature branch |
| `base_branch` | `str \| null` | PR target branch (defaults to current branch at creation) |
| `worktree_path` | `str \| null` | Git worktree path |
| `commit` | `str \| null` | Associated commit |
| `pr_url` | `str \| null` | Pull request URL |
| `subtasks` | `list[str]` | Legacy subtask list |
| `children` | `list[str]` | Child task dir_names (e.g., `["06-07-child-task"]`) |
| `parent` | `str \| null` | Parent task dir_name |
| `relatedFiles` | `list[str]` | Related file paths |
| `notes` | `str` | Freeform notes |
| `meta` | `dict` | Arbitrary metadata dict |

### `TaskInfo` dataclass (loaded form, `types.py` lines 58-93):

```python
@dataclass(frozen=True)
class TaskInfo:
    dir_name: str           # e.g., "06-07-ccline-trellis-segment"
    directory: Path         # absolute path
    title: str              # from task.json "title" or "name" or "unknown"
    status: str             # from task.json "status" or "unknown"
    assignee: str           # from task.json "assignee" or ""
    priority: str           # from task.json "priority" or "P2"
    children: tuple[str, ...]  # from task.json "children" or ()
    parent: str | None      # from task.json "parent"
    package: str | None     # from task.json "package"
    raw: dict               # original dict for writes and uncommon fields
```

`load_task()` in `tasks.py` uses fallback: `data.get("title") or data.get("name") or "unknown"`.

---

## 4. `.developer` File

**Location**: `.trellis/.developer`

**Format**: Plain text, `name=value` pairs, one per line.

```
name=Hiskens
initialized_at=2026-04-15T11:55:41.390329
```

### Reading logic (`paths.py`, `get_developer()`, lines 69-94):

```python
def get_developer(repo_root: Path | None = None) -> str | None:
    dev_file = repo_root / DIR_WORKFLOW / FILE_DEVELOPER  # .trellis/.developer
    if not dev_file.is_file():
        return None
    content = dev_file.read_text(encoding="utf-8")
    for line in content.splitlines():
        if line.startswith("name="):
            return line.split("=", 1)[1].strip()
    return None
```

Key points for Rust port:
- File path: `{repo_root}/.trellis/.developer`
- Read as UTF-8 text
- Split into lines
- Find first line starting with `name=`
- Return everything after `=` (split on first `=` only), stripped of whitespace
- Returns `None` if file missing or no `name=` line found

### Writing logic (`developer.py`, `init_developer()`, lines 58-63):

```python
dev_file.write_text(
    f"name={name}\ninitialized_at={initialized_at}\n",
    encoding="utf-8"
)
```

Only two known fields: `name` and `initialized_at`.

---

## 5. Non-Archived Task Counting

**File**: `.trellis/scripts/common/tasks.py`, `iter_active_tasks()`, lines 54-73

```python
def iter_active_tasks(tasks_dir: Path) -> Iterator[TaskInfo]:
    if not tasks_dir.is_dir():
        return
    for d in sorted(tasks_dir.iterdir()):
        if not d.is_dir() or d.name == "archive":
            continue
        info = load_task(d)
        if info is not None:
            yield info
```

### Algorithm:

1. Get tasks directory: `{repo_root}/.trellis/tasks/`
2. List all entries, sorted by name
3. **Skip** entries that are not directories
4. **Skip** directory named exactly `"archive"`
5. For each remaining directory, try to load `task.json` via `load_task(d)`
6. Only yield if `task.json` exists and parses successfully

### Count derivation:

```python
# All active statuses:
get_all_statuses(tasks_dir) -> {dir_name: status}  # calls iter_active_tasks internally

# Children progress:
children_progress(children, all_statuses)  # counts children with status "completed" or "done"
                                            # or children MISSING from all_statuses (archived = done)
```

### Task directory naming convention:

`{MM-DD}-{slug}` — e.g., `06-07-ccline-trellis-segment`

Date prefix generated by `generate_task_date_prefix()` which returns `datetime.now().strftime("%m-%d")`.

---

## 6. Fallback Strategy When No Session Context Exists

### Full fallback chain (from `resolve_active_task`):

```
1. resolve_context_key()
   ├── TRELLIS_CONTEXT_ID env var?        → use as context key
   ├── platform_input dict has session_id? → build context key
   ├── platform_input has conversation_id? → build context key
   ├── platform_input has transcript_path? → build context key
   ├── platform-specific env vars?         → build context key
   └── Cursor shell ticket?                → build context key from ticket
       └── None if nothing found

2. If context key found:
   └── Read .trellis/.runtime/sessions/{key}.json
       ├── Has "current_task" field? → return ActiveTask(source_type="session")
       └── No task? → fall through to step 3

3. _resolve_single_session_fallback(repo_root)
   └── List .trellis/.runtime/sessions/*.json
       ├── Exactly 1 file? → read its "current_task"
       │   └── return ActiveTask(source_type="session-fallback")
       ├── 0 files? → return None
       └── ≥2 files? → return None (refuses to guess)

4. Final: return ActiveTask(None, "none", context_key)
```

### Degraded mode (`cmd_start` in `task.py`, lines 95-119):

When `resolve_context_key()` returns `None` during `task.py start`:
- Prints a warning about degraded mode
- Does NOT write a session pointer
- Still flips `task.json` status from `planning` → `in_progress`
- Returns exit code 0 (success)

### `normalize_task_ref()` (active_task.py, lines 100-117):

Normalizes task references for storage:
- Strip whitespace
- Convert absolute paths: keep as-is
- Replace backslashes with forward slashes
- Strip leading `./`
- If starts with `tasks/`, prepend `.trellis/`
- Otherwise return as-is

### `resolve_task_ref()` (active_task.py, lines 120-133):

Resolves a task ref to an absolute path:
- If absolute: return as Path
- If starts with `.trellis/`: join with repo_root
- Otherwise: join with `repo_root/.trellis/tasks/`

---

## 7. Supported Platforms

The system supports these platforms (from `_KNOWN_PLATFORMS`, line 34):

```
claude, codex, cursor, opencode, gemini, droid, qoder, codebuddy, kiro, copilot, pi
```

Platform aliases (`_ENV_PLATFORM_ALIASES`, line 73):
```
claude-code → claude
factory → droid
factory-ai → droid
github-copilot → copilot
```

---

## 8. `set_active_task()` — Write Path

**File**: `active_task.py`, lines 548-574

1. Canonicalize the task ref (normalize + resolve to verify directory exists + make repo-relative)
2. Resolve context key (must exist — returns `None` if not)
3. Read existing session file (or start empty dict)
4. Merge metadata (platform, last_seen_at, session identity fields)
5. Set `current_task` to canonical ref
6. Set `current_run` to `None` if not already present
7. Write back to `.trellis/.runtime/sessions/{context_key}.json`

---

## Caveats / Notes for Rust Port

1. **No `.current_task` file** — the legacy constant exists but is unused. All state is in `.trellis/.runtime/sessions/*.json`.
2. **Session isolation** — each AI window/session gets its own pointer file. The fallback only works with exactly 1 session file.
3. **Cursor shell tickets** have a 30-second TTL and are specific to Cursor's `beforeShellExecution` hook flow.
4. **Path normalization** uses POSIX forward slashes (`/`) even on Windows.
5. **`_sanitize_key`** uses regex `[^A-Za-z0-9._-]+` → `_`, strips leading/trailing `._-`, truncates to 160 chars.
6. **`_hash_value`** uses SHA-256, first 24 hex chars.
7. **JSON I/O** uses `ensure_ascii=False` and UTF-8 encoding.
8. **Stale detection** — `_active_from_ref` checks if the resolved task directory still exists (`is_dir()`).
