"""Open and migrate the application database."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.storage.connection import connect, connect_memory
from app.storage.migrations import apply_migrations
from app.storage.paths import default_db_path


def open_database(path: str | Path | None = None) -> sqlite3.Connection:
    """Open a file DB (default XDG path), apply migrations, return connection."""
    db_path = Path(path) if path is not None else default_db_path()
    conn = connect(db_path)
    apply_migrations(conn)
    return conn


def open_memory_database() -> sqlite3.Connection:
    """Open a migrated in-memory DB (tests / ephemeral)."""
    conn = connect_memory()
    apply_migrations(conn)
    return conn
