"""TimerEngine — multi-session tracking, hierarchy mutex, work roster."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime

from app.domain.models import (
    HEARTBEAT_INTERVAL_SECONDS,
    CompletionKind,
    EndReason,
    Session,
    TaskKind,
    WorkState,
)
from app.domain.timeutil import seconds_by_local_day, utc_now
from app.storage.completion_repo import CompletionRepo
from app.storage.session_repo import SessionRepo
from app.storage.stats_repo import StatsRepo, session_duration_seconds
from app.storage.task_repo import TaskRepo
from app.storage.transaction import atomic
from app.storage.work_repo import WorkRepo


class TimerEngineError(Exception):
    """Base error for timer operations."""


class NoActiveSessionError(TimerEngineError):
    """Raised when an operation requires an open session for a task."""


class TaskNotFoundError(TimerEngineError):
    """Raised when a task id does not exist."""


class ChecklistTaskError(TimerEngineError):
    """Raised when timer controls are used for a binary checklist task."""


class HierarchyConflictError(TimerEngineError):
    """Raised when starting would violate ancestor/descendant mutex."""


@dataclass(frozen=True, slots=True)
class TargetReachedEvent:
    session_id: int
    task_id: int


class TimerEngine:
    """Wall-clock multi-session engine with «В работе» roster."""

    heartbeat_interval_seconds = HEARTBEAT_INTERVAL_SECONDS

    def __init__(
        self,
        conn: sqlite3.Connection,
        *,
        sessions: SessionRepo | None = None,
        tasks: TaskRepo | None = None,
        stats: StatsRepo | None = None,
        work: WorkRepo | None = None,
        completions: CompletionRepo | None = None,
    ) -> None:
        self._conn = conn
        self._sessions = sessions or SessionRepo(conn)
        self._tasks = tasks or TaskRepo(conn)
        self._stats = stats or StatsRepo(conn)
        self._work = work or WorkRepo(conn)
        self._completions = completions or CompletionRepo(conn)
        self._zero_notified: set[int] = set()

    def recover_crash(self) -> list[Session]:
        recovered: list[Session] = []
        with atomic(self._conn):
            for open_session in self._sessions.list_running():
                closed = self._sessions.close(
                    open_session.id,
                    ended_at=open_session.last_seen_at,
                    end_reason=EndReason.CRASH_RECOVERED,
                )
                self._work.upsert(
                    closed.task_id,
                    WorkState.PAUSED,
                    activated_at=closed.last_seen_at,
                )
                recovered.append(closed)
            if recovered:
                self._stats.rebuild_from_sessions()
        return recovered

    def open_sessions(self) -> list[Session]:
        """Currently running sessions (paused sessions remain open but idle)."""
        return self._sessions.list_running()

    def open_session_for(self, task_id: int) -> Session | None:
        return self._sessions.get_running_for_task(task_id)

    def session_for_task(self, task_id: int) -> Session | None:
        """Return the open session, including one paused between intervals."""
        return self._sessions.get_open_for_task(task_id)

    def start(
        self,
        task_id: int,
        *,
        target_seconds: int | None = None,
        use_task_default: bool = True,
        note: str = "",
        now: datetime | None = None,
    ) -> Session:
        task = self._tasks.get(task_id)
        if task is None:
            raise TaskNotFoundError(f"Task {task_id} not found")
        if task.kind is TaskKind.CHECKLIST:
            raise ChecklistTaskError("Checklist tasks do not have timer sessions")

        stamp = now or utc_now()
        existing_running = self._sessions.get_running_for_task(task_id)
        if existing_running is not None:
            return existing_running

        with atomic(self._conn):
            ancestors = self._tasks.ancestor_ids(task_id)
            descendants = self._tasks.descendant_ids(task_id)
            for open_session in self._sessions.list_running():
                other = open_session.task_id
                if other in descendants:
                    raise HierarchyConflictError(
                        "Cannot start a task while a descendant is running"
                    )
                if other in ancestors:
                    self.pause(other, now=stamp)

            resolved_target = target_seconds
            if target_seconds is None and use_task_default:
                if task.default_mode.value == "countdown":
                    resolved_target = task.default_target_seconds
                else:
                    resolved_target = None

            existing = self._sessions.get_open_for_task(task_id)
            if existing is not None:
                self._sessions.start_interval(existing.id, started_at=stamp)
                # Fetch the owning session after adding the new active interval.
                reopened = self._sessions.get(existing.id)
                assert reopened is not None
                session_obj = reopened
            else:
                session_obj = self._sessions.create(
                    task_id,
                    started_at=stamp,
                    target_seconds=resolved_target,
                    note=note,
                )
            self._work.upsert(task_id, WorkState.RUNNING, activated_at=stamp)
        return session_obj

    def pause(self, task_id: int, *, now: datetime | None = None) -> Session:
        stamp = now or utc_now()
        open_session = self._sessions.get_running_for_task(task_id)
        if open_session is None:
            raise NoActiveSessionError(f"No open session for task {task_id}")
        with atomic(self._conn):
            self._sessions.close_interval(open_session.id, ended_at=stamp)
            self._work.upsert(task_id, WorkState.PAUSED, activated_at=stamp)
            self._stats.rebuild_from_sessions()
        paused = self._sessions.get(open_session.id)
        assert paused is not None
        return paused

    def stop(
        self,
        task_id: int,
        *,
        now: datetime | None = None,
        completion_kind: CompletionKind = CompletionKind.MANUAL_STOP,
    ) -> Session | None:
        stamp = now or utc_now()
        open_session = self._sessions.get_open_for_task(task_id)
        closed: Session | None = None
        with atomic(self._conn):
            if open_session is not None:
                closed = self._sessions.close(
                    open_session.id,
                    ended_at=stamp,
                    end_reason=EndReason.STOPPED,
                )
                self._completions.create_from_session(
                    task_id,
                    session_id=closed.id,
                    completed_at=stamp,
                    kind=completion_kind,
                    note=closed.note,
                )
            self._work.remove(task_id)
            if closed is not None:
                self._stats.rebuild_from_sessions()
        return closed

    def resume(self, task_id: int, *, now: datetime | None = None) -> Session:
        """Resume a paused work item in the same session when possible."""
        return self.start(task_id, use_task_default=True, now=now)

    def update_note(self, task_id: int, note: str) -> Session:
        """Update the note for the open session without changing its intervals."""
        session = self.session_for_task(task_id)
        if session is None:
            raise NoActiveSessionError(f"No open session for task {task_id}")
        return self._sessions.set_note(session.id, note.strip())

    def heartbeat(self, *, now: datetime | None = None) -> list[Session]:
        stamp = now or utc_now()
        touched: list[Session] = []
        with atomic(self._conn):
            for open_session in self._sessions.list_open():
                touched.append(self._sessions.touch(open_session.id, last_seen_at=stamp))
        return touched

    def set_mode(
        self,
        task_id: int,
        *,
        target_seconds: int | None = None,
        countdown_duration: int | None = None,
        now: datetime | None = None,
    ) -> Session:
        open_session = self._sessions.get_running_for_task(task_id)
        if open_session is None:
            raise NoActiveSessionError(f"No open session for task {task_id}")

        stamp = now or utc_now()
        if countdown_duration is not None:
            if countdown_duration < 0:
                raise ValueError("countdown_duration must be non-negative")
            elapsed = self.elapsed_seconds(open_session, now=stamp)
            resolved: int | None = elapsed + countdown_duration
        else:
            resolved = target_seconds
        return self._sessions.set_target_seconds(open_session.id, resolved)

    def elapsed_seconds(self, session: Session, *, now: datetime | None = None) -> int:
        stamp = now or utc_now()
        total = 0
        for interval in self._sessions.list_intervals(session.id):
            end = interval.ended_at or stamp
            total += session_duration_seconds(interval.started_at, end)
        return total

    def task_elapsed_seconds(self, task_id: int, *, now: datetime | None = None) -> int:
        stamp = now or utc_now()
        total = 0
        for session in self._sessions.list_for_task(task_id):
            total += self.elapsed_seconds(session, now=stamp)
        return total

    def task_elapsed_today(
        self,
        task_id: int,
        *,
        now: datetime | None = None,
        today: date | None = None,
    ) -> int:
        stamp = now or utc_now()
        day = today or stamp.astimezone().date()
        total = 0
        for session in self._sessions.list_for_task(task_id):
            for interval in self._sessions.list_intervals(session.id):
                ended_at = interval.ended_at or stamp
                total += seconds_by_local_day(interval.started_at, ended_at).get(day, 0)
        return total

    def task_rollup_seconds(self, task_id: int, *, now: datetime | None = None) -> int:
        """Own time + unique descendants (tree)."""
        stamp = now or utc_now()
        ids = {task_id, *self._tasks.descendant_ids(task_id)}
        return sum(self.task_elapsed_seconds(tid, now=stamp) for tid in ids)

    def remaining_seconds(self, session: Session, *, now: datetime | None = None) -> int | None:
        if session.target_seconds is None:
            return None
        return int(session.target_seconds) - self.elapsed_seconds(session, now=now)

    def poll_target_reached(self, *, now: datetime | None = None) -> list[TargetReachedEvent]:
        """One-shot zero events for all open countdown sessions that crossed zero."""
        events: list[TargetReachedEvent] = []
        for session in self._sessions.list_open():
            if session.target_seconds is None:
                continue
            if session.id in self._zero_notified:
                continue
            if self.elapsed_seconds(session, now=now) < session.target_seconds:
                continue
            self._zero_notified.add(session.id)
            events.append(TargetReachedEvent(session_id=session.id, task_id=session.task_id))
        return events
