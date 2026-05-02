"""
Nocturne Memory Client for Trellis Hooks

This module provides read-only access to Nocturne's SQLite database.
Hooks cannot use MCP tools, so they must read directly from SQLite.

Usage:
    from nocturne_client import NocturneClient

    client = NocturneClient()
    if client.is_available():
        patterns = client.query_patterns("trellis", "patterns/python/%")
"""

from __future__ import annotations

import os
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class NocturneMemory:
    """Represents a memory entry from Nocturne."""

    uri: str
    domain: str
    path: str
    content: str
    priority: int
    disclosure: str | None
    created_at: str | None


class NocturneClient:
    """
    Client for reading Nocturne memories from SQLite.

    This client is designed for Hooks that cannot use MCP tools.
    All operations are read-only and have graceful error handling.
    """

    # Default path for Nocturne database
    DEFAULT_DB_PATH = "~/.nocturne/memory.db"

    # Regex for parsing trellis:// URIs
    _URI_PATTERN = re.compile(r"^([a-zA-Z_][a-zA-Z0-9_]*)://(.*)$")

    def __init__(self, db_path: str | None = None) -> None:
        """
        Initialize the Nocturne client.

        Args:
            db_path: Path to Nocturne SQLite database. If None, uses config or default.
        """
        self._db_path = self._resolve_db_path(db_path)
        self._connection: sqlite3.Connection | None = None

    def _resolve_db_path(self, db_path: str | None) -> str:
        """
        Resolve the database path from parameter, config, or environment.

        Priority:
        1. Explicit db_path parameter
        2. NOCTURNE_DB_PATH environment variable
        3. Config file (.trellis/config/nocturne.yaml)
        4. Default path (~/.nocturne/memory.db)
        """
        if db_path:
            return os.path.expanduser(db_path)

        # Check environment variable
        env_path = os.environ.get("NOCTURNE_DB_PATH")
        if env_path:
            return os.path.expanduser(env_path)

        # Check config file
        config_path = self._get_config_db_path()
        if config_path:
            return os.path.expanduser(config_path)

        # Default
        return os.path.expanduser(self.DEFAULT_DB_PATH)

    def _get_config_db_path(self) -> str | None:
        """Read db_path from nocturne.yaml config if it exists."""
        try:
            config_file = Path(__file__).parent.parent / "config" / "nocturne.yaml"
            if not config_file.exists():
                return None

            import yaml

            with open(config_file, encoding="utf-8") as f:
                config = yaml.safe_load(f)

            if not config or not isinstance(config, dict):
                return None

            db_path = config.get("db_path", "")
            if not db_path:
                return None

            # Expand environment variables in config
            return os.path.expandvars(db_path)

        except Exception:
            return None

    def is_available(self) -> bool:
        """
        Check if Nocturne database is available and accessible.

        Returns:
            True if database exists and is readable, False otherwise.
        """
        try:
            if not self._db_path:
                return False

            db_file = Path(self._db_path)
            if not db_file.exists():
                return False

            # Try to open and query the database
            conn = self._get_connection()
            conn.execute("SELECT 1 FROM memories LIMIT 1")
            return True

        except Exception:
            return False

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create SQLite connection."""
        if self._connection is None:
            self._connection = sqlite3.connect(
                self._db_path,
                timeout=5.0,
                check_same_thread=False,
            )
            # Enable row factory for dict-like access
            self._connection.row_factory = sqlite3.Row
        return self._connection

    def close(self) -> None:
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None

    def __enter__(self) -> NocturneClient:
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()

    @staticmethod
    def parse_nocturne_uri(uri: str) -> tuple[str, str]:
        """
        Parse a Nocturne URI into (domain, path).

        Args:
            uri: URI in format "domain://path" (e.g., "trellis://patterns/python")

        Returns:
            Tuple of (domain, path)

        Raises:
            ValueError: If URI format is invalid

        Examples:
            >>> parse_nocturne_uri("trellis://patterns/python")
            ("trellis", "patterns/python")
            >>> parse_nocturne_uri("core://agent")
            ("core", "agent")
        """
        uri = uri.strip()
        match = NocturneClient._URI_PATTERN.match(uri)

        if not match:
            raise ValueError(
                f"Invalid URI format: '{uri}'. Expected format: 'domain://path'",
            )

        domain = match.group(1).lower()
        path = match.group(2).strip("/")

        return domain, path

    def query_patterns(
        self,
        domain: str,
        prefix: str,
        max_results: int = 50,
    ) -> list[NocturneMemory]:
        """
        Query memories by domain and path prefix using LIKE matching.

        Args:
            domain: The domain/namespace (e.g., "trellis", "core")
            prefix: Path prefix for LIKE query (e.g., "patterns/python/%")
                    Use '%' as wildcard, e.g., "patterns/%" matches any subpath
            max_results: Maximum number of results to return

        Returns:
            List of NocturneMemory objects, sorted by priority ascending

        Examples:
            >>> client.query_patterns("trellis", "patterns/python/%")
            # Returns all memories under trellis://patterns/python/

            >>> client.query_patterns("trellis", "domain/power-systems/%")
            # Returns all memories under trellis://domain/power-systems/
        """
        try:
            conn = self._get_connection()

            # Build the query
            query = """
                SELECT
                    p.domain,
                    p.path,
                    p.priority,
                    p.disclosure,
                    m.content,
                    m.created_at
                FROM paths p
                JOIN memories m ON p.memory_id = m.id
                WHERE p.domain = ?
                  AND p.path LIKE ?
                  AND m.deprecated = 0
                ORDER BY p.priority ASC, p.path ASC
                LIMIT ?
            """

            cursor = conn.execute(query, (domain, prefix, max_results))
            rows = cursor.fetchall()

            results = []
            for row in rows:
                domain_val = row["domain"]
                path_val = row["path"]
                uri = f"{domain_val}://{path_val}"

                results.append(
                    NocturneMemory(
                        uri=uri,
                        domain=domain_val,
                        path=path_val,
                        content=row["content"] or "",
                        priority=row["priority"] or 0,
                        disclosure=row["disclosure"],
                        created_at=row["created_at"],
                    ),
                )

            return results

        except Exception:
            return []

    def query_by_priority(
        self,
        domain: str,
        max_priority: int = 2,
        max_results: int = 50,
    ) -> list[NocturneMemory]:
        """
        Query memories by priority threshold.

        Lower priority numbers = higher importance.
        Returns memories with priority <= max_priority.

        Args:
            domain: The domain/namespace (e.g., "trellis", "core")
            max_priority: Maximum priority value (inclusive)
            max_results: Maximum number of results to return

        Returns:
            List of NocturneMemory objects, sorted by priority ascending

        Examples:
            >>> client.query_by_priority("trellis", max_priority=1)
            # Returns high-priority memories (priority 0 or 1)
        """
        try:
            conn = self._get_connection()

            query = """
                SELECT
                    p.domain,
                    p.path,
                    p.priority,
                    p.disclosure,
                    m.content,
                    m.created_at
                FROM paths p
                JOIN memories m ON p.memory_id = m.id
                WHERE p.domain = ?
                  AND p.priority <= ?
                  AND m.deprecated = 0
                ORDER BY p.priority ASC, p.path ASC
                LIMIT ?
            """

            cursor = conn.execute(query, (domain, max_priority, max_results))
            rows = cursor.fetchall()

            results = []
            for row in rows:
                domain_val = row["domain"]
                path_val = row["path"]
                uri = f"{domain_val}://{path_val}"

                results.append(
                    NocturneMemory(
                        uri=uri,
                        domain=domain_val,
                        path=path_val,
                        content=row["content"] or "",
                        priority=row["priority"] or 0,
                        disclosure=row["disclosure"],
                        created_at=row["created_at"],
                    ),
                )

            return results

        except Exception:
            return []

    def get_memory(self, uri: str) -> NocturneMemory | None:
        """
        Get a single memory by its full URI.

        Args:
            uri: Full URI (e.g., "trellis://patterns/python/error-handling")

        Returns:
            NocturneMemory if found, None otherwise
        """
        try:
            domain, path = self.parse_nocturne_uri(uri)
            conn = self._get_connection()

            query = """
                SELECT
                    p.domain,
                    p.path,
                    p.priority,
                    p.disclosure,
                    m.content,
                    m.created_at
                FROM paths p
                JOIN memories m ON p.memory_id = m.id
                WHERE p.domain = ?
                  AND p.path = ?
                  AND m.deprecated = 0
            """

            cursor = conn.execute(query, (domain, path))
            row = cursor.fetchone()

            if not row:
                return None

            return NocturneMemory(
                uri=uri,
                domain=row["domain"],
                path=row["path"],
                content=row["content"] or "",
                priority=row["priority"] or 0,
                disclosure=row["disclosure"],
                created_at=row["created_at"],
            )

        except Exception:
            return None

    def get_project_memories(
        self,
        project_id: str,
        max_results: int = 50,
    ) -> list[NocturneMemory]:
        """
        Get all memories for a specific project.

        Args:
            project_id: Project identifier (e.g., "topo-reliability")
            max_results: Maximum number of results to return

        Returns:
            List of NocturneMemory objects under trellis://projects/{project_id}/
        """
        prefix = f"projects/{project_id}/%"
        return self.query_patterns("trellis", prefix, max_results)


def get_db_path() -> str | None:
    """
    Get the resolved Nocturne database path.

    Returns:
        Absolute path to Nocturne database, or None if not configured
    """
    try:
        client = NocturneClient()
        return client._db_path  # noqa: SLF001
    except Exception:
        return None


def is_available() -> bool:
    """
    Check if Nocturne database is available.

    Returns:
        True if database exists and is accessible
    """
    try:
        with NocturneClient() as client:
            return client.is_available()
    except Exception:
        return False


def parse_nocturne_uri(uri: str) -> tuple[str, str]:
    """
    Parse a Nocturne URI into (domain, path).

    Args:
        uri: URI in format "domain://path"

    Returns:
        Tuple of (domain, path)

    Raises:
        ValueError: If URI format is invalid
    """
    return NocturneClient.parse_nocturne_uri(uri)
