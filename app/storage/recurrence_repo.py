"""Persistence for ``task_recurrence``."""

from __future__ import annotations

import sqlite3

from app.domain.models import RecurrenceKind, TaskRecurrence
from app.domain.timeutil import date_from_db, date_to_db
from app.storage.transaction import write


class RecurrenceRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get(self, task_id: int) -> TaskRecurrence | None:
        row = self._conn.execute(
            """
            SELECT task_id, kind, interval, weekdays_mask, anchor_date
            FROM task_recurrence WHERE task_id = ?
            """,
            (task_id,),
        ).fetchone()
        return None if row is None else _from_row(row)

    def list_all(self) -> list[TaskRecurrence]:
        rows = self._conn.execute(
            """
            SELECT task_id, kind, interval, weekdays_mask, anchor_date
            FROM task_recurrence
            """
        ).fetchall()
        return [_from_row(r) for r in rows]

    def list_active(self) -> list[TaskRecurrence]:
        """Rules that can place a task into «Сегодня» (kind ≠ none)."""
        rows = self._conn.execute(
            """
            SELECT task_id, kind, interval, weekdays_mask, anchor_date
            FROM task_recurrence
            WHERE kind != 'none'
            """
        ).fetchall()
        return [_from_row(r) for r in rows]

    def upsert(self, rule: TaskRecurrence) -> TaskRecurrence:
        with write(self._conn):
            self._conn.execute(
                """
                INSERT INTO task_recurrence (
                    task_id, kind, interval, weekdays_mask, anchor_date
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    kind = excluded.kind,
                    interval = excluded.interval,
                    weekdays_mask = excluded.weekdays_mask,
                    anchor_date = excluded.anchor_date
                """,
                (
                    rule.task_id,
                    rule.kind.value,
                    rule.interval,
                    rule.weekdays_mask,
                    date_to_db(rule.anchor_date) if rule.anchor_date else None,
                ),
            )
        saved = self.get(rule.task_id)
        assert saved is not None
        return saved

    def delete(self, task_id: int) -> None:
        with write(self._conn):
            self._conn.execute("DELETE FROM task_recurrence WHERE task_id = ?", (task_id,))


def _from_row(row: sqlite3.Row | tuple) -> TaskRecurrence:
    if isinstance(row, sqlite3.Row):
        task_id = int(row["task_id"])
        kind = RecurrenceKind(str(row["kind"]))
        interval = row["interval"]
        weekdays_mask = row["weekdays_mask"]
        anchor = row["anchor_date"]
    else:
        task_id = int(row[0])
        kind = RecurrenceKind(str(row[1]))
        interval = row[2]
        weekdays_mask = row[3]
        anchor = row[4]
    return TaskRecurrence(
        task_id=task_id,
        kind=kind,
        interval=int(interval) if interval is not None else None,
        weekdays_mask=int(weekdays_mask) if weekdays_mask is not None else None,
        anchor_date=date_from_db(str(anchor)) if anchor else None,
    )
