"""UTC helpers for wall-clock timestamps stored in SQLite."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta, tzinfo


def utc_now() -> datetime:
    return datetime.now(UTC)


def local_today() -> date:
    """Calendar date in the system local timezone (for «Сегодня» / recurrence)."""
    return datetime.now().astimezone().date()


def to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def dt_to_db(dt: datetime) -> str:
    return to_utc(dt).isoformat()


def dt_from_db(value: str) -> datetime:
    return to_utc(datetime.fromisoformat(value))


def date_to_db(value: date) -> str:
    return value.isoformat()


def date_from_db(value: str) -> date:
    return date.fromisoformat(value)


def seconds_by_local_day(
    started_at: datetime,
    ended_at: datetime,
    *,
    timezone: tzinfo | None = None,
) -> dict[date, int]:
    """Split a UTC interval across local calendar days.

    Local midnight boundaries are converted independently, so 23/25-hour DST
    days are handled without assuming that every date contains 86,400 seconds.
    """
    started = to_utc(started_at)
    ended = to_utc(ended_at)
    if ended <= started:
        return {}

    def localize_midnight(day: date) -> datetime:
        naive = datetime.combine(day, time.min)
        if timezone is None:
            return naive.astimezone().astimezone(UTC)
        return naive.replace(tzinfo=timezone).astimezone(UTC)

    local_start = started.astimezone(timezone).date()
    # Subtracting a microsecond keeps an interval ending exactly at midnight
    # from creating an empty bucket for the following day.
    local_end = (ended - timedelta(microseconds=1)).astimezone(timezone).date()
    result: dict[date, int] = {}
    day = local_start
    while day <= local_end:
        next_day = day + timedelta(days=1)
        overlap_start = max(started, localize_midnight(day))
        overlap_end = min(ended, localize_midnight(next_day))
        seconds = max(0, int((overlap_end - overlap_start).total_seconds()))
        if seconds:
            result[day] = seconds
        day = next_day
    return result
