"""Application façade for timer/work roster — no QML / ViewModel dependency.

Used by the tray, Plasma widget (via D-Bus), and tests.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import asdict, dataclass

from app.application.models import WorkRow
from app.application.task_presentation import (
    build_task_rows,
    build_work_rows,
    seed_tasks_for_list,
)
from app.domain.models import LIST_FAVORITES_ID, LIST_IN_WORK_ID, LIST_TODAY_ID
from app.domain.timeutil import local_today
from app.i18n import list_title
from app.services.task_service import TaskService
from app.services.timer_engine import (
    HierarchyConflictError,
    NoActiveSessionError,
    TimerEngine,
)
from app.storage.assignment_repo import AssignmentRepo
from app.storage.completion_repo import CompletionRepo
from app.storage.list_repo import ListRepo
from app.storage.recurrence_repo import RecurrenceRepo
from app.storage.session_repo import SessionRepo
from app.storage.stats_repo import StatsRepo
from app.storage.task_repo import TaskRepo
from app.storage.work_repo import WorkRepo


@dataclass(frozen=True, slots=True)
class WorkSnapshot:
    """JSON-friendly work row for IPC."""

    task_id: int
    title: str
    state: str
    clock: str
    is_countdown: bool
    progress: float | None
    can_start: bool
    can_pause: bool
    can_stop: bool
    # Paused ancestor while a descendant runs — widget should hide the row.
    blocked_by_descendant: bool


@dataclass(frozen=True, slots=True)
class ListSnapshot:
    list_id: int
    name: str
    icon: str
    is_system: bool


@dataclass(frozen=True, slots=True)
class TaskSnapshot:
    """JSON-friendly task row for a selected list (widget popup)."""

    task_id: int
    title: str
    state: str
    clock: str
    is_countdown: bool
    progress: float | None
    can_start: bool
    can_pause: bool
    can_stop: bool
    depth: int
    blocked_by_descendant: bool
    has_children: bool
    kind: str
    is_completed: bool
    can_complete: bool


@dataclass(frozen=True, slots=True)
class TodayStatsSnapshot:
    """List forest leaves: done (Stop events today, repeats allowed) / total leaves."""

    done: int
    total: int


class SessionFacade:
    def __init__(
        self,
        conn: sqlite3.Connection,
        *,
        engine: TimerEngine | None = None,
        on_changed: Callable[[], None] | None = None,
    ) -> None:
        self._conn = conn
        self._engine = engine or TimerEngine(conn)
        self._tasks = TaskRepo(conn)
        self._task_service = TaskService(conn)
        self._work = WorkRepo(conn)
        self._lists = ListRepo(conn)
        self._recurrence = RecurrenceRepo(conn)
        self._assignments = AssignmentRepo(conn)
        self._completions = CompletionRepo(conn)
        self._sessions = SessionRepo(conn)
        self._stats = StatsRepo(conn)
        self._on_changed = on_changed

    @property
    def engine(self) -> TimerEngine:
        return self._engine

    def list_work(self) -> list[WorkSnapshot]:
        rows = build_work_rows(
            engine=self._engine,
            work_repo=self._work,
            tasks_repo=self._tasks,
        )
        return [_work_snapshot(row) for row in rows]

    def list_work_dicts(self) -> list[dict[str, object]]:
        return [asdict(row) for row in self.list_work()]

    def list_lists(self) -> list[ListSnapshot]:
        out: list[ListSnapshot] = []
        for lst in self._lists.list_all():
            out.append(
                ListSnapshot(
                    list_id=lst.id,
                    name=list_title(lst.key, lst.name),
                    icon=lst.icon or "",
                    is_system=bool(lst.is_system),
                )
            )
        return out

    def list_lists_dicts(self) -> list[dict[str, object]]:
        return [asdict(row) for row in self.list_lists()]

    def list_tasks(self, list_id: int) -> list[TaskSnapshot]:
        """Tasks for a list — widget roster.

        Most lists: **leaves only** in the list forest (parents stay in the app).
        «В работе»: only tasks **currently in the work roster** (Stop removes them).
        Parents in work are shown when they are in the roster — we do not keep
        non-work descendants visible under an in-work ancestor.
        """
        lid = int(list_id)
        seed = seed_tasks_for_list(
            selected_list_id=lid,
            lists_repo=self._lists,
            tasks_repo=self._tasks,
            work_repo=self._work,
            recurrence_repo=self._recurrence,
            assignment_repo=self._assignments,
            completion_repo=self._completions,
        )
        rows = build_task_rows(
            engine=self._engine,
            work_repo=self._work,
            tasks_repo=self._tasks,
            seed_tasks=seed,
            collapsed_task_ids=set(),
            assignment_repo=self._assignments,
            recurrence_repo=self._recurrence,
            today_occurrence=lid == LIST_TODAY_ID,
        )
        work_by_id = {
            w.task_id: w
            for w in build_work_rows(
                engine=self._engine,
                work_repo=self._work,
                tasks_repo=self._tasks,
            )
        }
        in_work_ids = set(work_by_id)
        out: list[TaskSnapshot] = []
        for row in rows:
            if lid == LIST_IN_WORK_ID:
                if row.id not in in_work_ids:
                    continue
            elif row.has_children:
                continue
            work = work_by_id.get(row.id)
            out.append(
                TaskSnapshot(
                    task_id=row.id,
                    title=row.title,
                    state=row.work_state or "",
                    clock=row.time_today,
                    is_countdown=bool(work.is_countdown) if work else False,
                    progress=(
                        (1.0 if row.is_completed else 0.0)
                        if row.kind == "checklist"
                        else (work.progress if work else None)
                    ),
                    can_start=row.can_start and not (work.blocked_by_descendant if work else False),
                    can_pause=row.can_pause,
                    can_stop=row.can_stop,
                    depth=0 if lid == LIST_IN_WORK_ID else row.depth,
                    blocked_by_descendant=bool(work.blocked_by_descendant) if work else False,
                    has_children=bool(row.has_children) if lid == LIST_IN_WORK_ID else False,
                    kind=row.kind,
                    is_completed=row.is_completed,
                    can_complete=row.can_complete,
                )
            )
        return out

    def list_tasks_dicts(self, list_id: int) -> list[dict[str, object]]:
        return [asdict(row) for row in self.list_tasks(list_id)]

    def list_progress(self, list_id: int) -> TodayStatsSnapshot:
        """Progress for a list: done today / size of ``list_tasks`` for that list.

        Leaves/roster match ``list_tasks``. ``done``:
        - **Favorites** — each ``Stop`` today counts (+1 even for the same task again),
          plus checklist execution events;
        - **other lists** — unique tasks with a ``Stop`` today (fraction ``done/total``),
          plus checklist execution events.
        Pause alone does not count. Checklist completion is a separate binary
        event and does not create a timer session.
        """
        lid = int(list_id)
        tasks = self.list_tasks(lid)
        ids = {t.task_id for t in tasks}
        today = local_today()
        if lid == LIST_TODAY_ID:
            all_today = seed_tasks_for_list(
                selected_list_id=lid,
                lists_repo=self._lists,
                tasks_repo=self._tasks,
                work_repo=self._work,
                recurrence_repo=self._recurrence,
                assignment_repo=self._assignments,
                completion_repo=None,
            )
            all_rows = build_task_rows(
                engine=self._engine,
                work_repo=self._work,
                tasks_repo=self._tasks,
                seed_tasks=all_today,
                collapsed_task_ids=set(),
                assignment_repo=self._assignments,
                recurrence_repo=self._recurrence,
            )
            all_ids = {row.id for row in all_rows if not row.has_children}
            completed = self._sessions.task_ids_stopped_on(today, all_ids)
            completed |= self._completions.task_ids_checklist_completed_on(today) & all_ids
            return TodayStatsSnapshot(done=len(completed), total=len(all_ids))
        if lid == LIST_FAVORITES_ID:
            done = self._sessions.count_stops_on(today, ids)
        else:
            done = len(self._sessions.task_ids_stopped_on(today, ids))
        done += self._completions.count_checklist_on(today, ids)
        return TodayStatsSnapshot(done=done, total=len(ids))

    def list_progress_dict(self, list_id: int) -> dict[str, object]:
        return asdict(self.list_progress(list_id))

    def today_stats(self) -> TodayStatsSnapshot:
        """Shortcut: progress for the Today list (leaf-only)."""
        return self.list_progress(LIST_TODAY_ID)

    def today_stats_dict(self) -> dict[str, object]:
        return asdict(self.today_stats())

    def resume(self, task_id: int) -> None:
        self._engine.resume(task_id)
        self._notify()

    def pause(self, task_id: int) -> None:
        self._engine.pause(task_id)
        self._notify()

    def stop(self, task_id: int) -> None:
        self._engine.stop(task_id)
        self._notify()

    def toggle_checklist(self, task_id: int) -> None:
        self._task_service.toggle_checklist(int(task_id))
        self._notify()

    def complete_checklist(self, task_id: int) -> None:
        self._task_service.complete_checklist(int(task_id))
        self._notify()

    def _notify(self) -> None:
        if self._on_changed is not None:
            self._on_changed()


def _work_snapshot(row: WorkRow) -> WorkSnapshot:
    running = row.state == "running"
    return WorkSnapshot(
        task_id=row.task_id,
        title=row.title,
        state=row.state,
        clock=row.clock,
        is_countdown=row.is_countdown,
        progress=row.progress,
        # Hierarchy mutex: cannot resume an ancestor while a descendant runs.
        can_start=not running and not row.blocked_by_descendant,
        can_pause=running,
        can_stop=True,
        blocked_by_descendant=row.blocked_by_descendant,
    )


# Re-export errors for D-Bus adapters
__all__ = [
    "HierarchyConflictError",
    "ListSnapshot",
    "NoActiveSessionError",
    "SessionFacade",
    "TaskSnapshot",
    "TodayStatsSnapshot",
    "WorkSnapshot",
]
