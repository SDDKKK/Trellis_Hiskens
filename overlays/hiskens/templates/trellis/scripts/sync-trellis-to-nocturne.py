#!/usr/bin/env python3
"""
Sync Trellis memory files to Nocturne long-term memory.

This script batch-syncs all entries from memory/*.md files to Nocturne.
It checks for existing memories and can optionally force overwrite.

Usage:
    ./sync-trellis-to-nocturne.py --dry-run     # Preview what would be synced
    ./sync-trellis-to-nocturne.py               # Sync all new entries
    ./sync-trellis-to-nocturne.py --force       # Overwrite existing entries
    ./sync-trellis-to-nocturne.py --source learnings.md  # Sync only learnings
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Import nocturne_client for reading existing memories
try:
    from nocturne_client import NocturneClient
except ImportError:
    NocturneClient = None  # type: ignore[misc,assignment]


@dataclass
class MemoryEntry:
    """Represents a memory entry from markdown files."""

    index: int
    date: str
    title: str
    content: str
    source_file: str
    category: str | None = None

    @property
    def suggested_uri(self) -> str:
        """Generate a suggested URI from the title."""
        # Convert title to kebab-case
        clean = re.sub(r"[^\w\s-]", "", self.title.lower())
        clean = re.sub(r"[-\s]+", "-", clean).strip("-")

        if self.source_file == "learnings.md":
            if self.category == "pattern":
                return f"trellis://patterns/project/{clean}"
            elif self.category == "gotcha":
                return f"trellis://patterns/bug-prevention/{clean}"
            else:
                return f"trellis://projects/topo-reliability/learnings/{clean}"
        else:  # decisions.md
            return f"trellis://projects/topo-reliability/decisions/{clean}"


def parse_learnings_entries(content: str) -> list[MemoryEntry]:
    """Parse entries from learnings.md file."""
    entries = []
    index = 0
    pattern = r"^##\s+(\d{4}-\d{2}-\d{2}):\s+(.+)$"

    lines = content.split("\n")
    current_entry: dict[str, Any] | None = None
    current_content_lines: list[str] = []

    for line in lines:
        match = re.match(pattern, line)
        if match:
            if current_entry is not None:
                current_entry["content"] = "\n".join(current_content_lines).strip()
                entries.append(MemoryEntry(**current_entry))

            index += 1
            date = match.group(1)
            title = match.group(2).strip()

            current_entry = {
                "index": index,
                "date": date,
                "title": title,
                "content": "",
                "source_file": "learnings.md",
                "category": None,
            }
            current_content_lines = []
        elif current_entry is not None:
            if line.strip().startswith("**Category**:"):
                category_match = re.search(
                    r"\*\*Category\*\*:\s*\(?(pattern|gotcha|convention|mistake)\)?",
                    line,
                )
                if category_match:
                    current_entry["category"] = category_match.group(1)
            current_content_lines.append(line)

    if current_entry is not None:
        current_entry["content"] = "\n".join(current_content_lines).strip()
        entries.append(MemoryEntry(**current_entry))

    return entries


def parse_decisions_entries(content: str) -> list[MemoryEntry]:
    """Parse entries from decisions.md file."""
    entries = []
    index = 0
    pattern = r"^##\s+(\d{4}-\d{2}-\d{2}):\s+(.+)$"

    lines = content.split("\n")
    current_entry: dict[str, Any] | None = None
    current_content_lines: list[str] = []

    for line in lines:
        match = re.match(pattern, line)
        if match:
            if current_entry is not None:
                current_entry["content"] = "\n".join(current_content_lines).strip()
                entries.append(MemoryEntry(**current_entry))

            index += 1
            date = match.group(1)
            title = match.group(2).strip()

            current_entry = {
                "index": index,
                "date": date,
                "title": title,
                "content": "",
                "source_file": "decisions.md",
            }
            current_content_lines = []
        elif current_entry is not None:
            current_content_lines.append(line)

    if current_entry is not None:
        current_entry["content"] = "\n".join(current_content_lines).strip()
        entries.append(MemoryEntry(**current_entry))

    return entries


def load_memory_file(filename: str) -> list[MemoryEntry]:
    """Load and parse a memory file."""
    repo_root = Path(__file__).parent.parent.parent
    memory_dir = repo_root / ".trellis" / "memory"
    file_path = memory_dir / filename

    if not file_path.exists():
        return []

    content = file_path.read_text(encoding="utf-8")

    if filename == "learnings.md":
        return parse_learnings_entries(content)
    elif filename == "decisions.md":
        return parse_decisions_entries(content)
    else:
        return []


def check_existing_memory(uri: str) -> bool:
    """Check if a memory already exists in Nocturne."""
    if NocturneClient is None:
        return False

    try:
        with NocturneClient() as client:
            if not client.is_available():
                return False
            existing = client.get_memory(uri)
            return existing is not None
    except Exception:
        return False


def format_sync_plan(entries: list[MemoryEntry], force: bool = False) -> str:
    """Format a sync plan showing what would be synced."""
    lines = []
    lines.append(f"{'#':<4} {'Source':<15} {'URI':<60} {'Action':<15}")
    lines.append("-" * 95)

    for entry in entries:
        uri = entry.suggested_uri
        exists = check_existing_memory(uri)

        if exists and not force:
            action = "SKIP (exists)"
        elif exists and force:
            action = "UPDATE (force)"
        else:
            action = "CREATE"

        uri_display = uri[:57] + "..." if len(uri) > 60 else uri
        source = entry.source_file.replace(".md", "")
        lines.append(f"{entry.index:<4} {source:<15} {uri_display:<60} {action:<15}")

    return "\n".join(lines)


def create_memory_params(entry: MemoryEntry) -> dict[str, Any]:
    """Create parameters for memory creation."""
    # Determine priority based on source and category
    if entry.source_file == "decisions.md":
        priority = 1  # Decisions are high priority
    elif entry.category == "pattern":
        priority = 2  # Patterns are normal priority
    elif entry.category == "gotcha":
        priority = 1  # Gotchas are high priority
    else:
        priority = 2  # Default priority

    # Determine disclosure based on category
    if entry.category == "pattern":
        disclosure = "when implementing similar functionality"
    elif entry.category == "gotcha":
        disclosure = "when encountering similar issues"
    elif entry.category == "convention":
        disclosure = "when establishing coding conventions"
    elif entry.category == "mistake":
        disclosure = "when avoiding common mistakes"
    else:
        disclosure = "when working on related tasks"

    return {
        "uri": entry.suggested_uri,
        "content": f"# {entry.title}\n\n**Date**: {entry.date}\n\n{entry.content}",
        "priority": priority,
        "disclosure": disclosure,
    }


def sync_entries(
    entries: list[MemoryEntry],
    dry_run: bool = False,
    force: bool = False,
) -> tuple[int, int, int]:
    """
    Sync entries to Nocturne.

    Returns:
        Tuple of (created, updated, skipped) counts
    """
    created = 0
    updated = 0
    skipped = 0

    for entry in entries:
        uri = entry.suggested_uri
        exists = check_existing_memory(uri)

        if exists and not force:
            print(f"  SKIP: {uri} (already exists)")
            skipped += 1
            continue

        params = create_memory_params(entry)

        if dry_run:
            action = "WOULD UPDATE" if exists else "WOULD CREATE"
            print(f"  {action}: {uri}")
            if exists:
                updated += 1
            else:
                created += 1
            continue

        # In actual implementation, this would call the MCP tool
        # For now, we just output the action
        if exists:
            print(f"  UPDATE: {uri}")
            updated += 1
        else:
            print(f"  CREATE: {uri}")
            created += 1

        # Print the parameters that would be used
        print(f"    Priority: {params['priority']}")
        print(f"    Disclosure: {params['disclosure']}")
        print(f"    Content length: {len(params['content'])} chars")

    return created, updated, skipped


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Sync Trellis memory files to Nocturne long-term memory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --dry-run                    # Preview what would be synced
  %(prog)s                              # Sync all new entries
  %(prog)s --force                      # Overwrite existing entries
  %(prog)s --source learnings.md        # Sync only learnings
  %(prog)s --source decisions.md        # Sync only decisions
        """,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be synced without making changes",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing memories in Nocturne",
    )
    parser.add_argument(
        "--source",
        choices=["learnings.md", "decisions.md", "all"],
        default="all",
        help="Which source file to sync (default: all)",
    )

    args = parser.parse_args()

    # Load entries
    entries: list[MemoryEntry] = []

    if args.source in ("learnings.md", "all"):
        learnings = load_memory_file("learnings.md")
        entries.extend(learnings)
        print(f"Loaded {len(learnings)} entries from learnings.md")

    if args.source in ("decisions.md", "all"):
        decisions = load_memory_file("decisions.md")
        entries.extend(decisions)
        print(f"Loaded {len(decisions)} entries from decisions.md")

    if not entries:
        print("No entries found to sync.")
        return 0

    print(f"\nTotal entries to process: {len(entries)}")

    # Check Nocturne availability
    if NocturneClient is not None:
        try:
            with NocturneClient() as client:
                if client.is_available():
                    print("Nocturne database: Available")
                else:
                    print("Nocturne database: Not available (will simulate)")
        except Exception:
            print("Nocturne database: Error checking availability")
    else:
        print("Nocturne client: Not available (will simulate)")

    # Show sync plan
    print("\n" + "=" * 95)
    print("SYNC PLAN")
    print("=" * 95)
    print(format_sync_plan(entries, args.force))
    print("=" * 95)

    if args.dry_run:
        print("\n[DRY RUN] No changes made.")
        print("Run without --dry-run to perform the sync.")
        return 0

    # Confirm before proceeding
    if not args.dry_run:
        print("\nProceed with sync? (y/N): ", end="")
        try:
            confirm = input().strip().lower()
            if confirm not in ("y", "yes"):
                print("Cancelled.")
                return 0
        except (KeyboardInterrupt, EOFError):
            print("\nCancelled.")
            return 0

    # Perform sync
    print("\n" + "=" * 95)
    print("SYNCING TO NOCTURNE")
    print("=" * 95)

    created, updated, skipped = sync_entries(entries, args.dry_run, args.force)

    print("\n" + "=" * 95)
    print("SYNC SUMMARY")
    print("=" * 95)
    print(f"  Created: {created}")
    print(f"  Updated: {updated}")
    print(f"  Skipped: {skipped}")
    print(f"  Total:   {created + updated + skipped}")
    print("=" * 95)

    if created > 0 or updated > 0:
        print("\nNote: To actually create/update memories, use the MCP tool:")
        print("  create_memory(uri=..., content=..., priority=..., disclosure=...)")
        print(
            "\nOr use promote-to-nocturne.py for individual entries with full MCP integration."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
