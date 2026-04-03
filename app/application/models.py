"""Transport-neutral rows shared by the desktop UI and external adapters."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TaskRow:
    id: int
    title: str
    description: str
    mode: str
    time_today: str
    work_state: str
    can_start: bool
    can_pause: bool
    can_stop: bool
    depth: int
    is_nested: bool
    is_last_sibling: bool
    ancestor_continues: tuple[bool, ...]
    has_children: bool
    is_expanded: bool
    kind: str = "timed"
    is_completed: bool = False
    can_complete: bool = False
    is_scheduled_today: bool = False


@dataclass(slots=True)
class WorkRow:
    task_id: int
    title: str
    state: str
    clock: str
    is_countdown: bool
    progress: float | None = None
    blocked_by_descendant: bool = False


@dataclass(slots=True)
class HistoryRow:
    id: int
    task_id: int
    title: str
    kind: str
    completion_kind: str
    completion_date: str
    completed_at: str
    started_at: str
    ended_at: str
    duration: str
    note: str
    is_timed: bool
