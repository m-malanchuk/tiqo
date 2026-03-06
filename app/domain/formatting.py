"""Pure display helpers (no Qt)."""

from __future__ import annotations


def format_duration(total_seconds: int) -> str:
    """Format a non-negative duration as H:MM:SS or M:SS for short spans."""
    seconds = max(0, int(total_seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_session_clock(elapsed_seconds: int, target_seconds: int | None) -> str:
    """Stopwatch ``M:SS``, countdown remaining, or overtime ``+M:SS``."""
    elapsed = max(0, int(elapsed_seconds))
    if target_seconds is None:
        return format_duration(elapsed)
    remaining = int(target_seconds) - elapsed
    if remaining >= 0:
        return format_duration(remaining)
    return f"+{format_duration(-remaining)}"


def session_progress(elapsed_seconds: int, target_seconds: int | None) -> float | None:
    """Fraction of countdown filled (may exceed 1.0 in overtime).

    Stopwatch sessions have no target → ``None`` (indeterminate / empty bar).
    """
    if target_seconds is None:
        return None
    target = int(target_seconds)
    if target <= 0:
        return 1.0
    return max(0, int(elapsed_seconds)) / target
