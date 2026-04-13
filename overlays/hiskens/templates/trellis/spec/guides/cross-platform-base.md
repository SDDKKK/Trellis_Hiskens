# Cross-Platform Thinking Guide

> **Base document** -- universal cross-platform patterns. Project-specific extensions (if any) are loaded via `{project}-topo.md` files and appended after this content by the hook.

> **Purpose**: Catch platform-specific issues before they become runtime bugs.
> **Scope**: WSL2 (Linux) ↔ Windows ↔ MATLAB (Windows-native) ↔ Java

## Why This Guide?

This project runs across multiple platform boundaries:

| Component | Runtime Environment | Path Style |
|-----------|-------------------|------------|
| Python scripts | WSL2 (Linux) | `/mnt/e/...` |
| MATLAB | Windows-native | `E:\...` |
| Java (FMEACal) | Windows JVM | `E:\...` |
| SQLite (ledger.db) | Shared file | Both styles |
| Git | WSL2 | `/mnt/e/...` |

**Most cross-platform bugs come from path conversion, encoding, and line endings.**

---

## 1. Path Handling

### WSL ↔ Windows Path Conversion

```python
# Python: Convert WSL path to Windows path
import subprocess

def wsl_to_win(wsl_path: str) -> str:
    """Convert /mnt/e/... to E:\\..."""
    result = subprocess.run(
        ["wslpath", "-w", wsl_path],
        capture_output=True, text=True
    )
    return result.stdout.strip()

def win_to_wsl(win_path: str) -> str:
    """Convert E:\\... to /mnt/e/..."""
    result = subprocess.run(
        ["wslpath", "-u", win_path],
        capture_output=True, text=True
    )
    return result.stdout.strip()
```

### Common Mistakes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Hardcoded `/mnt/e/` prefix | Breaks on different drive letters | Use `wslpath` or config |
| Backslash in Python strings | `\t` becomes tab | Use raw strings `r"E:\path"` or forward slashes |
| MATLAB receiving WSL paths | `FileNotFoundException` | Convert before passing to MATLAB |
| Chinese characters in path | `UnicodeEncodeError` on Windows | Ensure UTF-8 encoding everywhere |

### Decision Rule

> **Python → MATLAB/Java**: Always convert to Windows path before passing.
> **MATLAB/Java → Python**: Always convert to WSL path after receiving.
> **SQLite paths stored in DB**: Use relative paths from project root when possible.

---

## 2. File Encoding

### UTF-8 Everywhere Rule

```python
# Always specify encoding explicitly
with open(filepath, "r", encoding="utf-8") as f:
    data = f.read()

# NEVER rely on system default encoding
# Bad: open(filepath)  # Uses locale encoding, varies by platform
```

### MATLAB Encoding

```matlab
% Read UTF-8 file in MATLAB
fid = fopen(filepath, 'r', 'n', 'UTF-8');
content = fread(fid, '*char')';
fclose(fid);

% Write UTF-8
fid = fopen(filepath, 'w', 'n', 'UTF-8');
fprintf(fid, '%s', content);
fclose(fid);
```

### Java Encoding

```java
// Always specify charset
BufferedReader reader = new BufferedReader(
    new InputStreamReader(new FileInputStream(file), StandardCharsets.UTF_8)
);
```

### Windows Console UTF-8

```python
# At script entry point (already in inject-subagent-context.py)
import sys
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
```

---

## 3. Line Endings

### Git Configuration

```bash
# .gitattributes (project root)
*.py    text eol=lf
*.m     text eol=crlf    # MATLAB expects CRLF on Windows
*.java  text eol=lf
*.md    text eol=lf
*.json  text eol=lf
*.csv   text eol=crlf    # Excel expects CRLF
```

### When Line Endings Matter

| Scenario | Risk | Mitigation |
|----------|------|------------|
| Python reading MATLAB-generated CSV | `\r\n` in field values | Use `newline=""` in `open()` |
| Shell scripts from Windows | `\r` causes `/bin/bash^M: bad interpreter` | Ensure LF in `.gitattributes` |
| SQLite text fields | Mixed endings in stored data | Normalize on write |

---

## 4. Environment Variables

### WSL ↔ Windows Env Isolation

WSL2 and Windows have separate environment variable spaces:

```bash
# WSL: Set for Python scripts
export DB_PATH="/path/to/your/project/data/database.db"

# Windows: Set for MATLAB/Java (PowerShell)
$env:DB_PATH = "X:\path\to\your\project\data\database.db"
```

### Proxy Variables

