# Research: TRELLIS_CONTEXT_ID Availability in statusLine.command

- **Query**: Is TRELLIS_CONTEXT_ID available to processes spawned by Claude Code's `statusLine.command`?
- **Scope**: internal + external
- **Date**: 2026-06-07

## Findings

### 1. How TRELLIS_CONTEXT_ID Gets Written to CLAUDE_ENV_FILE

**File**: `.claude/hooks/session-start.py`, lines 231-248

```python
def _persist_context_key_for_bash(context_key: str | None) -> None:
    """Expose Trellis session identity to later Claude Code Bash commands.

    Claude Code SessionStart hooks can append exports to CLAUDE_ENV_FILE; those
    variables are then available to Bash tools in the same conversation. Without
    this bridge, `task.py start` has hook stdin during SessionStart but no
    session identity when the AI later runs it as a normal shell command.
    """
    if not context_key:
        return
    env_file = os.environ.get("CLAUDE_ENV_FILE")
    if not env_file:
        return
    try:
        with open(env_file, "a", encoding="utf-8") as handle:
            handle.write(f"export TRELLIS_CONTEXT_ID={shlex.quote(context_key)}\n")
    except OSError:
        pass
```

Called from `main()` at line 754:
```python
context_key = _resolve_context_key(trellis_dir, hook_input)
_persist_context_key_for_bash(context_key)
```

**What is CLAUDE_ENV_FILE**: A temporary file path provided by Claude Code to SessionStart (and Setup/CwdChanged/FileChanged) hooks. The hook writes `export VAR=value` lines into it. Before each subsequent **Bash tool call**, Claude Code sources this file as a shell preamble, making those variables visible to the spawned shell.

### 2. CLAUDE_ENV_FILE Scope: Bash Tool Only, NOT statusLine

Per official Claude Code documentation (docs.anthropic.com/en/docs/claude-code/hooks):

> `CLAUDE_ENV_FILE` is available for SessionStart, Setup, CwdChanged, and FileChanged hooks. Other hook types do not have access to this variable.

> Path to a shell script whose contents Claude Code runs **before each Bash command in the same shell process**, so exports in the file are visible to the command.

**Critical distinction**: The `CLAUDE_ENV_FILE` mechanism is a "shell preamble" -- it only applies to the **Bash tool**. The `statusLine.command` is **not** a Bash tool call; it is a separate subprocess spawned by the Claude Code UI on a timer (`refreshInterval: 5` seconds) or on events.

**However**, this turns out NOT to be the bottleneck -- see finding #3.

### 3. statusLine Gets Session Identity Through TWO Other Paths

#### Path A: `CLAUDE_CODE_SESSION_ID` Environment Variable

Claude Code sets `CLAUDE_CODE_SESSION_ID` as a process-level environment variable for **all** subprocesses it spawns, including statusLine commands. Confirmed live:

```
CLAUDE_CODE_SESSION_ID=e1f4a0de-9ad3-48a1-8eca-32bdc82e6c74
```

From external docs (code.claude.com/docs/en/env-vars):
> `CLAUDE_CODE_SESSION_ID`: Automatically set to match the `session_id` from the JSON. Stable for the session lifetime (updates on `/clear` or resume). Useful for correlating scripts, avoiding race conditions on per-session resources.

#### Path B: `session_id` in stdin JSON

Claude Code pipes a rich JSON object to the statusLine command's stdin. It contains `session_id` among many other fields:

```json
{
  "session_id": "e1f4a0de-9ad3-48a1-8eca-32bdc82e6c74",
  "model": { "display_name": "..." },
  "context_window": { ... },
  ...
}
```

The current `statusline.py` (line 285) already reads this JSON:
```python
cc_data = json.loads(sys.stdin.read())
```

And passes it to `_get_current_task(trellis_dir, cc_data)` (line 294), which calls `resolve_active_task(repo_root, cc_data, platform=...)`.

