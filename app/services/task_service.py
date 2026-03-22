"""Task editing helpers: parent link and delete."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime

from app.domain.models import CompletionKind, Task, TaskKind
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

    def set_checklist_done(
        self,
        task_id: int,
        done: bool = True,
        *,
        now: datetime | None = None,
    ) -> Task:
        """Set a checklist task's binary state and record a done event once.

        Unchecking changes the current state but deliberately keeps prior
        completion events as history. Calling this with the current state is
        idempotent and does not create duplicate events.
        """
        task = self._tasks.get(task_id)
        if task is None:
            raise KeyError(f"Task {task_id} not found")
        if task.kind is not TaskKind.CHECKLIST:
            raise ValueError("Only checklist tasks can be marked done")
        desired = bool(done)
        if task.is_completed == desired:
            return task

        stamp = now or utc_now()
        with atomic(self._conn):
            if desired:
                self._completions.create(
                    task_id,
                    session_id=None,
                    completed_at=stamp,
                    kind=CompletionKind.CHECKLIST,
                )
                updated = self._tasks.set_checklist_state(
                    task_id,
                    is_completed=True,
                    completed_at=stamp,
                )
            else:
                updated = self._tasks.set_checklist_state(
                    task_id,
                    is_completed=False,
                    completed_at=None,
                )
        return updated

    def complete_checklist(self, task_id: int, *, now: datetime | None = None) -> Task:
        """Record one checklist execution, even when it was completed before."""
        task = self._tasks.get(task_id)
        if task is None:
            raise KeyError(f"Task {task_id} not found")
        if task.kind is not TaskKind.CHECKLIST:
            raise ValueError("Only checklist tasks can be marked done")
        stamp = now or utc_now()
        with atomic(self._conn):
            self._completions.create(
                task_id,
                session_id=None,
                completed_at=stamp,
                kind=CompletionKind.CHECKLIST,
            )
            updated = self._tasks.set_checklist_state(
                task_id,
                is_completed=True,
                completed_at=stamp,
            )
        return updated

    def toggle_checklist(self, task_id: int, *, now: datetime | None = None) -> Task:
        """Toggle a checklist task and return its new state."""
        task = self._tasks.get(task_id)
        if task is None:
            raise KeyError(f"Task {task_id} not found")
        return self.set_checklist_done(task_id, not task.is_completed, now=now)

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
