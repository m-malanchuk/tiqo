"""Task repository."""

from __future__ import annotations

import sqlite3
from datetime import datetime

from app.domain.models import Task, TaskKind, TimerMode
from app.domain.timeutil import dt_from_db, dt_to_db, utc_now
from app.storage.transaction import write

_TASK_COLS = """
    id, list_id, title, description, default_mode, default_target_seconds,
    is_favorite, is_archived, created_at, parent_task_id,
    task_kind, checklist_done, checklist_completed_at
"""


class TaskRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get(self, task_id: int) -> Task | None:
        row = self._conn.execute(
            f"SELECT {_TASK_COLS} FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()
        return None if row is None else _task_from_row(row)

    def list_by_list(self, list_id: int, *, include_archived: bool = False) -> list[Task]:
        sql = f"SELECT {_TASK_COLS} FROM tasks WHERE list_id = ?"
        params: list[object] = [list_id]
        if not include_archived:
            sql += " AND is_archived = 0"
        sql += " ORDER BY id"
        rows = self._conn.execute(sql, params).fetchall()
        return [_task_from_row(row) for row in rows]

    def list_by_ids(self, task_ids: list[int]) -> list[Task]:
        if not task_ids:
            return []
        placeholders = ",".join("?" for _ in task_ids)
        rows = self._conn.execute(
            f"SELECT {_TASK_COLS} FROM tasks WHERE id IN ({placeholders})",
            task_ids,
        ).fetchall()
        by_id = {int(row["id"]): _task_from_row(row) for row in rows}
        return [by_id[i] for i in task_ids if i in by_id]

    def list_all(self, *, include_archived: bool = False) -> list[Task]:
        sql = f"SELECT {_TASK_COLS} FROM tasks"
        if not include_archived:
            sql += " WHERE is_archived = 0"
        sql += " ORDER BY title COLLATE NOCASE, id"
        rows = self._conn.execute(sql).fetchall()
        return [_task_from_row(row) for row in rows]

    def delete(self, task_id: int) -> None:
        with write(self._conn):
            self._conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    def set_parent(self, task_id: int, parent_task_id: int | None) -> Task:
        if parent_task_id is not None and parent_task_id == task_id:
            raise ValueError("A task cannot be its own parent")
        if parent_task_id is not None and parent_task_id in self.descendant_ids(task_id):
            raise ValueError("Cannot set a descendant as parent (cycle)")
        with write(self._conn):
            self._conn.execute(
                "UPDATE tasks SET parent_task_id = ? WHERE id = ?",
                (parent_task_id, task_id),
            )
        task = self.get(task_id)
        assert task is not None
        return task

    def children_of(self, parent_task_id: int) -> list[int]:
        rows = self._conn.execute(
            """
            SELECT id FROM tasks
            WHERE parent_task_id = ? AND is_archived = 0
            ORDER BY title COLLATE NOCASE, id
            """,
            (parent_task_id,),
        ).fetchall()
        return [int(row["id"]) for row in rows]

    def parent_of(self, task_id: int) -> int | None:
        task = self.get(task_id)
        return None if task is None else task.parent_task_id

    def ancestor_ids(self, task_id: int) -> set[int]:
        found: set[int] = set()
        current = self.parent_of(task_id)
        while current is not None and current not in found:
            found.add(current)
            current = self.parent_of(current)
        return found

    def descendant_ids(self, task_id: int) -> set[int]:
        found: set[int] = set()
        stack = list(self.children_of(task_id))
        while stack:
            child = stack.pop()
            if child in found:
                continue
            found.add(child)
            stack.extend(self.children_of(child))
        return found

    def parent_child_pairs(self) -> list[tuple[int, int]]:
        rows = self._conn.execute(
            """
            SELECT parent_task_id, id FROM tasks
            WHERE parent_task_id IS NOT NULL AND is_archived = 0
            """
        ).fetchall()
        return [(int(row["parent_task_id"]), int(row["id"])) for row in rows]

    def update(
        self,
        task_id: int,
        *,
        title: str | None = None,
        description: str | None = None,
        kind: TaskKind | None = None,
        default_mode: TimerMode | None = None,
        default_target_seconds: int | None = None,
        update_target: bool = False,
        is_archived: bool | None = None,
        list_id: int | None = None,
    ) -> Task:
        task = self.get(task_id)
        if task is None:
            raise KeyError(f"Task {task_id} not found")

        new_title = task.title if title is None else title
        new_description = task.description if description is None else description
        new_kind = task.kind if kind is None else kind
        new_mode = task.default_mode if default_mode is None else default_mode
        new_target = default_target_seconds if update_target else task.default_target_seconds
        new_archived = task.is_archived if is_archived is None else is_archived
        new_list_id = task.list_id if list_id is None else list_id

        if new_kind is TaskKind.CHECKLIST:
            new_mode = TimerMode.STOPWATCH
            new_target = None
            new_checklist_done = task.is_completed
            new_checklist_completed_at = task.completed_at
        else:
            # A task changed back to timed must not resurrect a stale binary
            # completion if it is later switched to checklist again.
            new_checklist_done = False
            new_checklist_completed_at = None

        with write(self._conn):
            self._conn.execute(
                """
                UPDATE tasks SET
                    list_id = ?,
                    title = ?,
                    description = ?,
                    task_kind = ?,
                    default_mode = ?,
                    default_target_seconds = ?,
                    is_archived = ?,
                    checklist_done = ?,
                    checklist_completed_at = ?
                WHERE id = ?
                """,
                (
                    new_list_id,
                    new_title,
                    new_description,
                    new_kind.value,
                    new_mode.value,
                    new_target,
                    int(new_archived),
                    int(new_checklist_done),
                    None
                    if new_checklist_completed_at is None
                    else dt_to_db(new_checklist_completed_at),
                    task_id,
                ),
            )
        updated = self.get(task_id)
        assert updated is not None
        return updated

    def set_checklist_state(
        self,
        task_id: int,
        *,
        is_completed: bool,
        completed_at: datetime | None,
    ) -> Task:
        """Persist the current binary state without touching task metadata."""
        task = self.get(task_id)
        if task is None:
            raise KeyError(f"Task {task_id} not found")
        if task.kind is not TaskKind.CHECKLIST:
            raise ValueError("Only checklist tasks have a completion state")
        with write(self._conn):
            self._conn.execute(
                """
                UPDATE tasks
                SET checklist_done = ?, checklist_completed_at = ?
                WHERE id = ?
                """,
                (
                    int(is_completed),
                    None if completed_at is None else dt_to_db(completed_at),
                    task_id,
                ),
            )
        updated = self.get(task_id)
        assert updated is not None
        return updated

    def create(
        self,
        list_id: int,
        title: str,
        *,
        description: str = "",
        kind: TaskKind = TaskKind.TIMED,
        default_mode: TimerMode = TimerMode.STOPWATCH,
        default_target_seconds: int | None = None,
        is_favorite: bool = False,
        created_at: datetime | None = None,
        parent_task_id: int | None = None,
    ) -> Task:
        created = created_at or utc_now()
        if kind is TaskKind.CHECKLIST:
            default_mode = TimerMode.STOPWATCH
            default_target_seconds = None
        with write(self._conn):
            cur = self._conn.execute(
                """
                INSERT INTO tasks (
                    list_id, title, description, default_mode, default_target_seconds,
                    is_favorite, is_archived, created_at, parent_task_id,
                    task_kind, checklist_done, checklist_completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?, 0, NULL)
                """,
                (
                    list_id,
                    title,
                    description,
                    default_mode.value,
                    default_target_seconds,
                    int(is_favorite),
                    dt_to_db(created),
                    parent_task_id,
                    kind.value,
                ),
            )
            task_id = cur.lastrowid
            if task_id is None:
                raise RuntimeError("INSERT INTO tasks did not return an id")
        task = self.get(int(task_id))
        assert task is not None
        return task


def _task_from_row(row: sqlite3.Row) -> Task:
    parent_raw = row["parent_task_id"]
    return Task(
        id=int(row["id"]),
        list_id=int(row["list_id"]),
        title=str(row["title"]),
        description=str(row["description"] or ""),
        kind=TaskKind(str(row["task_kind"])),
        default_mode=TimerMode(row["default_mode"]),
        default_target_seconds=(
            None if row["default_target_seconds"] is None else int(row["default_target_seconds"])
        ),
        is_favorite=bool(row["is_favorite"]),
        is_archived=bool(row["is_archived"]),
        created_at=dt_from_db(str(row["created_at"])),
        parent_task_id=None if parent_raw is None else int(parent_raw),
        is_completed=bool(row["checklist_done"]),
        completed_at=(
            None
            if row["checklist_completed_at"] is None
            else dt_from_db(str(row["checklist_completed_at"]))
        ),
    )