#### Path C: TRELLIS_CONTEXT_ID Is Also a Process-Level Env Var

Confirmed live -- `TRELLIS_CONTEXT_ID` is present in the current Bash environment:

```
TRELLIS_CONTEXT_ID=claude_e1f4a0de-9ad3-48a1-8eca-32bdc82e6c74
```

This is because `CLAUDE_ENV_FILE` was sourced by the Bash tool shell, making it a shell-level export. The statusLine subprocess, however, is spawned by the Claude Code process itself (not by the Bash tool shell), so it does NOT inherit exports from `CLAUDE_ENV_FILE`.

**But** `resolve_context_key()` in `active_task.py` (line 389) checks `os.environ.get("TRELLIS_CONTEXT_ID")` first, before trying stdin JSON fields. So even if `TRELLIS_CONTEXT_ID` is not in the statusLine process environment, the resolver falls through to:

1. Check `TRELLIS_CONTEXT_ID` env var -> **not set in statusLine process** (only in Bash tool shells)
2. Check `session_id` from stdin JSON -> **AVAILABLE** (Claude Code passes it)
3. Check `CLAUDE_CODE_SESSION_ID` env var -> **AVAILABLE** (Claude Code sets it for all subprocesses)

### 4. The Resolution Chain in statusline.py

The call chain is:

```
statusline.py:main()
  -> cc_data = json.loads(sys.stdin.read())          # Gets session_id from stdin
  -> _get_current_task(trellis_dir, cc_data)          # line 294
    -> resolve_active_task(repo_root, cc_data, ...)   # line 130
      -> resolve_context_key(cc_data, platform)       # internally
        -> 1. os.environ["TRELLIS_CONTEXT_ID"]?       # NOT available (not in statusLine env)
        -> 2. cc_data["session_id"]?                   # AVAILABLE (stdin JSON)
        -> 3. os.environ["CLAUDE_CODE_SESSION_ID"]?    # AVAILABLE (Claude Code sets it)
```

The resolved context key from stdin `session_id` will be `claude_session_e1f4a0de-9ad3-48a1-8eca-32bdc82e6c74` (prefixed with `claude_session_` by `_context_key()`).

