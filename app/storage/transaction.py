"""SQLite transaction scopes shared by repositories and application services."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager


@contextmanager
def atomic(conn: sqlite3.Connection) -> Iterator[None]:
    """Commit the whole scope, or join an already active transaction."""
    if conn.in_transaction:
        yield
        return
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield
    except BaseException:
        conn.rollback()
        raise
    else:
        conn.commit()


@contextmanager
def write(conn: sqlite3.Connection) -> Iterator[None]:
    """Repository write that participates in an enclosing atomic operation."""
    with atomic(conn):
        yield
