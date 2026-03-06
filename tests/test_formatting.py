"""Duration formatting helpers."""

from __future__ import annotations

from app.domain.formatting import format_duration, format_session_clock, session_progress


def test_format_duration() -> None:
    assert format_duration(0) == "0:00"
    assert format_duration(5) == "0:05"
    assert format_duration(65) == "1:05"
    assert format_duration(3600) == "1:00:00"
    assert format_duration(1500) == "25:00"


def test_format_session_clock() -> None:
    assert format_session_clock(90, None) == "1:30"
    assert format_session_clock(90, 120) == "0:30"
    assert format_session_clock(130, 120) == "+0:10"


def test_session_progress() -> None:
    assert session_progress(30, None) is None
    assert session_progress(0, 100) == 0.0
    assert session_progress(50, 100) == 0.5
    assert session_progress(100, 100) == 1.0
    assert session_progress(150, 100) == 1.5
    assert session_progress(10, 0) == 1.0