```python
# Proxy env vars must be set in the correct environment
# WSL Python: reads from WSL env
# MATLAB/Java: reads from Windows env
# start.py already handles this for multi-agent pipeline
```

---

## 5. Command Availability

### Tool Availability Matrix

| Tool | WSL2 | Windows | Notes |
|------|------|---------|-------|
| `python3` / `uv` | Yes | Maybe | Use `uv run` in WSL |
| `matlab` | No | Yes | Call via `matlab -batch` from WSL |
| `java` / `mvn` | Maybe | Yes | FMEACal runs on Windows JVM |
| `git` | Yes | Yes | Use WSL git for consistency |
| `ruff` | Yes | Maybe | `uv run ruff` in WSL |
| `pytest` | Yes | Maybe | `uv run pytest` in WSL |
| `sqlite3` | Yes | Maybe | WSL version preferred |

### Calling MATLAB from WSL Python

```python
import subprocess

def run_matlab_script(script_name: str, args: list[str] = None):
    """Run MATLAB script from WSL via Windows MATLAB."""
    matlab_cmd = f"cd('{win_project_root}'); {script_name}"
    if args:
        matlab_cmd += f"({', '.join(args)})"

    # Use matlab.exe (Windows binary accessible from WSL)
    result = subprocess.run(
        ["matlab.exe", "-batch", matlab_cmd],
        capture_output=True, text=True
    )
    return result
```

---

## 6. SQLite Cross-Platform Access

### Concurrent Access Warning

SQLite on network/shared filesystems (like `/mnt/e/` which is NTFS via WSL) has limitations:

```python
# Use WAL mode for better concurrent read performance
import sqlite3
conn = sqlite3.connect(db_path)
conn.execute("PRAGMA journal_mode=WAL")

# But beware: WAL on NTFS-over-WSL can have issues
# For write-heavy operations, copy to WSL-local first:
# cp /mnt/e/.../ledger.db /tmp/ledger.db
# ... process ...
# cp /tmp/ledger.db /mnt/e/.../ledger.db
```

### NULL Handling Across Languages

> **Gotcha**: MATLAB `fetch()` crashes on NULL numeric columns. Java handles NULL differently from Python.

| Language | NULL behavior | Mitigation |
|----------|--------------|------------|
| Python | `None` | `if val is not None` |
| MATLAB | Crashes on numeric NULL | `COALESCE(col, -1)` in SQL |
| Java | `ResultSet.wasNull()` | Check after `getInt()`/`getDouble()` |

See also: [Cross-Layer Thinking Guide](./cross-layer-thinking-guide.md) for data flow details.

---

## Python Command Detection

Different platforms use `python3` (Linux/macOS) vs `python` (Windows). Always use `sys.executable` for subprocess calls:

```python
import sys
import subprocess

# GOOD - Use current interpreter
subprocess.run([sys.executable, "other_script.py"])  # Always correct
# NOT: subprocess.run(["python3", "other_script.py"])  # Fails on some Windows
```

---

## Cross-Platform Command Alternatives

Some Unix commands don't exist on Windows. Use Python stdlib alternatives:

| Unix Command | Python Alternative |
|---|---|
| `tail -f` | `open() + seek + read in loop` |
| `grep -r` | `pathlib.Path.rglob() + re` |
| `find` | `pathlib.Path.glob()` |
| `wc -l` | `len(path.read_text().splitlines())` |

---

## Defensive Encoding

When reading files that might have mixed encodings, use `errors="replace"`:

```python
content = path.read_text(encoding="utf-8", errors="replace")
```

For git commands, force UTF-8 output:

```python
git_args = ["git", "-c", "i18n.logOutputEncoding=UTF-8"] + args
```

---

## Common Cross-Platform Mistakes

1. **Hardcoded `python3`** — Use `sys.executable` instead
2. **Hardcoded `/` path separator** — Use `pathlib.Path` or `os.path.join`
3. **Assuming Unix commands exist** — Check availability or use Python stdlib
4. **Not specifying encoding** — Always pass `encoding="utf-8"` to file operations
5. **Not handling CRLF** — Use `newline=""` when precise line ending control is needed

---

## Quick Checklist

Before any cross-platform code:

- [ ] Paths converted correctly for target platform?
- [ ] File encoding explicitly set to UTF-8?
- [ ] Line endings appropriate for target tool?
- [ ] Environment variables set in correct environment (WSL vs Windows)?
- [ ] SQLite NULL values handled for all three languages?
- [ ] Chinese characters in paths/data handled correctly?
- [ ] `wslpath` used instead of hardcoded path prefixes?
