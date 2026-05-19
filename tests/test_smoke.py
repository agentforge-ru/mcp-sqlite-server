"""Smoke tests for mcp_sqlite_server. These verify the package imports cleanly,
safety guards behave as documented, and the server builds against a real SQLite file."""
from __future__ import annotations

import os
import sqlite3
import tempfile

import pytest

from mcp_sqlite_server.server import (
    SafetyError,
    _check_destructive,
    _check_read_only,
    build_server,
)


def test_package_imports():
    """Package imports without errors and exposes __version__."""
    import mcp_sqlite_server

    assert mcp_sqlite_server.__version__


# --- read-only guard ------------------------------------------------------

@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM users",
        "  SELECT id FROM events  ",
        "WITH cte AS (SELECT 1) SELECT * FROM cte",
        "PRAGMA table_info(users)",
        "PRAGMA table_list",
    ],
)
def test_read_only_accepts_select_and_pragma(sql: str):
    _check_read_only(sql)  # no exception


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO users VALUES (1)",
        "UPDATE users SET name = 'X'",
        "DELETE FROM users WHERE id = 1",
        "ALTER TABLE users ADD COLUMN x TEXT",
    ],
)
def test_read_only_rejects_writes(sql: str):
    with pytest.raises(SafetyError):
        _check_read_only(sql)


# --- destructive guard ----------------------------------------------------

@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE users",
        "DROP DATABASE prod",
        "TRUNCATE TABLE events",
        "ATTACH DATABASE 'other.db' AS other",
        "PRAGMA writable_schema = 1",
    ],
)
def test_destructive_blocked_in_safe_mode(sql: str):
    with pytest.raises(SafetyError):
        _check_destructive(sql, unsafe=False)


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE users",
        "TRUNCATE TABLE events",
    ],
)
def test_destructive_allowed_in_unsafe_mode(sql: str):
    """Unsafe flag disables the destructive guard."""
    _check_destructive(sql, unsafe=True)  # no exception


# --- server build ---------------------------------------------------------

def test_build_server_with_real_sqlite():
    """Server builds against a real on-disk SQLite without raising."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        conn = sqlite3.connect(path)
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO test (name) VALUES ('alpha')")
        conn.commit()
        conn.close()

        server = build_server(db_path=path, allow_writes=False, unsafe=False)
        assert server is not None
        assert server.name == "sqlite-server"
    finally:
        os.unlink(path)


def test_build_server_with_writes_enabled():
    """Server builds with --allow-writes flag without raising."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        conn = sqlite3.connect(path)
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()

        server = build_server(db_path=path, allow_writes=True, unsafe=False)
        assert server is not None
    finally:
        os.unlink(path)
