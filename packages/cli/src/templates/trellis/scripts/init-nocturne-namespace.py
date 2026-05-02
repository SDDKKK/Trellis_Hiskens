#!/usr/bin/env python3
"""
Initialize Nocturne trellis:// Namespace

Creates the trellis:// namespace hierarchy in Nocturne via direct SQLite writes.
This is a one-time setup script, not a Hook.

Usage:
    python3 init-nocturne-namespace.py [--dry-run] [--db-path PATH]

Prerequisites:
    - Nocturne MCP server's VALID_DOMAINS must include "trellis"
    - Nocturne's Memory model must have server_default=text("0") on the
      deprecated column, so external INSERTs that omit it get 0 (not NULL).

Note on external SQLite writes:
    This script writes directly to SQLite. The key compatibility requirement
    is that all columns with ORM-level defaults (e.g. deprecated, created_at)
    must also have SQL-level DEFAULT values (server_default in SQLAlchemy).
    Without server_default, external INSERTs store NULL, and MCP queries
    like `WHERE deprecated = 0` silently exclude NULL rows (SQL three-valued
    logic: NULL = 0 → UNKNOWN → row excluded).

    After running this script, restart the MCP server to pick up new rows.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Namespace structure: nested dict → branch nodes, str values → leaf nodes
# ---------------------------------------------------------------------------
NAMESPACE_STRUCTURE = {
    "patterns": {
        "python": {
            "idioms": "Python idioms and best practices for scientific computing",
            "error-handling": "Error handling patterns in Python",
            "data-processing": "Data processing patterns (polars, pandas)",
            "testing": "Testing patterns and strategies",
            "performance": "Performance optimization patterns",
        },
        "matlab": {
            "vectorization": "MATLAB vectorization patterns",
            "translation": "MATLAB to Python translation patterns",
        },
        "architecture": {
            "layering": "Layered architecture patterns",
            "interfaces": "Interface design patterns",
            "state-management": "State management patterns",
        },
        "workflow": {
            "trellis": "Trellis framework usage patterns",
            "git": "Git workflow patterns",
            "mcp": "MCP tool usage patterns",
        },
    },
    "domain": {
        "power-systems": {
            "reliability": "Power system reliability analysis",
            "topology": "Power network topology analysis",
            "load-flow": "Power flow calculation methods",
        },
        "standards": {
            "ieee-519": "IEEE 519 standard",
            "gb": "Chinese national standards (国标)",
        },
    },
    "tools": {
        "claude-code": {
            "slash-commands": "Claude Code slash command usage",
            "hooks": "Hook development guide",
            "agents": "Agent development guide",
        },
        "mcp": {
            "tool-design": "MCP tool design principles",
            "error-handling": "MCP error handling patterns",
        },
        "testing": {
            "pytest": "Pytest usage and patterns",
            "matlab-unit": "MATLAB unit testing",
        },
    },
    "projects": {
        "topo-reliability": {
            "decisions": "Architecture decisions for Topo-Reliability project",
            "learnings": "Project-specific learnings",
            "patterns": "Project-specific patterns",
        },
    },
}

# ---------------------------------------------------------------------------
# Seed content for key nodes (others get a generated stub)
# ---------------------------------------------------------------------------
INITIAL_CONTENT = {
    "trellis://patterns/python/idioms": """\
# Python Idioms for Scientific Computing

## Core Principles

1. **Type hints everywhere** - Use `from __future__ import annotations` for Python 3.9+
2. **Polars over pandas** - For all new data processing code
3. **Flat is better than nested** - Max 1 level of try-except nesting
4. **Explicit over implicit** - Clear variable names, explicit imports

## Common Patterns

### Result Type for Error Handling
```python
from typing import TypeVar, Generic

T = TypeVar('T')
E = TypeVar('E')

class Result(Generic[T, E]):
    def __init__(self, ok: T | None = None, err: E | None = None):
        self.ok = ok
        self.err = err

    @property
    def is_ok(self) -> bool:
        return self.err is None
```

### Data Processing Pipeline
```python
def process_data(input_path: Path) -> pl.DataFrame:
    return (
        pl.read_csv(input_path)
        .filter(pl.col("status") == "active")
        .with_columns(
            pl.col("value").cast(pl.Float64).alias("value_f64")
        )
    )
```
""",
    "trellis://domain/power-systems/reliability": """\
# Power System Reliability Analysis

## Key Metrics

- **SAIFI**: System Average Interruption Frequency Index
- **SAIDI**: System Average Interruption Duration Index
- **CAIDI**: Customer Average Interruption Duration Index
- **ASAI**: Average Service Availability Index
- **ENS**: Energy Not Supplied

## Calculation Methods

### SAIDI
```
SAIDI = (Sum of interruption durations) / (Total customers served)
```
Units: hours/customer/year

### SAIFI
```
SAIFI = (Total number of customer interruptions) / (Total number of customers served)
```
Units: interruptions/customer/year

## Data Requirements

1. Outage event records (start time, end time, affected customers)
2. Network topology (bus-branch model)
3. Customer count by feeder/region
4. Load data for ENS calculation
""",
    "trellis://tools/claude-code/hooks": """\
# Claude Code Hook Development

## Hook Types

1. **SessionStart**: Runs when Claude Code starts
   - File: `.claude/hooks/session-start.py`
   - Matcher: `"startup"`

2. **PreToolUse**: Runs before a tool is called
   - File: `.claude/hooks/inject-subagent-context.py`
   - Matcher: specific tool names

