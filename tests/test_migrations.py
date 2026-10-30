"""Migration runner tests."""

from __future__ import annotations

import sqlite3

import pytest
from app.storage.connection import connect_memory
from app.storage.list_repo import ListRepo
from app.storage.migrations import apply_migrations, current_version


def test_apply_migrations_seeds_system_lists() -> None:
    conn = connect_memory()
    version = apply_migrations(conn)
    assert version == 11
    assert current_version(conn) == 11

    lists = ListRepo(conn).list_all()
    keys = [item.key for item in lists]
    assert keys[0] == "all"
    assert "favorites" in keys and "today" in keys and "in_work" in keys
    assert all(item.is_system for item in lists if item.key)
    assert all(item.icon for item in lists)


def test_apply_migrations_is_idempotent() -> None:
    conn = connect_memory()
    assert apply_migrations(conn) == 11
    assert apply_migrations(conn) == 11

    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    }
    assert "sessions" in tables
    assert "work_items" in tables
    assert "task_links" not in tables
    assert "schema_version" in tables
    assert "task_completions" in tables
    cols = {row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
    assert "parent_task_id" in cols
    assert {"task_kind", "checklist_done", "checklist_completed_at"} <= cols
    assert "session_intervals" in tables
    assert "task_assignments" in tables
    assert "completion_intervals" in tables
    kind_sql = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'task_recurrence'"
    ).fetchone()[0]
    assert "monthly" in kind_sql


def test_foreign_keys_enforced(conn: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO tasks (
                list_id, title, description, default_mode, is_favorite, is_archived, created_at
            ) VALUES (999, 'x', '', 'stopwatch', 0, 0, '2024-01-01T00:00:00+00:00')
            """
        )


def test_failed_migration_rolls_back_its_schema_and_version(tmp_path) -> None:
    (tmp_path / "001_ok.sql").write_text("CREATE TABLE stable (id INTEGER);", encoding="utf-8")
    (tmp_path / "002_bad.sql").write_text(
        "CREATE TABLE partial (id INTEGER); THIS IS NOT SQL;",
        encoding="utf-8",
    )
    conn = connect_memory()

    with pytest.raises(sqlite3.Error):
        apply_migrations(conn, tmp_path)

    assert current_version(conn) == 1
    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    }
    assert "stable" in tables
    assert "partial" not in tables
