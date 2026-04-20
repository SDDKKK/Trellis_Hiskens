# Background Task Monitoring Guide

> **Purpose**: Supervise a Trellis Multi-Agent Pipeline (`multi_agent/start.py`) background dispatch without flooding your main session with every sub-agent tool call.

## When to Use

- Running `uv run python ./.trellis/scripts/multi_agent/start.py <task-dir>`
- User is asleep / AFK and needs status when they return
- Long-running pipelines (implement 30 min × 6 polls, total 60-120 min typical)

## Architecture: Monitor + Health Watchdog

Two complementary `Monitor` tasks running in parallel, both `persistent: true`:

```
┌─────────────────────────────────────┐
│ Main Monitor (event-driven)         │  phase transitions, errors, FINAL
│ tail -F .agent-log | jq ...         │  → emits on log lines
├─────────────────────────────────────┤
│ Health Watchdog (polling loop)      │  process death, log idle >15min
│ kill -0 <PID> + stat log mtime      │  → emits on silence (watchdog)
└─────────────────────────────────────┘
```

Silence alone is NOT success — dispatch could be hung with no log output. Watchdog catches what Monitor can't.

## Main Monitor: Tight jq Filter

Dispatch's log (`.agent-log`) contains:
- Dispatch's own tool calls (Task spawns, PR bash, Read)
- **Sub-agent tool calls (high volume, low value)** — Edit / Read / Grep from implement/check/etc
- Dispatch and sub-agent text messages
- Hook events, system init, result

### Filtering principles

1. **Dispatch-level only**: `.parent_tool_use_id == null`
   Sub-agent tool calls carry non-null `parent_tool_use_id` — filter them out.
2. **Phase transitions**: `.name == "Task"` → surface `subagent_type`
3. **Pipeline-critical Bash only**: `.name == "Bash" and .input.command | test("create_pr|git commit|git push")`
4. **Keyword-filtered text**: emit dispatch text only when it contains `API Error|Traceback|BLOCKED|NEEDS_CONTEXT|DONE|completed|failed|FAIL`
5. **Always emit** (terminal states):
   - `.type == "result"` — pipeline end with `is_error`, cost, duration
   - `.type == "system" and .subtype == "hook_response" and .exit_code != 0` — hook failures

### Reference filter

```jq
if .type == "result" then
  "[FINAL] is_error=" + (.is_error|tostring) + " reason=" + (.terminal_reason // "?") + " cost=$" + ((.total_cost_usd // 0)|tostring)
elif .type == "assistant" and (.parent_tool_use_id == null) then
  (.message.content[]? |
    if .type == "tool_use" then
      if .name == "Task" then "[PHASE] spawn " + (.input.subagent_type // "?")
      elif .name == "Bash" and ((.input.command // "") | test("create_pr|git commit|git push"; "i")) then
        "[PIPELINE-BASH] " + ((.input.description // "")[0:120])
      else empty end
    elif .type == "text" and (.text | test("API Error|Traceback|BLOCKED|DONE|completed|failed|FAIL"; "i")) then
      "[ALERT] " + (.text[0:240] | gsub("\n"; " | "))
    else empty end
  )
elif .type == "system" and .subtype == "hook_response" and .exit_code != 0 then
  "[HOOK-FAIL] " + (.hook_name // "?") + ": " + ((.stderr // "")[0:150])
else empty end
```

Pipe through `grep --line-buffered -v "^$"` to drop empty emissions.

## Health Watchdog

```bash
LOG=<worktree>/.agent-log
while true; do
  if ! kill -0 <PID> 2>/dev/null; then echo "[HEALTH-DEAD] dispatch died"; break; fi
  NOW=$(date +%s); LAST=$(stat -c %Y "$LOG" 2>/dev/null || echo 0); AGE=$((NOW - LAST))
  if [ $AGE -gt 900 ]; then echo "[HEALTH-IDLE] ${AGE}s idle (PID alive)"; fi
  sleep 300
done
```

- `[HEALTH-DEAD]` on process death → loop exits
- `[HEALTH-IDLE]` every 5 min if log hasn't been updated for ≥15 min
- 300s poll balances responsiveness vs overhead

## Launch Ordering

1. **Launch dispatch**: `start.py <task-dir>` — note the PID from SUCCESS block
2. **Verify first turn survived** (before arming monitors — if API call failed, you get a fresh [FINAL] immediately):
   ```bash
   sleep 15; tail -5 .agent-log | jq -rc 'select(.type=="result") | "is_error=\(.is_error)"'
   ```
   If `is_error=true` appears, abort and diagnose before arming monitors.
3. **Start main Monitor** (tight filter above)
4. **Start health watchdog** (using PID from step 1)

Both with `persistent: true`, `timeout_ms: 3600000` (max).

## Common Gotchas

### 1. Wide filter floods main session (burned context)

A filter that emits all `tool_use` including sub-agent Edit/Read/Grep can produce hundreds of notifications in a 30-min phase. The main session ends up context-starved and the user receives useless noise.

**Mitigation**: Start tight; expand only when a critical event is missed.

### 2. Sub-agent text leaks into Monitor

Sub-agent (implement/check) text messages also appear in dispatch's stream. The `parent_tool_use_id == null` filter is what separates them.

### 3. Registry cleanup between relaunches

After dispatch dies, its PID stays stale in `.trellis/workspace/<dev>/.agents/registry.json`. Always prune before re-launch:

```python
with open(reg) as f: d = json.load(f)
d['agents'] = [a for a in d['agents'] if (os.kill(a['pid'], 0) ... success)]
```

### 4. Log archive before relaunch

`start.py` writes into the existing `.agent-log` (append). To distinguish attempts, `mv .agent-log .agent-log.crashed.$(date +%s)` before relaunch — otherwise the new Monitor sees old error lines.

### 5. Stop Monitors on FINAL

Once `[FINAL]` emits, dispatch has exited. Call `TaskStop <task_id>` on both to free resources. Health watchdog also stops itself on `[HEALTH-DEAD]`.

### 6. `parent_tool_use_id` field lives at top-level

It's a sibling of `type`, `message`, `session_id` in the JSON object — NOT inside `.message`. Easy to get wrong on first pass.

## Related

- `.claude/agents/dispatch.md` — dispatch agent definition (model, timeouts, phase mapping)
- `.trellis/scripts/multi_agent/start.py:432-439` — where `claude -p --agent dispatch` is launched
- `.trellis/scripts/multi_agent/cleanup.py` — full teardown (worktree + branch + registry, not just registry)
- `memory/ccr.md` (auto-memory) — why dispatch needs `model: opus[1m]` in frontmatter for `Any` provider routes
