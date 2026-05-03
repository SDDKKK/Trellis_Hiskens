#!/usr/bin/env python3
"""
Promote Trellis memories to Nocturne long-term memory.

This script parses entries from memory/learnings.md and memory/decisions.md
and promotes them to Nocturne via MCP tools.

Usage:
    ./promote-to-nocturne.py --learning 5          # Promote learning #5
    ./promote-to-nocturne.py --decision 3          # Promote decision #3
    ./promote-to-nocturne.py --list                # Show all entries
    ./promote-to-nocturne.py --learning 5 --auto-uri --priority 3  # Direct mode

Interactive mode (default):
    - Shows the selected entry
    - Prompts for URI, priority, disclosure
    - Calls create_memory via MCP

Direct mode (--auto-uri):
    - Auto-generates URI from entry title
    - Uses provided --priority
    - Skips interactive prompts
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class MemoryEntry:
    """Represents a memory entry from markdown files."""

    index: int
    date: str
    title: str
    content: str
    source_file: str
    category: str | None = None  # For learnings: pattern|gotcha|convention|mistake

    @property
    def suggested_uri(self) -> str:
        """Generate a suggested URI from the title."""
        # Convert title to kebab-case
        # Remove special characters, convert spaces to hyphens
        clean = re.sub(r"[^\w\s-]", "", self.title.lower())
        clean = re.sub(r"[-\s]+", "-", clean).strip("-")

        if self.source_file == "learnings.md":
            # Determine subpath based on category
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

    # Split by H2 headers (## YYYY-MM-DD: Title)
    pattern = r"^##\s+(\d{4}-\d{2}-\d{2}):\s+(.+)$"

    lines = content.split("\n")
    current_entry: dict[str, Any] | None = None
    current_content_lines: list[str] = []

    for line in lines:
        match = re.match(pattern, line)
        if match:
            # Save previous entry if exists
            if current_entry is not None:
                current_entry["content"] = "\n".join(current_content_lines).strip()
                entries.append(MemoryEntry(**current_entry))

            # Start new entry
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
            # Check for category marker
            if line.strip().startswith("**Category**:"):
                category_match = re.search(
                    r"\*\*Category\*\*:\s*\(?(pattern|gotcha|convention|mistake)\)?",
                    line,
                )
                if category_match:
                    current_entry["category"] = category_match.group(1)
            current_content_lines.append(line)

    # Don't forget the last entry
    if current_entry is not None:
        current_entry["content"] = "\n".join(current_content_lines).strip()
        entries.append(MemoryEntry(**current_entry))

    return entries


def parse_decisions_entries(content: str) -> list[MemoryEntry]:
    """Parse entries from decisions.md file."""
    entries = []
    index = 0

    # Split by H2 headers (## YYYY-MM-DD: Decision Title)
    pattern = r"^##\s+(\d{4}-\d{2}-\d{2}):\s+(.+)$"

    lines = content.split("\n")
    current_entry: dict[str, Any] | None = None
    current_content_lines: list[str] = []

    for line in lines:
        match = re.match(pattern, line)
        if match:
            # Save previous entry if exists
            if current_entry is not None:
                current_entry["content"] = "\n".join(current_content_lines).strip()
                entries.append(MemoryEntry(**current_entry))

            # Start new entry
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

    # Don't forget the last entry
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


def format_entry_list(entries: list[MemoryEntry]) -> str:
    """Format entries for display."""
    lines = []
    lines.append(f"{'#':<4} {'Date':<12} {'Title':<50} {'Source':<15}")
    lines.append("-" * 85)

    for entry in entries:
        title = entry.title[:47] + "..." if len(entry.title) > 50 else entry.title
        lines.append(
            f"{entry.index:<4} {entry.date:<12} {title:<50} {entry.source_file:<15}"
        )

    return "\n".join(lines)


def display_entry(entry: MemoryEntry) -> None:
    """Display a single entry in detail."""
    print("\n" + "=" * 80)
    print(f"Entry #{entry.index} from {entry.source_file}")
    print("=" * 80)
    print(f"Date: {entry.date}")
    print(f"Title: {entry.title}")
    if entry.category:
        print(f"Category: {entry.category}")
    print(f"\nSuggested URI: {entry.suggested_uri}")
    print("-" * 80)
    print("Content:")
    print(entry.content[:500] + "..." if len(entry.content) > 500 else entry.content)
    print("=" * 80 + "\n")


def interactive_prompt(entry: MemoryEntry) -> dict[str, Any] | None:
    """Interactively prompt for memory creation parameters."""
    print("\nPromoting to Nocturne...")
    print("Press Ctrl+C to cancel at any time.\n")

    try:
        # URI
        suggested = entry.suggested_uri
        print(f"Suggested URI: {suggested}")
        uri = input(f"URI [{suggested}]: ").strip()
        if not uri:
            uri = suggested

        # Validate URI format
        if "://" not in uri:
            print(f"Error: Invalid URI format: {uri}")
            return None

        # Priority
        default_priority = "2"
        print("\nPriority levels:")
        print("  0 = Critical (always loaded)")
        print("  1 = High (important patterns)")
        print("  2 = Normal (general patterns)")
        print("  3+ = Low (specialized knowledge)")
        priority_str = input(f"Priority [{default_priority}]: ").strip()
        priority = int(priority_str) if priority_str else int(default_priority)

        # Disclosure
        default_disclosure = "when working on related tasks"
        print("\nDisclosure: When should this memory be used?")
        disclosure = input(f"[{default_disclosure}]: ").strip()
        if not disclosure:
            disclosure = default_disclosure

        # Content
        print("\nContent preview (first 200 chars):")
        preview = (
            entry.content[:200] + "..." if len(entry.content) > 200 else entry.content
        )
        print(preview)
        print("\nUse this content? (Y/n): ", end="")
        confirm = input().strip().lower()
        if confirm and confirm not in ("y", "yes"):
            print("Edit content (Ctrl+D to finish):")
            lines = []
            try:
                while True:
                    lines.append(input())
            except EOFError:
                pass
            content = "\n".join(lines)
        else:
            content = entry.content

        # Final confirmation
        print("\n" + "-" * 80)
        print("Summary:")
        print(f"  URI: {uri}")
        print(f"  Priority: {priority}")
        print(f"  Disclosure: {disclosure}")
        print(f"  Content length: {len(content)} chars")
        print("-" * 80)
        print("\nCreate memory? (y/N): ", end="")
        final = input().strip().lower()

        if final not in ("y", "yes"):
            print("Cancelled.")
            return None

        return {
            "uri": uri,
            "content": content,
            "priority": priority,
            "disclosure": disclosure,
        }

    except KeyboardInterrupt:
        print("\n\nCancelled.")
        return None
    except Exception as e:
        print(f"\nError: {e}")
        return None


def create_memory_via_mcp(params: dict[str, Any]) -> bool:
    """Create memory using MCP tool (simulated - actual call requires MCP context)."""
    print("\n" + "=" * 80)
    print("MEMORY CREATION PARAMETERS")
    print("=" * 80)
    print(f"URI: {params['uri']}")
    print(f"Priority: {params['priority']}")
    print(f"Disclosure: {params['disclosure']}")
    print(f"Content:\n{params['content'][:500]}...")
    print("=" * 80)

    print("\nNote: To actually create the memory, use the MCP tool:")
    print("  create_memory(")
    print(f"    uri='{params['uri']}',")
    print("    content='...',")
    print(f"    priority={params['priority']},")
    print(f"    disclosure='{params['disclosure']}'")
    print("  )")

    # In actual implementation, this would call the MCP tool
    # For now, we just output the parameters
    return True


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Promote Trellis memories to Nocturne long-term memory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --list                          # List all entries
  %(prog)s --learning 5                    # Promote learning #5 (interactive)
  %(prog)s --decision 3                    # Promote decision #3 (interactive)
  %(prog)s --learning 5 --auto-uri --priority 3  # Direct mode
        """,
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available entries",
    )
    parser.add_argument(
        "--learning",
        type=int,
        metavar="N",
        help="Promote learning entry #N",
    )
    parser.add_argument(
        "--decision",
        type=int,
        metavar="N",
        help="Promote decision entry #N",
    )
    parser.add_argument(
        "--auto-uri",
        action="store_true",
        help="Auto-generate URI (skip interactive prompt)",
    )
    parser.add_argument(
        "--priority",
        type=int,
        default=2,
        help="Priority level (0=critical, 1=high, 2=normal, 3+=low)",
    )
    parser.add_argument(
        "--disclosure",
        type=str,
        default="when working on related tasks",
        help="When to disclose this memory",
    )

    args = parser.parse_args()

    # Load entries
    learnings = load_memory_file("learnings.md")
    decisions = load_memory_file("decisions.md")

    # List mode
    if args.list:
        print("\nLEARNINGS:")
        if learnings:
            print(format_entry_list(learnings))
        else:
            print("  (no entries)")

        print("\n\nDECISIONS:")
        if decisions:
            print(format_entry_list(decisions))
        else:
            print("  (no entries)")

        return 0

    # Promote learning
    if args.learning:
        entry = next((e for e in learnings if e.index == args.learning), None)
        if not entry:
            print(f"Error: Learning #{args.learning} not found", file=sys.stderr)
            return 1

        display_entry(entry)

        if args.auto_uri:
            # Direct mode
            params = {
                "uri": entry.suggested_uri,
                "content": entry.content,
                "priority": args.priority,
                "disclosure": args.disclosure,
            }
            if create_memory_via_mcp(params):
                print("\n[OK] Memory creation parameters prepared.")
                return 0
            return 1
        else:
            # Interactive mode
            params = interactive_prompt(entry)
            if params:
                if create_memory_via_mcp(params):
                    print("\n[OK] Memory creation parameters prepared.")
                    return 0
            return 1

    # Promote decision
    if args.decision:
        entry = next((e for e in decisions if e.index == args.decision), None)
        if not entry:
            print(f"Error: Decision #{args.decision} not found", file=sys.stderr)
            return 1

        display_entry(entry)

        if args.auto_uri:
            # Direct mode
            params = {
                "uri": entry.suggested_uri,
                "content": entry.content,
                "priority": args.priority,
                "disclosure": args.disclosure,
            }
            if create_memory_via_mcp(params):
                print("\n[OK] Memory creation parameters prepared.")
                return 0
            return 1
        else:
            # Interactive mode
            params = interactive_prompt(entry)
            if params:
                if create_memory_via_mcp(params):
                    print("\n[OK] Memory creation parameters prepared.")
                    return 0
            return 1

    # No action specified
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
