"""Pure recurrence rules for the «Сегодня» list (local calendar dates)."""

from __future__ import annotations

import calendar
from datetime import date

from app.domain.models import RecurrenceKind, TaskRecurrence


# bit0 = Monday … bit6 = Sunday (ISO weekday - 1)
def weekday_bit(iso_weekday: int) -> int:
    """ISO weekday 1=Mon … 7=Sun → mask bit."""
    if not 1 <= iso_weekday <= 7:
        raise ValueError(f"iso_weekday out of range: {iso_weekday}")
    return 1 << (iso_weekday - 1)


def mask_has_weekday(mask: int, iso_weekday: int) -> bool:
    return bool(mask & weekday_bit(iso_weekday))


def clamp_month_day(year: int, month: int, day: int) -> int:
    """Day-of-month clamped to the last day of that month (e.g. 31 → 28/29 in Feb)."""
    last = calendar.monthrange(year, month)[1]
    return min(max(1, day), last)


def is_due_on(rule: TaskRecurrence, on: date) -> bool:
    """Whether ``rule`` makes the task appear in «Сегодня» on local date ``on``."""
    kind = rule.kind
    if kind is RecurrenceKind.NONE:
        return False
    if kind is RecurrenceKind.DAILY:
        return True
    if kind is RecurrenceKind.EVERY_N_DAYS:
        n = int(rule.interval or 0)
        if n <= 0 or rule.anchor_date is None:
            return False
        delta = (on - rule.anchor_date).days
        if delta < 0:
            return False
        return delta % n == 0
    if kind is RecurrenceKind.WEEKLY:
        mask = int(rule.weekdays_mask or 0)
        if mask == 0:
            return False
        return mask_has_weekday(mask, on.isoweekday())
    if kind is RecurrenceKind.MONTHLY:
        day = int(rule.interval or 0)
        if not 1 <= day <= 31:
            return False
        return on.day == clamp_month_day(on.year, on.month, day)
    return False
