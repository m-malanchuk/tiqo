"""Key/value settings repository."""

from __future__ import annotations

import sqlite3

from app.storage.transaction import write


class SettingsRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get(self, key: str) -> str | None:
        row = self._conn.execute(
            "SELECT value FROM settings WHERE key = ?",
            (key,),
        ).fetchone()
        return None if row is None else str(row["value"])

    def set(self, key: str, value: str) -> None:
        with write(self._conn):
            self._conn.execute(
                """
                INSERT INTO settings (key, value) VALUES (?, ?)
                ON CONFLICT (key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )
