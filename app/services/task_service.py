"""Task editing helpers: parent link and delete."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime

from app.domain.models import CompletionKind, TaskCompletion, TaskKind
from app.domain.timeutil import utc_now
from app.storage.assignment_repo import AssignmentRepo
from app.storage.completion_repo import CompletionRepo
from app.storage.session_repo import SessionRepo
from app.storage.stats_repo import StatsRepo
from app.storage.task_repo import TaskRepo
from app.storage.transaction import atomic
from app.storage.work_repo import WorkRepo


class TaskService:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._tasks = TaskRepo(conn)
        self._sessions = SessionRepo(conn)
        self._completions = CompletionRepo(conn)
        self._assignments = AssignmentRepo(conn)
        self._stats = StatsRepo(conn)
        self._work = WorkRepo(conn)

    def complete_checklist(
        self,
        task_id: int,
        *,
        note: str = "",
        now: datetime | None = None,
    ) -> TaskCompletion:
        """Record one checklist execution as a standalone history event."""
        task = self._tasks.get(task_id)
        if task is None:
            raise KeyError(f"Task {task_id} not found")
        if task.kind is not TaskKind.CHECKLIST:
            raise ValueError("Only checklist tasks can be marked done")
        stamp = now or utc_now()
        with atomic(self._conn):
            return self._completions.create(
                task_id,
                session_id=None,
                completed_at=stamp,
                kind=CompletionKind.CHECKLIST,
                note=note.strip(),
            )

    def set_today_assignment(
        self,
        task_id: int,
        assigned: bool,
        *,
        assigned_date: date,
    ) -> None:
        """Add/remove a task from a concrete local calendar date."""
        task = self._tasks.get(task_id)
        if task is None:
            raise KeyError(f"Task {task_id} not found")
        if assigned:
            self._assignments.assign(task_id, assigned_date)
        else:
            self._assignments.remove(task_id, assigned_date)

    def toggle_today_assignment(self, task_id: int, *, assigned_date: date) -> bool:
        assigned = not self._assignments.is_assigned(task_id, assigned_date)
        self.set_today_assignment(task_id, assigned, assigned_date=assigned_date)
        return assigned

    def set_parent(self, child_task_id: int, parent_task_id: int | None) -> None:
        with atomic(self._conn):
            self._tasks.set_parent(child_task_id, parent_task_id)

    def delete_task(self, task_id: int, *, mode: str) -> list[int]:
        """Delete a task.

        - ``this_only``: delete this task and its sessions; children become roots.
        - ``cascade``: delete this task and all descendants (and their sessions).
        """
        if mode not in ("this_only", "cascade"):
            raise ValueError(f"Unknown delete mode: {mode}")
        task = self._tasks.get(task_id)
        if task is None:
            raise KeyError(f"Task {task_id} not found")

        with atomic(self._conn):
            if mode == "cascade":
                to_delete = [task_id, *sorted(self._tasks.descendant_ids(task_id), reverse=True)]
            else:
                for child_id in self._tasks.children_of(task_id):
                    self._tasks.set_parent(child_id, None)
                to_delete = [task_id]

            deleted: list[int] = []
            for tid in to_delete:
                if self._tasks.get(tid) is None:
                    continue
                self._work.remove(tid)
                self._sessions.delete_for_task(tid)
                self._tasks.delete(tid)
                deleted.append(tid)

            self._stats.rebuild_from_sessions()
        return deleted