3. **SubagentStop**: Runs when a subagent stops
   - File: `.claude/hooks/ralph-loop.py`
   - Matcher: `"SubagentStop"`

## Communication Protocol

Hooks communicate via stdin/stdout with JSON:
```python
input_data = json.load(sys.stdin)
output = {"hookSpecificOutput": {...}}
print(json.dumps(output))
```

## Key Constraints

- **No MCP access**: Hooks cannot call MCP tools
- **Read-only SQLite**: Can read Nocturne DB directly
- **Timeout**: Must complete within reasonable time
- **No exceptions**: Must handle errors gracefully
""",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def flatten_namespace(structure: dict, parent_path: str = "") -> list[dict]:
    """Flatten nested namespace dict into ordered list of node definitions.

    Nodes are yielded parent-first so that SQLite inserts respect the
    implicit hierarchy (parent path exists before child path).
    """
    nodes: list[dict] = []
    for name, value in structure.items():
        current_path = f"{parent_path}/{name}" if parent_path else name
        if isinstance(value, dict):
            nodes.append(
                {
                    "uri": f"trellis://{current_path}",
                    "title": name.replace("-", " ").title(),
                    "is_branch": True,
                }
            )
            nodes.extend(flatten_namespace(value, current_path))
        else:
            nodes.append(
                {
                    "uri": f"trellis://{current_path}",
                    "title": name.replace("-", " ").title(),
                    "description": value,
                    "is_branch": False,
                }
            )
    return nodes


def get_nocturne_db_path() -> str | None:
    """Resolve Nocturne database path from env or default location."""
    env_path = os.environ.get("NOCTURNE_DB_PATH")
    if env_path:
        return os.path.expanduser(env_path)
    default_path = os.path.expanduser("~/.nocturne/memory.db")
    if os.path.exists(default_path):
        return default_path
    return None


def load_existing_uris(conn: sqlite3.Connection) -> set[str]:
    """Load existing trellis:// URIs from the database."""
    try:
        rows = conn.execute(
            "SELECT domain, path FROM paths WHERE domain = 'trellis'"
        ).fetchall()
        return {f"{row[0]}://{row[1]}" for row in rows}
    except Exception as e:
        print(f"Warning: Could not load existing URIs: {e}")
        return set()


def create_memory(
    conn: sqlite3.Connection,
    uri: str,
    content: str,
    priority: int,
    disclosure: str | None,
    now: str,
) -> bool:
    """Insert a single memory + path row with proper created_at timestamp."""
    if "://" not in uri:
        return False

    domain, path = uri.split("://", 1)

    # Skip duplicates
    if conn.execute(
        "SELECT 1 FROM paths WHERE domain = ? AND path = ?", (domain, path)
    ).fetchone():
        print(f"  Already exists, skipping: {uri}")
        return True

    try:
        cursor = conn.execute(
            "INSERT INTO memories (content, deprecated, created_at) VALUES (?, 0, ?)",
            (content, now),
        )
        memory_id = cursor.lastrowid
        conn.execute(
            "INSERT INTO paths (domain, path, memory_id, priority, disclosure, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (domain, path, memory_id, priority, disclosure, now),
        )
        print(f"  Created: {uri}")
        return True
    except Exception as e:
        print(f"  Error creating {uri}: {e}")
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Initialize Nocturne trellis:// namespace"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without writing",
    )
    parser.add_argument("--db-path", help="Path to Nocturne SQLite database")
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        default=True,
        help="Skip existing URIs (default)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Nocturne trellis:// Namespace Initialization")
    print("=" * 60)

    db_path = args.db_path or get_nocturne_db_path()
    if not db_path:
        print("Error: No Nocturne database found.")
        print("Set NOCTURNE_DB_PATH or ensure ~/.nocturne/memory.db exists.")
        sys.exit(1)

    if not os.path.exists(db_path):
        print(f"Error: Database not found: {db_path}")
        sys.exit(1)

    print(f"Database: {db_path}")

    conn = sqlite3.connect(db_path)
    existing_uris = load_existing_uris(conn)
    print(f"Existing trellis:// URIs: {len(existing_uris)}")

    nodes = flatten_namespace(NAMESPACE_STRUCTURE)
    print(f"Nodes to create: {len(nodes)}")
    print()

    now = datetime.now(timezone.utc).isoformat()
    created = 0
    skipped = 0
    failed = 0

    for node in nodes:
        uri = node["uri"]

        if args.skip_existing and uri in existing_uris:
            skipped += 1
            continue

        # Resolve content
        content = INITIAL_CONTENT.get(uri, "")
        if not content:
            title = node.get("title", uri)
            description = node.get("description", "")
            content = f"# {title}\n\n{description}\n"

        # Priority: project-specific > top-level > default
        if "projects/topo-reliability" in uri:
            priority = 1
        elif uri.count("/") <= 2:
            priority = 2
        else:
            priority = 5

        if args.dry_run:
            print(f"[DRY RUN] Would create: {uri} (priority={priority})")
            created += 1
        else:
            ok = create_memory(
                conn,
                uri=uri,
                content=content,
                priority=priority,
                disclosure=f"When working with {node.get('title', uri)}",
                now=now,
            )
            if ok:
                created += 1
            else:
                failed += 1

    if not args.dry_run:
        conn.commit()
    conn.close()

    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Created:  {created}")
    print(f"Skipped:  {skipped}")
    print(f"Failed:   {failed}")

    if not args.dry_run and created > 0:
        print()
        print("Note: Nocturne MCP server needs pool_pre_ping=True to see")
        print("these rows without restart. If reads fail, restart the server.")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
