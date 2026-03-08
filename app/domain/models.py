"""Domain dataclasses and enums. No Qt, no SQL."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class TimerMode(StrEnum):
    STOPWATCH = "stopwatch"
    COUNTDOWN = "countdown"


class TaskKind(StrEnum):
    """Whether a task tracks elapsed time or a binary completion state."""

    TIMED = "timed"
    CHECKLIST = "checklist"


class EndReason(StrEnum):
    STOPPED = "stopped"
    PAUSED = "paused"
    CRASH_RECOVERED = "crash_recovered"


class CompletionKind(StrEnum):
    MANUAL_STOP = "manual_stop"
    TARGET_REACHED = "target_reached"
    CHECKLIST = "checklist"


class RecurrenceKind(StrEnum):
    NONE = "none"
    DAILY = "daily"
    EVERY_N_DAYS = "every_n_days"
    WEEKLY = "weekly"
    MONTHLY = "monthly"  # day-of-month in ``interval`` (1–31; clamp on short months)


@dataclass(frozen=True, slots=True)
class TaskRecurrence:
    task_id: int
    kind: RecurrenceKind
    interval: int | None = None  # every_n_days: N; monthly: day of month
    weekdays_mask: int | None = None  # bit0=Mon … bit6=Sun
    anchor_date: date | None = None  # every_n_days epoch (local calendar date)


class WorkState(StrEnum):
    RUNNING = "running"
    PAUSED = "paused"


@dataclass(frozen=True, slots=True)
class TaskList:
    id: int
    name: str
    position: int
    is_system: bool
    key: str | None = None
    icon: str = "📁"
    description: str = ""


@dataclass(frozen=True, slots=True)
class Task:
    id: int
    list_id: int
    title: str
    description: str
    kind: TaskKind
    default_mode: TimerMode
    default_target_seconds: int | None
    is_completed: bool
    completed_at: datetime | None
    is_favorite: bool
    is_archived: bool
    created_at: datetime
    parent_task_id: int | None = None


@dataclass(frozen=True, slots=True)
class Session:
    id: int
    task_id: int
    started_at: datetime
    ended_at: datetime | None
    last_seen_at: datetime
    target_seconds: int | None
    end_reason: EndReason | None
    note: str = ""

    @property
    def is_open(self) -> bool:
        return self.ended_at is None


@dataclass(frozen=True, slots=True)
class SessionInterval:
    """A single period when a session was actively running."""

    id: int
    session_id: int
    started_at: datetime
    ended_at: datetime | None

    @property
    def is_open(self) -> bool:
        return self.ended_at is None


@dataclass(frozen=True, slots=True)
class WorkItem:
    task_id: int
    state: WorkState
    position: int
    activated_at: datetime


@dataclass(frozen=True, slots=True)
class DailyStat:
    task_id: int
    date: date
    total_seconds: int
    sessions_count: int


@dataclass(frozen=True, slots=True)
class TaskCompletion:
    id: int
    task_id: int
    session_id: int | None
    completed_at: datetime
    completion_date: date
    kind: CompletionKind
    note: str = ""
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_seconds: int | None = None


@dataclass(frozen=True, slots=True)
class CompletionInterval:
    id: int
    completion_id: int
    started_at: datetime
    ended_at: datetime


HEARTBEAT_INTERVAL_SECONDS = 10

# Fixed system list ids
LIST_ALL_ID = 4
LIST_FAVORITES_ID = 1
LIST_TODAY_ID = 2
LIST_IN_WORK_ID = 3

LIST_KEY_ALL = "all"

# System lists without user description
LISTS_WITHOUT_DESCRIPTION = frozenset({LIST_FAVORITES_ID, LIST_TODAY_ID, LIST_ALL_ID})
