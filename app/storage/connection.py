"""SQLite connection helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def connect(path: str | Path) -> sqlite3.Connection:
    """Open a file-backed database with foreign keys and WAL enabled."""
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    _configure(conn, wal=True)
    return conn


def connect_memory() -> sqlite3.Connection:
    """Open an in-memory database (tests)."""
    conn = sqlite3.connect(":memory:")
    _configure(conn, wal=False)
    return conn


def _configure(conn: sqlite3.Connection, *, wal: bool) -> None:
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if wal:
        conn.execute("PRAGMA journal_mode = WAL")
