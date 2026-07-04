"""Repository for the unified completed-session/checklist history."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime

from app.domain.models import CompletionInterval, CompletionKind, TaskCompletion
from app.domain.timeutil import date_from_db, date_to_db, dt_from_db, dt_to_db
from app.storage.transaction import write


class CompletionRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(
        self,
        task_id: int,
        *,
        session_id: int | None,
        completed_at: datetime,
        kind: CompletionKind,
        completion_date: date | None = None,
        note: str = "",
    ) -> TaskCompletion:
        stamp = dt_to_db(completed_at)
        day = completion_date or completed_at.astimezone().date()
        with write(self._conn):
            cur = self._conn.execute(
                """
                INSERT INTO task_completions (
                    task_id, session_id, completed_at, completion_date, completion_kind, note,
                    started_at, ended_at, duration_seconds
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    session_id,
                    stamp,
                    date_to_db(day),
                    kind.value,
                    note,
                    None,
                    None,
                    None,
                ),
            )
            completion_id = cur.lastrowid
            if completion_id is None:
                raise RuntimeError("INSERT INTO task_completions did not return an id")
        completion = self.get(int(completion_id))
        assert completion is not None
        return completion

    def create_from_session(
        self,
        task_id: int,
        *,
        session_id: int,
        completed_at: datetime,
        kind: CompletionKind,
        note: str = "",
    ) -> TaskCompletion:
        completion = self.create(
            task_id,
            session_id=session_id,
            completed_at=completed_at,
            kind=kind,
            note=note,
        )
        rows = self._conn.execute(
            """
            SELECT started_at, ended_at
            FROM session_intervals
            WHERE session_id = ? AND ended_at IS NOT NULL
            ORDER BY id
            """,
            (session_id,),
        ).fetchall()
        intervals = [
            (dt_from_db(str(row["started_at"])), dt_from_db(str(row["ended_at"]))) for row in rows
        ]
        if intervals:
            self.replace_intervals(completion.id, intervals)
        refreshed = self.get(completion.id)
        assert refreshed is not None
        return refreshed

    def get(self, completion_id: int) -> TaskCompletion | None:
        row = self._conn.execute(
            """
            SELECT id, task_id, session_id, completed_at, completion_date, completion_kind,
                   note, started_at, ended_at, duration_seconds
            FROM task_completions WHERE id = ?
            """,
            (completion_id,),
        ).fetchone()
        return None if row is None else _completion_from_row(row)

    def get_for_session(self, session_id: int) -> TaskCompletion | None:
        row = self._conn.execute(
            """
            SELECT id, task_id, session_id, completed_at, completion_date, completion_kind,
                   note, started_at, ended_at, duration_seconds
            FROM task_completions WHERE session_id = ?
            """,
            (session_id,),
        ).fetchone()
        return None if row is None else _completion_from_row(row)

    def list_for_task(self, task_id: int) -> list[TaskCompletion]:
        rows = self._conn.execute(
            """
            SELECT id, task_id, session_id, completed_at, completion_date, completion_kind,
                   note, started_at, ended_at, duration_seconds
            FROM task_completions
            WHERE task_id = ?
            ORDER BY completed_at, id
            """,
            (task_id,),
        ).fetchall()
        return [_completion_from_row(row) for row in rows]

    def list_all(self) -> list[TaskCompletion]:
        rows = self._conn.execute(
            """
            SELECT id, task_id, session_id, completed_at, completion_date, completion_kind,
                   note, started_at, ended_at, duration_seconds
            FROM task_completions
            ORDER BY completed_at DESC, id DESC
            """
        ).fetchall()
        return [_completion_from_row(row) for row in rows]

    def list_on(self, day: date) -> list[TaskCompletion]:
        rows = self._conn.execute(
            """
            SELECT id, task_id, session_id, completed_at, completion_date, completion_kind,
                   note, started_at, ended_at, duration_seconds
            FROM task_completions
            WHERE completion_date = ?
            ORDER BY completed_at DESC, id DESC
            """,
            (date_to_db(day),),
        ).fetchall()
        return [_completion_from_row(row) for row in rows]

    def task_ids_checklist_completed_on(self, day: date) -> set[int]:
        rows = self._conn.execute(
            """
            SELECT DISTINCT task_id FROM task_completions
            WHERE completion_date = ? AND completion_kind = ?
            """,
            (date_to_db(day), CompletionKind.CHECKLIST.value),
        ).fetchall()
        return {int(row["task_id"]) for row in rows}

    def count_checklist_on(self, day: date, task_ids: set[int] | None = None) -> int:
        sql = """
            SELECT COUNT(*) AS n FROM task_completions
            WHERE completion_date = ? AND completion_kind = ?
        """
        params: list[object] = [date_to_db(day), CompletionKind.CHECKLIST.value]
        if task_ids is not None:
            if not task_ids:
                return 0
            placeholders = ",".join("?" for _ in task_ids)
            sql += f" AND task_id IN ({placeholders})"
            params.extend(sorted(task_ids))
        row = self._conn.execute(sql, params).fetchone()
        return int(row["n"])

    def list_intervals(self, completion_id: int) -> list[CompletionInterval]:
        rows = self._conn.execute(
            """
            SELECT id, completion_id, started_at, ended_at
            FROM completion_intervals
            WHERE completion_id = ? ORDER BY id
            """,
            (completion_id,),
        ).fetchall()
        return [
            CompletionInterval(
                id=int(row["id"]),
                completion_id=int(row["completion_id"]),
                started_at=dt_from_db(str(row["started_at"])),
                ended_at=dt_from_db(str(row["ended_at"])),
            )
            for row in rows
        ]

    def replace_intervals(
        self,
        completion_id: int,
        intervals: list[tuple[datetime, datetime]],
    ) -> TaskCompletion:
        if any(end < start for start, end in intervals):
            raise ValueError("Completion interval end must not precede its start")
        with write(self._conn):
            self._conn.execute(
                "DELETE FROM completion_intervals WHERE completion_id = ?",
                (completion_id,),
            )
            self._conn.executemany(
                """
                INSERT INTO completion_intervals (completion_id, started_at, ended_at)
                VALUES (?, ?, ?)
                """,
                [(completion_id, dt_to_db(start), dt_to_db(end)) for start, end in intervals],
            )
            if intervals:
                started = min(start for start, _ in intervals)
                ended = max(end for _, end in intervals)
                duration = sum(int((end - start).total_seconds()) for start, end in intervals)
                self._conn.execute(
                    """
                    UPDATE task_completions
                    SET started_at = ?, ended_at = ?, duration_seconds = ?
                    WHERE id = ?
                    """,
                    (dt_to_db(started), dt_to_db(ended), max(0, duration), completion_id),
                )
            else:
                self._conn.execute(
                    """
                    UPDATE task_completions
                    SET started_at = NULL, ended_at = NULL, duration_seconds = NULL
                    WHERE id = ?
                    """,
                    (completion_id,),
                )
        completion = self.get(completion_id)
        assert completion is not None
        return completion

    def update(
        self,
        completion_id: int,
        *,
        completed_at: datetime | None = None,
        note: str | None = None,
    ) -> TaskCompletion:
        current = self.get(completion_id)
        if current is None:
            raise KeyError(f"Completion {completion_id} not found")
        stamp = current.completed_at if completed_at is None else completed_at
        new_note = current.note if note is None else note
        with write(self._conn):
            self._conn.execute(
                """
                UPDATE task_completions
                SET completed_at = ?, completion_date = ?, note = ?
                WHERE id = ?
                """,
                (dt_to_db(stamp), date_to_db(stamp.astimezone().date()), new_note, completion_id),
            )
        refreshed = self.get(completion_id)
        assert refreshed is not None
        return refreshed

    def delete(self, completion_id: int) -> None:
        with write(self._conn):
            self._conn.execute("DELETE FROM task_completions WHERE id = ?", (completion_id,))

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS n FROM task_completions").fetchone()
        return int(row["n"])


def _completion_from_row(row: sqlite3.Row) -> TaskCompletion:
    return TaskCompletion(
        id=int(row["id"]),
        task_id=int(row["task_id"]),
        session_id=None if row["session_id"] is None else int(row["session_id"]),
        completed_at=dt_from_db(str(row["completed_at"])),
        completion_date=date_from_db(str(row["completion_date"])),
        kind=CompletionKind(str(row["completion_kind"])),
        note=str(row["note"] or ""),
        started_at=None if row["started_at"] is None else dt_from_db(str(row["started_at"])),
        ended_at=None if row["ended_at"] is None else dt_from_db(str(row["ended_at"])),
        duration_seconds=(
            None if row["duration_seconds"] is None else int(row["duration_seconds"])
        ),
    )
