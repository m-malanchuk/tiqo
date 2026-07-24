"""Rich showcase database for manual UI checks during development."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.domain.models import (
    LIST_FAVORITES_ID,
    CompletionKind,
    EndReason,
    RecurrenceKind,
    TaskKind,
    TaskRecurrence,
    TimerMode,
    WorkState,
)
from app.domain.recurrence import weekday_bit
from app.domain.timeutil import local_today
from app.services.task_service import TaskService
from app.storage.assignment_repo import AssignmentRepo
from app.storage.completion_repo import CompletionRepo
from app.storage.db import open_database
from app.storage.list_repo import ListRepo
from app.storage.paths import data_dir
from app.storage.recurrence_repo import RecurrenceRepo
from app.storage.session_repo import SessionRepo
from app.storage.stats_repo import StatsRepo
from app.storage.task_repo import TaskRepo
from app.storage.work_repo import WorkRepo


def showcase_db_path() -> Path:
    return data_dir() / "demo.db"


def reset_showcase_db(*, now: datetime | None = None) -> Path:
    """Delete and recreate ``~/.local/share/tiqo/demo.db`` with sample entities."""
    path = showcase_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    conn = open_database(path)
    try:
        seed_showcase(conn, now=now)
    finally:
        conn.close()
    return path


def seed_showcase(conn: sqlite3.Connection, *, now: datetime | None = None) -> None:
    """Fill an already-migrated connection with a visible demo graph."""
    stamp = now or datetime.now(UTC).replace(microsecond=0)
    lists = ListRepo(conn)
    tasks = TaskRepo(conn)
    sessions = SessionRepo(conn)
    work = WorkRepo(conn)
    stats = StatsRepo(conn)
    completions = CompletionRepo(conn)
    assignments = AssignmentRepo(conn)
    recurrence = RecurrenceRepo(conn)
    task_svc = TaskService(conn)
    today = stamp.astimezone().date() if stamp.tzinfo else local_today()

    study = lists.create("Учёба", position=10, icon="📚", description="Учёба и языки")
    job = lists.create("Работа", position=11, icon="💼", description="Рабочие задачи")

    english = tasks.create(
        LIST_FAVORITES_ID,
        "Английский",
        description="Общая цель: язык. Сессии с разными заметками — это заходы, не отдельные цели.",
        is_favorite=True,
        created_at=stamp - timedelta(days=10),
    )
    grammar = tasks.create(
        study.id,
        "Грамматика",
        description="Дочерняя задача под «Английский».",
        default_mode=TimerMode.STOPWATCH,
        created_at=stamp - timedelta(days=9),
    )
    vocab = tasks.create(
        study.id,
        "Лексика",
        description="Ещё один ребёнок «Английского».",
        created_at=stamp - timedelta(days=9),
    )
    task_svc.set_parent(grammar.id, english.id)
    task_svc.set_parent(vocab.id, english.id)

    present = tasks.create(
        study.id,
        "Present Perfect",
        description="Подзадача грамматики — третий уровень вложенности.",
        created_at=stamp - timedelta(days=8),
    )
    articles = tasks.create(
        study.id,
        "Артикли a/the",
        description="Ещё одна подзадача под «Грамматика».",
        created_at=stamp - timedelta(days=8),
    )
    task_svc.set_parent(present.id, grammar.id)
    task_svc.set_parent(articles.id, grammar.id)

    coding = tasks.create(
        LIST_FAVORITES_ID,
        "Код tiqo",
        description="Разработка трекера",
        is_favorite=True,
        created_at=stamp - timedelta(days=5),
    )
    review = tasks.create(
        job.id,
        "Ревью",
        description="Разбор чужого кода",
        created_at=stamp - timedelta(days=4),
    )
    pomodoro = tasks.create(
        LIST_FAVORITES_ID,
        "Помодоро",
        description="Таймер на 25 минут по умолчанию",
        default_mode=TimerMode.COUNTDOWN,
        default_target_seconds=25 * 60,
        is_favorite=True,
        created_at=stamp - timedelta(days=3),
    )
    bills = tasks.create(
        job.id,
        "Оплата счетов",
        description="Раз в месяц в тот же день числа",
        created_at=stamp - timedelta(days=40),
    )
    checklist = tasks.create(
        LIST_FAVORITES_ID,
        "Подготовить документы",
        description="Бинарная задача: либо выполнено, либо нет — без таймера.",
        kind=TaskKind.CHECKLIST,
        is_favorite=True,
        created_at=stamp - timedelta(days=2),
    )
    checklist_done = tasks.create(
        job.id,
        "Отправить отчёт",
        description="Демонстрация выполненной бинарной задачи.",
        kind=TaskKind.CHECKLIST,
        created_at=stamp - timedelta(days=2),
    )
    task_svc.set_checklist_done(checklist_done.id, now=stamp - timedelta(days=1, hours=2))
    assignments.assign(checklist.id, today, created_at=stamp)
    assignments.assign(coding.id, today + timedelta(days=1), created_at=stamp)

    # Extra flat tasks so «Избранное» / «Все» need real scrolling in a small window
    scroll_titles = (
        "Черновик письма",
        "Разбор логов",
        "Обновить README",
        "Созвон с командой",
        "Настроить бэкап",
        "Проверить CI",
        "Заметки с митинга",
        "Рефакторинг форм",
        "Тест трея",
        "Иконки hicolor",
        "Документация API",
        "План спринта",
        "Инбокс: разобрать",
        "Купить лампочку",
        "Прогулка 20 мин",
    )
    for i, title in enumerate(scroll_titles):
        tasks.create(
            LIST_FAVORITES_ID if i % 2 == 0 else job.id,
            title,
            description=f"Демо-задача для прокрутки #{i + 1}",
            is_favorite=(i % 2 == 0),
            created_at=stamp - timedelta(days=1, minutes=i),
        )

    # Past sessions on English (same task, different notes — chart entity is one)
    _closed_session(
        sessions,
        completions,
        english.id,
        started=stamp - timedelta(days=3, hours=2),
        seconds=40 * 60,
        note="слушать подкаст",
    )
    _closed_session(
        sessions,
        completions,
        english.id,
        started=stamp - timedelta(days=2, hours=1),
        seconds=25 * 60,
        note="учить слова",
    )
    _closed_session(
        sessions,
        completions,
        grammar.id,
        started=stamp - timedelta(days=1, hours=3),
        seconds=55 * 60,
        note="обзор времён",
    )
    _closed_session(
        sessions,
        completions,
        present.id,
        started=stamp - timedelta(hours=30),
        seconds=40 * 60,
        note="упражнения Present Perfect",
    )
    _closed_session(
        sessions,
        completions,
        vocab.id,
        started=stamp - timedelta(hours=20),
        seconds=30 * 60,
        note="Anki: 40 карточек",
    )
    # Keep demo «done today» at 0 — history is yesterday+, so Favorites
    # counter starts at [0] until the user Stops something.
    _closed_session(
        sessions,
        completions,
        coding.id,
        started=stamp - timedelta(days=1, hours=6),
        seconds=90 * 60,
        note="попапы старта и редактирование",
    )
    _closed_session(
        sessions,
        completions,
        review.id,
        started=stamp - timedelta(days=1, hours=5),
        seconds=35 * 60,
        note="PR #12",
    )

    # Recurrence → «Сегодня» (same tasks can also sit in «В работе»)
    recurrence.upsert(TaskRecurrence(task_id=english.id, kind=RecurrenceKind.DAILY))
    recurrence.upsert(
        TaskRecurrence(
            task_id=coding.id,
            kind=RecurrenceKind.WEEKLY,
            weekdays_mask=weekday_bit(today.isoweekday()),
        )
    )
    recurrence.upsert(
        TaskRecurrence(
            task_id=pomodoro.id,
            kind=RecurrenceKind.EVERY_N_DAYS,
            interval=2,
            anchor_date=today,  # due today
        )
    )
    recurrence.upsert(
        TaskRecurrence(
            task_id=bills.id,
            kind=RecurrenceKind.MONTHLY,
            interval=today.day,
        )
    )
    # Grammar: every 3 days, anchor yesterday → not due today (contrast)
    recurrence.upsert(
        TaskRecurrence(
            task_id=grammar.id,
            kind=RecurrenceKind.EVERY_N_DAYS,
            interval=3,
            anchor_date=today - timedelta(days=1),
        )
    )

    # «В работе»:
    # - Английский paused (blocked in widget while child Грамматика runs)
    # - Грамматика running stopwatch
    # - Код tiqo paused stopwatch
    # - Помодоро running countdown (~8 of 25 min) for progress-bar fill
    work.upsert(
        english.id,
        WorkState.PAUSED,
        activated_at=stamp - timedelta(minutes=15),
        position=0,
    )
    sessions.create(
        grammar.id,
        started_at=stamp - timedelta(minutes=3),
        note="Демо: ребёнок бежит — родитель скрыт в виджете",
    )
    work.upsert(
        grammar.id,
        WorkState.RUNNING,
        activated_at=stamp - timedelta(minutes=3),
        position=1,
    )
    work.upsert(
        coding.id,
        WorkState.PAUSED,
        activated_at=stamp - timedelta(minutes=10),
        position=2,
    )
    sessions.create(
        pomodoro.id,
        started_at=stamp - timedelta(minutes=8),
        target_seconds=25 * 60,
        note="Демо: открытый помодоро",
    )
    work.upsert(
        pomodoro.id,
        WorkState.RUNNING,
        activated_at=stamp - timedelta(minutes=8),
        position=3,
    )

    stats.rebuild_from_sessions()


def _closed_session(
    sessions: SessionRepo,
    completions: CompletionRepo,
    task_id: int,
    *,
    started: datetime,
    seconds: int,
    note: str,
) -> None:
    row = sessions.create(task_id, started_at=started, note=note)
    sessions.close(
        row.id,
        ended_at=started + timedelta(seconds=seconds),
        end_reason=EndReason.STOPPED,
    )
    completions.create_from_session(
        task_id,
        session_id=row.id,
        completed_at=started + timedelta(seconds=seconds),
        kind=CompletionKind.MANUAL_STOP,
    )
