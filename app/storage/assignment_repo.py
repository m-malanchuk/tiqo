"""Manual calendar assignments for the virtual «Today» list."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime

from app.domain.timeutil import date_from_db, date_to_db, dt_to_db, utc_now
from app.storage.transaction import write


class AssignmentRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def assign(
        self, task_id: int, assigned_date: date, *, created_at: datetime | None = None
    ) -> None:
        stamp = created_at or utc_now()
        with write(self._conn):
            self._conn.execute(
                """
                INSERT INTO task_assignments (task_id, assigned_date, created_at)
                VALUES (?, ?, ?)
                ON CONFLICT (task_id, assigned_date) DO NOTHING
                """,
                (task_id, date_to_db(assigned_date), dt_to_db(stamp)),
            )

    def remove(self, task_id: int, assigned_date: date) -> None:
        with write(self._conn):
            self._conn.execute(
                "DELETE FROM task_assignments WHERE task_id = ? AND assigned_date = ?",
                (task_id, date_to_db(assigned_date)),
            )

    def is_assigned(self, task_id: int, assigned_date: date) -> bool:
        row = self._conn.execute(
            """
            SELECT 1 FROM task_assignments
            WHERE task_id = ? AND assigned_date = ?
            """,
            (task_id, date_to_db(assigned_date)),
        ).fetchone()
        return row is not None

    def task_ids_on(self, assigned_date: date) -> list[int]:
        rows = self._conn.execute(
            """
            SELECT task_id FROM task_assignments
            WHERE assigned_date = ? ORDER BY task_id
            """,
            (date_to_db(assigned_date),),
        ).fetchall()
        return [int(row["task_id"]) for row in rows]

    def dates_for_task(self, task_id: int) -> list[date]:
        rows = self._conn.execute(
            """
            SELECT assigned_date FROM task_assignments
            WHERE task_id = ? ORDER BY assigned_date
            """,
            (task_id,),
        ).fetchall()
        return [date_from_db(str(row["assigned_date"])) for row in rows]