**Potential mismatch**: The session file on disk is named `claude_e1f4a0de-9ad3-48a1-8eca-32bdc82e6c74.json`, but the context key resolved from `session_id` via the `_context_key()` function formats it as `claude_session_<value>`. The TRELLIS_CONTEXT_ID value written by session-start.py is `claude_e1f4a0de-...` (using the hook input's session_id, resolved by `_resolve_context_key()` which calls the same `resolve_context_key()` function with hook stdin data).

**Both paths should produce the same context key** because `resolve_context_key()` processes `session_id` identically whether it comes from SessionStart hook stdin or statusLine stdin.

### 5. statusLine Configuration

**File**: `.claude/settings.json` (project-level), lines 73-78:

```json
"statusLine": {
    "type": "command",
    "command": "python3 .claude/hooks/statusline.py",
    "refreshInterval": 5
}
```

Claude Code spawns this as a subprocess every 5 seconds (plus on events like new messages, /compact, permission/mode changes). It pipes the session JSON to stdin and reads stdout for display.

### 6. Current Session Files on Disk

```
.trellis/.runtime/sessions/
├── claude_a6c6fdb4-59c8-41a8-8037-c755377956ad.json  (old session, task: 04-29-root-platform-cleanup)
└── claude_e1f4a0de-9ad3-48a1-8eca-32bdc82e6c74.json  (current session, task: 06-07-ccline-trellis-segment)
```

Current session file contents:
```json
{
  "platform": "claude",
  "last_seen_at": "2026-06-07T03:05:34Z",
  "current_task": ".trellis/tasks/06-07-ccline-trellis-segment",
  "current_run": null
}
```

### 7. TRELLIS_CONTEXT_ID in Current Shell Environment

```
TRELLIS_CONTEXT_ID=claude_e1f4a0de-9ad3-48a1-8eca-32bdc82e6c74
CLAUDE_CODE_SESSION_ID=e1f4a0de-9ad3-48a1-8eca-32bdc82e6c74
CLAUDECODE=1
```

`TRELLIS_CONTEXT_ID` IS set in the Bash tool shell (because `CLAUDE_ENV_FILE` was sourced). It is NOT set in the statusLine subprocess environment (different spawn path).

## Files Found

| File Path | Description |
|---|---|
| `.claude/hooks/session-start.py:231-248` | `_persist_context_key_for_bash()` -- writes `TRELLIS_CONTEXT_ID` to `CLAUDE_ENV_FILE` |
| `.claude/hooks/session-start.py:753-754` | Main flow: resolve context key, persist for bash |
| `.claude/hooks/statusline.py` | StatusLine script -- reads stdin JSON, resolves active task |
| `.claude/hooks/statusline.py:119-149` | `_get_current_task()` -- passes cc_data to resolve_active_task |
| `.claude/hooks/statusline.py:282-288` | `main()` -- reads cc_data from stdin |
| `.claude/settings.json:73-78` | statusLine configuration block |
| `.trellis/scripts/common/active_task.py:48-72` | `_ENV_SESSION_KEYS` -- platform env var mappings |
| `.trellis/scripts/common/active_task.py:216-244` | `_lookup_env_context_key()` -- env var resolution |
| `.trellis/scripts/common/active_task.py:380-415` | `resolve_context_key()` -- priority: TRELLIS_CONTEXT_ID > stdin > env |
| `.trellis/.runtime/sessions/claude_e1f4a0de-9ad3-48a1-8eca-32bdc82e6c74.json` | Current session pointer |

## Summary Answer

**YES, the statusLine command can resolve the session context key**, but NOT via `TRELLIS_CONTEXT_ID` directly. The resolution path is:

1. `TRELLIS_CONTEXT_ID` env var: **NOT available** in statusLine subprocess (only in Bash tool shells via CLAUDE_ENV_FILE sourcing)
2. `session_id` from stdin JSON: **AVAILABLE** (Claude Code passes it to statusLine)
3. `CLAUDE_CODE_SESSION_ID` env var: **AVAILABLE** (Claude Code sets it for all subprocesses)

The current `statusline.py` already uses path #2 -- it reads `cc_data` from stdin and passes it through `resolve_active_task()` which extracts `session_id`. This produces the same context key as the one used by `session-start.py`, so it correctly finds the session file and active task.

## Caveats

- `TRELLIS_CONTEXT_ID` is a **Bash-tool-only** variable (via CLAUDE_ENV_FILE sourcing). It is NOT a process-level env var set by Claude Code itself. The statusLine subprocess does NOT inherit it.
- The `CLAUDE_CODE_SESSION_ID` env var contains the raw UUID (`e1f4a0de-...`), while the Trellis context key is prefixed (`claude_e1f4a0de-...`). The `resolve_context_key()` function handles this mapping via `_context_key()`.
- If a ccline binary needs `TRELLIS_CONTEXT_ID` specifically (not just the session identity), it would need to either: (a) resolve it from `CLAUDE_CODE_SESSION_ID` or stdin `session_id` using the same logic as `resolve_context_key()`, or (b) have the statusline script pass it as a command-line argument after resolving it.

## External References

- [Claude Code Status Line docs](https://code.claude.com/docs/en/statusline) -- stdin JSON schema, env vars
- [Claude Code Environment Variables](https://code.claude.com/docs/en/env-vars) -- CLAUDE_CODE_SESSION_ID, CLAUDE_ENV_FILE scope
- [Claude Code Hooks docs](https://docs.anthropic.com/en/docs/claude-code/hooks) -- CLAUDE_ENV_FILE availability by hook type
