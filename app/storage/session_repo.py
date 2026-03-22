"""Session repository — source of truth for tracked time."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from datetime import date, datetime

from app.domain.models import EndReason, Session, SessionInterval
from app.domain.timeutil import dt_from_db, dt_to_db
from app.storage.transaction import write

_SESSION_COLS = """
    id, task_id, started_at, ended_at, last_seen_at,
    target_seconds, end_reason, note
"""

_INTERVAL_COLS = "id, session_id, started_at, ended_at"


class SessionRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get(self, session_id: int) -> Session | None:
        row = self._conn.execute(
            f"SELECT {_SESSION_COLS} FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        return None if row is None else _session_from_row(row)

    def get_open(self) -> Session | None:
        """Legacy helper: most recently opened session (prefer list_open)."""
        open_sessions = self.list_open()
        return open_sessions[-1] if open_sessions else None

    def get_open_for_task(self, task_id: int) -> Session | None:
        row = self._conn.execute(
            f"""
            SELECT {_SESSION_COLS} FROM sessions
            WHERE task_id = ? AND ended_at IS NULL
            ORDER BY id DESC LIMIT 1
            """,
            (task_id,),
        ).fetchone()
        return None if row is None else _session_from_row(row)

    def get_running_for_task(self, task_id: int) -> Session | None:
        row = self._conn.execute(
            f"""
            SELECT {_SESSION_COLS} FROM sessions
            WHERE task_id = ? AND ended_at IS NULL
              AND EXISTS (
                  SELECT 1 FROM session_intervals i
                  WHERE i.session_id = sessions.id AND i.ended_at IS NULL
              )
            ORDER BY id DESC LIMIT 1
            """,
            (task_id,),
        ).fetchone()
        return None if row is None else _session_from_row(row)

    def list_open(self) -> list[Session]:
        rows = self._conn.execute(
            f"""
            SELECT {_SESSION_COLS} FROM sessions
            WHERE ended_at IS NULL
            ORDER BY id
            """
        ).fetchall()
        return [_session_from_row(row) for row in rows]

    def list_running(self) -> list[Session]:
        rows = self._conn.execute(
            f"""
            SELECT {_SESSION_COLS} FROM sessions
            WHERE ended_at IS NULL
              AND EXISTS (
                  SELECT 1 FROM session_intervals i
                  WHERE i.session_id = sessions.id AND i.ended_at IS NULL
              )
            ORDER BY id
            """
        ).fetchall()
        return [_session_from_row(row) for row in rows]

    def list_intervals(self, session_id: int) -> list[SessionInterval]:
        rows = self._conn.execute(
            f"""
            SELECT {_INTERVAL_COLS} FROM session_intervals
            WHERE session_id = ? ORDER BY id
            """,
            (session_id,),
        ).fetchall()
        return [_interval_from_row(row) for row in rows]

    def get_open_interval(self, session_id: int) -> SessionInterval | None:
        row = self._conn.execute(
            f"""
            SELECT {_INTERVAL_COLS} FROM session_intervals
            WHERE session_id = ? AND ended_at IS NULL
            ORDER BY id DESC LIMIT 1
            """,
            (session_id,),
        ).fetchone()
        return None if row is None else _interval_from_row(row)

    def list_for_task(self, task_id: int) -> list[Session]:
        rows = self._conn.execute(
            f"""
            SELECT {_SESSION_COLS} FROM sessions
            WHERE task_id = ?
            ORDER BY id
            """,
            (task_id,),
        ).fetchall()
        return [_session_from_row(row) for row in rows]

    def create(
        self,
        task_id: int,
        *,
        started_at: datetime,
        target_seconds: int | None = None,
        note: str = "",
    ) -> Session:
        stamp = dt_to_db(started_at)
        with write(self._conn):
            cur = self._conn.execute(
                """
                INSERT INTO sessions (
                    task_id, started_at, ended_at, last_seen_at,
                    target_seconds, end_reason, note
                ) VALUES (?, ?, NULL, ?, ?, NULL, ?)
                """,
                (task_id, stamp, stamp, target_seconds, note),
            )
            session_id = cur.lastrowid
            if session_id is None:
                raise RuntimeError("INSERT INTO sessions did not return an id")
            self._conn.execute(
                """
                INSERT INTO session_intervals (session_id, started_at, ended_at)
                VALUES (?, ?, NULL)
                """,
                (int(session_id), stamp),
            )
        session = self.get(int(session_id))
        assert session is not None
        return session

    def close(
        self,
        session_id: int,
        *,
        ended_at: datetime,
        end_reason: EndReason,
    ) -> Session:
        with write(self._conn):
            self._conn.execute(
                """
                UPDATE session_intervals
                SET ended_at = ?
                WHERE session_id = ? AND ended_at IS NULL
                """,
                (dt_to_db(ended_at), session_id),
            )
            self._conn.execute(
                """
                UPDATE sessions
                SET ended_at = ?, last_seen_at = ?, end_reason = ?
                WHERE id = ? AND ended_at IS NULL
                """,
                (dt_to_db(ended_at), dt_to_db(ended_at), end_reason.value, session_id),
            )
        session = self.get(session_id)
        assert session is not None
        if session.ended_at is None:
            raise RuntimeError(f"Session {session_id} was not open")
        return session

    def close_interval(self, session_id: int, *, ended_at: datetime) -> SessionInterval:
        with write(self._conn):
            self._conn.execute(
                """
                UPDATE session_intervals
                SET ended_at = ?
                WHERE session_id = ? AND ended_at IS NULL
                """,
                (dt_to_db(ended_at), session_id),
            )
        interval = self.get_open_interval(session_id)
        if interval is not None:
            raise RuntimeError(f"Session interval {interval.id} was not closed")
        intervals = self.list_intervals(session_id)
        if not intervals:
            raise RuntimeError(f"Session {session_id} has no intervals")
        return intervals[-1]

    def start_interval(self, session_id: int, *, started_at: datetime) -> SessionInterval:
        with write(self._conn):
            if self.get_open_interval(session_id) is not None:
                raise RuntimeError(f"Session {session_id} already has an open interval")
            cur = self._conn.execute(
                """
                INSERT INTO session_intervals (session_id, started_at, ended_at)
                VALUES (?, ?, NULL)
                """,
                (session_id, dt_to_db(started_at)),
            )
            interval_id = cur.lastrowid
            if interval_id is None:
                raise RuntimeError("INSERT INTO session_intervals did not return an id")
        interval = self._conn.execute(
            f"SELECT {_INTERVAL_COLS} FROM session_intervals WHERE id = ?",
            (int(interval_id),),
        ).fetchone()
        assert interval is not None
        return _interval_from_row(interval)

    def touch(self, session_id: int, *, last_seen_at: datetime) -> Session:
        with write(self._conn):
            self._conn.execute(
                """
                UPDATE sessions
                SET last_seen_at = ?
                WHERE id = ? AND ended_at IS NULL
                """,
                (dt_to_db(last_seen_at), session_id),
            )
        session = self.get(session_id)
        assert session is not None
        return session

    def set_note(self, session_id: int, note: str) -> Session:
        """Update the note of an open session, including a paused one."""
        with write(self._conn):
            self._conn.execute(
                """
                UPDATE sessions SET note = ?
                WHERE id = ? AND ended_at IS NULL
                """,
                (note, session_id),
            )
        session = self.get(session_id)
        if session is None or not session.is_open:
            raise RuntimeError(f"Session {session_id} is not open")
        return session

    def set_target_seconds(self, session_id: int, target_seconds: int | None) -> Session:
        with write(self._conn):
            self._conn.execute(
                """
                UPDATE sessions
                SET target_seconds = ?
                WHERE id = ? AND ended_at IS NULL
                """,
                (target_seconds, session_id),
            )
        session = self.get(session_id)
        assert session is not None
        if not session.is_open:
            raise RuntimeError(f"Session {session_id} is not open")
        return session

    def latest_for_task(self, task_id: int) -> Session | None:
        row = self._conn.execute(
            f"""
            SELECT {_SESSION_COLS} FROM sessions
            WHERE task_id = ?
            ORDER BY id DESC LIMIT 1
            """,
            (task_id,),
        ).fetchone()
        return None if row is None else _session_from_row(row)

    def delete_for_task(self, task_id: int) -> int:
        with write(self._conn):
            cur = self._conn.execute(
                "DELETE FROM sessions WHERE task_id = ?",
                (task_id,),
            )
            return int(cur.rowcount)

    def count_for_task(self, task_id: int) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS n FROM sessions WHERE task_id = ?",
            (task_id,),
        ).fetchone()
        return int(row["n"])

    def iter_stops_on(self, day: date, task_ids: set[int] | None = None) -> Iterator[int]:
        """Yield ``task_id`` for each ``STOPPED`` session started on ``day`` (local)."""
        rows = self._conn.execute(
            """
            SELECT task_id, started_at FROM sessions
            WHERE end_reason = ? AND ended_at IS NOT NULL
            """,
            (EndReason.STOPPED.value,),
        ).fetchall()
        for row in rows:
            tid = int(row["task_id"])
            if task_ids is not None and tid not in task_ids:
                continue
            started = dt_from_db(str(row["started_at"]))
            if started.astimezone().date() == day:
                yield tid

    def task_ids_stopped_on(self, day: date, task_ids: set[int] | None = None) -> set[int]:
        """Unique tasks with at least one ``Stop`` on ``day`` (local)."""
        return set(self.iter_stops_on(day, task_ids))

    def count_stops_on(self, day: date, task_ids: set[int]) -> int:
        """How many ``Stop`` events on ``day`` for ``task_ids`` (repeats count)."""
        if not task_ids:
            return 0
        return sum(1 for _ in self.iter_stops_on(day, task_ids))


def _session_from_row(row: sqlite3.Row) -> Session:
    end_reason_raw = row["end_reason"]
    return Session(
        id=int(row["id"]),
        task_id=int(row["task_id"]),
        started_at=dt_from_db(str(row["started_at"])),
        ended_at=None if row["ended_at"] is None else dt_from_db(str(row["ended_at"])),
        last_seen_at=dt_from_db(str(row["last_seen_at"])),
        target_seconds=(None if row["target_seconds"] is None else int(row["target_seconds"])),
        end_reason=None if end_reason_raw is None else EndReason(end_reason_raw),
        note=str(row["note"] or ""),
    )


def _interval_from_row(row: sqlite3.Row) -> SessionInterval:
    return SessionInterval(
        id=int(row["id"]),
        session_id=int(row["session_id"]),
        started_at=dt_from_db(str(row["started_at"])),
        ended_at=None if row["ended_at"] is None else dt_from_db(str(row["ended_at"])),
    )
