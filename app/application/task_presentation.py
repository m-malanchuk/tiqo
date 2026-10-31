"""Build transport-neutral task and work rows from application state."""

from __future__ import annotations

from app.application.models import TaskRow, WorkRow
from app.domain.formatting import format_duration, format_session_clock, session_progress
from app.domain.models import (
    LIST_ALL_ID,
    LIST_FAVORITES_ID,
    LIST_IN_WORK_ID,
    LIST_KEY_ALL,
    LIST_TODAY_ID,
    Task,
    TaskKind,
    TimerMode,
    WorkState,
)
from app.domain.recurrence import is_due_on
from app.domain.timeutil import local_today
from app.i18n import tr
from app.services.task_tree import build_task_forest, filter_collapsed, index_links
from app.services.timer_engine import TimerEngine
from app.storage.assignment_repo import AssignmentRepo
from app.storage.completion_repo import CompletionRepo
from app.storage.list_repo import ListRepo
from app.storage.recurrence_repo import RecurrenceRepo
from app.storage.task_repo import TaskRepo
from app.storage.work_repo import WorkRepo


def task_clock_label(
    *, engine: TimerEngine, work_repo: WorkRepo, tasks_repo: TaskRepo, task_id: int
) -> str:
    session = engine.open_session_for(task_id)
    if session is not None:
        return format_session_clock(engine.elapsed_seconds(session), session.target_seconds)
    work = work_repo.get(task_id)
    if work is not None:
        return tr("status.paused")
    task = tasks_repo.get(task_id)
    if (
        task is not None
        and task.default_mode is TimerMode.COUNTDOWN
        and task.default_target_seconds
        and task.default_target_seconds > 0
    ):
        return format_duration(task.default_target_seconds)
    return format_duration(0)


def build_work_rows(
    *, engine: TimerEngine, work_repo: WorkRepo, tasks_repo: TaskRepo
) -> list[WorkRow]:
    items = sorted(
        work_repo.list_all(),
        key=lambda item: (
            0 if item.state is WorkState.RUNNING else 1,
            item.position,
            item.task_id,
        ),
    )
    running_ids = {item.task_id for item in items if item.state is WorkState.RUNNING}
    rows: list[WorkRow] = []
    for work in items:
        task = tasks_repo.get(work.task_id)
        session = engine.open_session_for(work.task_id)
        if session is not None:
            elapsed = engine.elapsed_seconds(session)
            clock = format_session_clock(elapsed, session.target_seconds)
            is_countdown = session.target_seconds is not None
            progress = session_progress(elapsed, session.target_seconds)
        else:
            clock = tr("status.paused")
            is_countdown = False
            progress = None
        blocked = bool(
            work.state is WorkState.PAUSED
            and running_ids
            and tasks_repo.descendant_ids(work.task_id) & running_ids
        )
        rows.append(
            WorkRow(
                task_id=work.task_id,
                title=task.title if task else f"#{work.task_id}",
                state=work.state.value,
                clock=clock,
                is_countdown=is_countdown,
                progress=progress,
                blocked_by_descendant=blocked,
            )
        )
    return rows


def seed_tasks_for_list(
    *,
    selected_list_id: int,
    lists_repo: ListRepo,
    tasks_repo: TaskRepo,
    work_repo: WorkRepo,
    recurrence_repo: RecurrenceRepo,
    assignment_repo: AssignmentRepo | None = None,
    completion_repo: CompletionRepo | None = None,
) -> list[Task]:
    selected = lists_repo.get(selected_list_id)
    is_all = selected_list_id == LIST_ALL_ID or (
        selected is not None and selected.key == LIST_KEY_ALL
    )
    if is_all:
        return tasks_repo.list_all()
    if selected_list_id == LIST_TODAY_ID:
        today = local_today()
        recurring_ids = {
            rule.task_id for rule in recurrence_repo.list_active() if is_due_on(rule, today)
        }
        assigned_ids = set(assignment_repo.task_ids_on(today)) if assignment_repo else set()
        ids = sorted(recurring_ids | assigned_ids)
        completed_today: set[int] = set()
        if completion_repo is not None:
            completed_today.update(completion_repo.task_ids_checklist_completed_on(today))
            completed_today.update(completion_repo.task_ids_timed_completed_on(today))
        ids = [task_id for task_id in ids if task_id not in completed_today]
        return tasks_repo.list_by_ids(ids)
    if selected_list_id == LIST_IN_WORK_ID:
        return tasks_repo.list_by_ids([item.task_id for item in work_repo.list_all()])
    if selected_list_id == LIST_FAVORITES_ID:
        return [task for task in tasks_repo.list_all() if task.is_favorite]
    return tasks_repo.list_by_list(selected_list_id)


def build_task_rows(
    *,
    engine: TimerEngine,
    work_repo: WorkRepo,
    tasks_repo: TaskRepo,
    seed_tasks: list[Task],
    collapsed_task_ids: set[int],
    assignment_repo: AssignmentRepo | None = None,
    recurrence_repo: RecurrenceRepo | None = None,
    today_occurrence: bool = False,
) -> list[TaskRow]:
    work_by_id = {item.task_id: item for item in work_repo.list_all()}
    open_ids = {session.task_id for session in engine.open_sessions()}
    all_tasks = {task.id: task for task in tasks_repo.list_all()}
    children, parents = index_links(tasks_repo.parent_child_pairs())
    today_ids: set[int] = set()
    if assignment_repo is not None:
        today_ids.update(assignment_repo.task_ids_on(local_today()))
    if recurrence_repo is not None:
        today_ids.update(
            rule.task_id for rule in recurrence_repo.list_active() if is_due_on(rule, local_today())
        )
    forest = filter_collapsed(
        build_task_forest(
            seed_tasks=seed_tasks,
            all_tasks=all_tasks,
            children_of=children,
            parents_of=parents,
        ),
        collapsed_task_ids,
    )
    return [
        TaskRow(
            id=node.task.id,
            title=node.task.title,
            description=node.task.description,
            mode=node.task.default_mode.value,
            time_today=task_clock_label(
                engine=engine,
                work_repo=work_repo,
                tasks_repo=tasks_repo,
                task_id=node.task.id,
            ),
            work_state=(work_by_id[node.task.id].state.value if node.task.id in work_by_id else ""),
            can_start=(node.task.kind is TaskKind.TIMED and node.task.id not in open_ids),
            can_pause=(node.task.kind is TaskKind.TIMED and node.task.id in open_ids),
            can_stop=(node.task.kind is TaskKind.TIMED and node.task.id in work_by_id),
            depth=node.depth,
            is_nested=node.depth > 0,
            is_last_sibling=node.is_last_sibling,
            ancestor_continues=node.ancestor_continues,
            has_children=node.has_children,
            is_expanded=node.task.id not in collapsed_task_ids,
            kind=node.task.kind.value,
            is_completed=(
                False
                if today_occurrence and node.task.kind is TaskKind.CHECKLIST
                else node.task.is_completed
            ),
            can_complete=node.task.kind is TaskKind.CHECKLIST,
            is_scheduled_today=(node.task.id in today_ids),
        )
        for node in forest
    ]
