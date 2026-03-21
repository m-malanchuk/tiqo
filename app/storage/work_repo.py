"""Work roster — tasks currently «В работе» (running or paused)."""

from __future__ import annotations

import sqlite3
from datetime import datetime

from app.domain.models import WorkItem, WorkState
from app.domain.timeutil import dt_from_db, dt_to_db
from app.storage.transaction import write


class WorkRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def list_all(self) -> list[WorkItem]:
        rows = self._conn.execute(
            """
            SELECT task_id, state, position, activated_at
            FROM work_items
            ORDER BY position, task_id
            """
        ).fetchall()
        return [_from_row(row) for row in rows]

    def get(self, task_id: int) -> WorkItem | None:
        row = self._conn.execute(
            """
            SELECT task_id, state, position, activated_at
            FROM work_items WHERE task_id = ?
            """,
            (task_id,),
        ).fetchone()
        return None if row is None else _from_row(row)

    def upsert(
        self,
        task_id: int,
        state: WorkState,
        *,
        activated_at: datetime,
        position: int | None = None,
    ) -> WorkItem:
        existing = self.get(task_id)
        if position is None:
            if existing is not None:
                position = existing.position
            else:
                row = self._conn.execute(
                    "SELECT COALESCE(MAX(position), -1) + 1 FROM work_items"
                ).fetchone()
                position = int(row[0])
        with write(self._conn):
            self._conn.execute(
                """
                INSERT INTO work_items (task_id, state, position, activated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT (task_id) DO UPDATE SET
                    state = excluded.state,
                    position = excluded.position,
                    activated_at = CASE
                        WHEN work_items.state = 'paused' AND excluded.state = 'running'
                        THEN excluded.activated_at
                        ELSE work_items.activated_at
                    END
                """,
                (task_id, state.value, position, dt_to_db(activated_at)),
            )
        item = self.get(task_id)
        assert item is not None
        return item

    def remove(self, task_id: int) -> None:
        with write(self._conn):
            self._conn.execute("DELETE FROM work_items WHERE task_id = ?", (task_id,))


def _from_row(row: sqlite3.Row) -> WorkItem:
    return WorkItem(
        task_id=int(row["task_id"]),
        state=WorkState(row["state"]),
        position=int(row["position"]),
        activated_at=dt_from_db(str(row["activated_at"])),
    )
