"""Recurrence rules for «Сегодня»."""

from __future__ import annotations

from datetime import date

from app.domain.models import RecurrenceKind, TaskRecurrence
from app.domain.recurrence import clamp_month_day, is_due_on, weekday_bit


def _rule(
    kind: RecurrenceKind,
    *,
    interval: int | None = None,
    weekdays_mask: int | None = None,
    anchor_date: date | None = None,
    task_id: int = 1,
) -> TaskRecurrence:
    return TaskRecurrence(
        task_id=task_id,
        kind=kind,
        interval=interval,
        weekdays_mask=weekdays_mask,
        anchor_date=anchor_date,
    )


def test_none_never_due() -> None:
    assert not is_due_on(_rule(RecurrenceKind.NONE), date(2024, 6, 15))


def test_daily_always_due() -> None:
    assert is_due_on(_rule(RecurrenceKind.DAILY), date(2024, 6, 15))


def test_every_n_days_from_anchor() -> None:
    anchor = date(2024, 6, 1)
    rule = _rule(RecurrenceKind.EVERY_N_DAYS, interval=2, anchor_date=anchor)
    assert is_due_on(rule, date(2024, 6, 1))
    assert not is_due_on(rule, date(2024, 6, 2))
    assert is_due_on(rule, date(2024, 6, 3))
    assert is_due_on(rule, date(2024, 7, 1))  # month rollover, 30 days → even
    assert not is_due_on(rule, date(2024, 5, 31))  # before anchor


def test_weekly_mask() -> None:
    # Monday + Wednesday
    mask = weekday_bit(1) | weekday_bit(3)
    rule = _rule(RecurrenceKind.WEEKLY, weekdays_mask=mask)
    assert is_due_on(rule, date(2024, 6, 17))  # Mon
    assert not is_due_on(rule, date(2024, 6, 18))  # Tue
    assert is_due_on(rule, date(2024, 6, 19))  # Wed


def test_monthly_day_and_short_month() -> None:
    rule = _rule(RecurrenceKind.MONTHLY, interval=31)
    assert is_due_on(rule, date(2024, 1, 31))
    assert not is_due_on(rule, date(2024, 1, 30))
    # Feb 2024 leap: 31 clamps to 29
    assert clamp_month_day(2024, 2, 31) == 29
    assert is_due_on(rule, date(2024, 2, 29))
    assert not is_due_on(rule, date(2024, 2, 28))
    # Feb 2023 non-leap → 28
    assert clamp_month_day(2023, 2, 31) == 28
    assert is_due_on(rule, date(2023, 2, 28))
