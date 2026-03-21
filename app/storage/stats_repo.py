"""Daily stats cache repository."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime

from app.domain.models import DailyStat
from app.domain.timeutil import date_from_db, date_to_db, dt_from_db, seconds_by_local_day
from app.storage.transaction import write


class StatsRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get(self, task_id: int, day: date) -> DailyStat | None:
        row = self._conn.execute(
            """
            SELECT task_id, date, total_seconds, sessions_count
            FROM daily_stats
            WHERE task_id = ? AND date = ?
            """,
            (task_id, date_to_db(day)),
        ).fetchone()
        return None if row is None else _stat_from_row(row)

    def add_session_seconds(self, task_id: int, day: date, seconds: int) -> DailyStat:
        if seconds < 0:
            raise ValueError("seconds must be non-negative")
        day_s = date_to_db(day)
        with write(self._conn):
            self._conn.execute(
                """
                INSERT INTO daily_stats (task_id, date, total_seconds, sessions_count)
                VALUES (?, ?, ?, 1)
                ON CONFLICT (task_id, date) DO UPDATE SET
                    total_seconds = total_seconds + excluded.total_seconds,
                    sessions_count = sessions_count + 1
                """,
                (task_id, day_s, seconds),
            )
        stat = self.get(task_id, day)
        assert stat is not None
        return stat

    def rebuild_from_sessions(self) -> None:
        """Recompute daily_stats from closed work intervals."""
        with write(self._conn):
            self._conn.execute("DELETE FROM daily_stats")
            rows = self._conn.execute(
                """
                SELECT s.task_id, i.session_id, i.started_at, i.ended_at
                FROM session_intervals i
                JOIN sessions s ON s.id = i.session_id
                WHERE i.ended_at IS NOT NULL
                """
            ).fetchall()
            totals: dict[tuple[int, str], list[int]] = {}
            session_days: dict[tuple[int, str], set[int]] = {}
            for row in rows:
                started = dt_from_db(str(row["started_at"]))
                ended = dt_from_db(str(row["ended_at"]))
                for day, seconds in seconds_by_local_day(started, ended).items():
                    key = (int(row["task_id"]), date_to_db(day))
                    bucket = totals.setdefault(key, [0, 0])
                    bucket[0] += seconds
                    session_days.setdefault(key, set()).add(int(row["session_id"]))
            for key, bucket in totals.items():
                bucket[1] = len(session_days[key])
            self._conn.executemany(
                """
                INSERT INTO daily_stats (task_id, date, total_seconds, sessions_count)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (task_id, day_s, total, count)
                    for (task_id, day_s), (total, count) in totals.items()
                ],
            )


def session_duration_seconds(started_at: datetime, ended_at: datetime) -> int:
    return max(0, int((ended_at - started_at).total_seconds()))


def _stat_from_row(row: sqlite3.Row) -> DailyStat:
    return DailyStat(
        task_id=int(row["task_id"]),
        date=date_from_db(str(row["date"])),
        total_seconds=int(row["total_seconds"]),
        sessions_count=int(row["sessions_count"]),
    )
