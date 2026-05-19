"""MCP server core. Wires SQLite tools into FastMCP."""
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP


DESTRUCTIVE_KEYWORDS = re.compile(
    r"\b(DROP\s+(TABLE|DATABASE|INDEX|VIEW|TRIGGER)|TRUNCATE|"
    r"ATTACH\s+DATABASE|DETACH\s+DATABASE|"
    r"PRAGMA\s+writable_schema|VACUUM)\b",
    re.IGNORECASE,
)

READ_KEYWORDS = re.compile(r"^\s*(SELECT|WITH|PRAGMA\s+(table_info|table_list|index_list))\b", re.IGNORECASE)


class SafetyError(RuntimeError):
    """Raised when a SQL statement is blocked by the safety layer."""


def _check_destructive(sql: str, unsafe: bool) -> None:
    if unsafe:
        return
    match = DESTRUCTIVE_KEYWORDS.search(sql)
    if match:
        raise SafetyError(
            f"Refused: destructive operation detected ({match.group(0).upper()}). "
            f"Re-run with --unsafe if you really mean it."
        )


def _check_read_only(sql: str) -> None:
    if not READ_KEYWORDS.match(sql):
        raise SafetyError(
            "Refused: query tool accepts SELECT / WITH / PRAGMA only. "
            "For writes, use execute_write (requires --allow-writes)."
        )


def _connect(db_path: str) -> sqlite3.Connection:
    path = Path(db_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Database file does not exist: {path}")
    conn = sqlite3.connect(path, isolation_level=None)  # autocommit mode
    conn.row_factory = sqlite3.Row
    return conn


def _rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def build_server(db_path: str, allow_writes: bool, unsafe: bool) -> FastMCP:
    """Construct a configured FastMCP server bound to a specific SQLite file."""
    mcp = FastMCP(
        name="sqlite-server",
        instructions=(
            f"This server exposes SQLite tools for the database at {db_path}. "
            f"Writes are {'enabled' if allow_writes else 'disabled'}. "
            f"{'UNSAFE mode: destructive ops allowed.' if unsafe else 'Destructive ops blocked.'}"
        ),
    )

    def audit(action: str, sql: str) -> None:
        print(f"[mcp-sqlite-server] {action}: {sql[:200]}", file=sys.stderr, flush=True)

    @mcp.tool()
    def list_tables() -> list[str]:
        """List user tables in the database (excludes sqlite_* internal tables)."""
        with _connect(db_path) as conn:
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
            return [row["name"] for row in cur.fetchall()]

    @mcp.tool()
    def get_schema(table: str) -> str:
        """Return the CREATE TABLE statement for a given table."""
        with _connect(db_path) as conn:
            cur = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            )
            row = cur.fetchone()
            if row is None:
                return f"Table '{table}' not found."
            return row["sql"] or f"-- No DDL stored for {table}"

    @mcp.tool()
    def query(sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
        """Run a read-only query (SELECT / WITH / PRAGMA table_info etc.).

        Args:
            sql: SQL statement. Must start with SELECT, WITH, or PRAGMA table_info/table_list/index_list.
            params: Positional parameters for ?-placeholders. Always use parameter binding, never string interpolation.
        """
        _check_read_only(sql)
        _check_destructive(sql, unsafe)
        audit("query", sql)
        with _connect(db_path) as conn:
            cur = conn.execute(sql, tuple(params or ()))
            return _rows_to_dicts(cur.fetchall())

    @mcp.tool()
    def database_stats() -> dict[str, Any]:
        """Return per-table row counts and the database file size in bytes."""
        stats: dict[str, Any] = {"file_path": str(Path(db_path).resolve())}
        try:
            stats["file_size_bytes"] = Path(db_path).stat().st_size
        except OSError:
            stats["file_size_bytes"] = None
        with _connect(db_path) as conn:
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
            tables = [row["name"] for row in cur.fetchall()]
            counts: dict[str, int] = {}
            for table in tables:
                # Identifier escaped via double quotes (SQL standard)
                safe_table = '"' + table.replace('"', '""') + '"'
                cur = conn.execute(f"SELECT COUNT(*) AS n FROM {safe_table}")
                counts[table] = cur.fetchone()["n"]
            stats["row_counts"] = counts
        return stats

    if allow_writes:
        @mcp.tool()
        def execute_write(sql: str, params: list[Any] | None = None) -> dict[str, Any]:
            """Execute INSERT / UPDATE / DELETE with parameter binding.

            Returns rowcount and lastrowid. Destructive operations (DROP, TRUNCATE, etc.)
            are blocked unless the server was started with --unsafe.
            """
            _check_destructive(sql, unsafe)
            audit("write", sql)
            with _connect(db_path) as conn:
                cur = conn.execute(sql, tuple(params or ()))
                return {"rowcount": cur.rowcount, "lastrowid": cur.lastrowid}

    return mcp
