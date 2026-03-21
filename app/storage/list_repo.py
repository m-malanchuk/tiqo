"""List repository."""

from __future__ import annotations

import sqlite3

from app.domain.models import TaskList
from app.storage.transaction import write


class ListRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get(self, list_id: int) -> TaskList | None:
        row = self._conn.execute(
            """
            SELECT id, name, position, is_system, key, icon, description
            FROM lists WHERE id = ?
            """,
            (list_id,),
        ).fetchone()
        return None if row is None else _list_from_row(row)

    def list_all(self) -> list[TaskList]:
        rows = self._conn.execute(
            """
            SELECT id, name, position, is_system, key, icon, description
            FROM lists ORDER BY position, id
            """
        ).fetchall()
        return [_list_from_row(row) for row in rows]

    def create(
        self,
        name: str,
        *,
        position: int | None = None,
        icon: str = "📁",
        description: str = "",
    ) -> TaskList:
        if position is None:
            row = self._conn.execute("SELECT COALESCE(MAX(position), -1) + 1 FROM lists").fetchone()
            position = int(row[0])
        with write(self._conn):
            cur = self._conn.execute(
                """
                INSERT INTO lists (name, position, is_system, key, icon, description)
                VALUES (?, ?, 0, NULL, ?, ?)
                """,
                (name, position, icon, description),
            )
            list_id = cur.lastrowid
            if list_id is None:
                raise RuntimeError("INSERT INTO lists did not return an id")
        result = self.get(int(list_id))
        assert result is not None
        return result

    def update(
        self,
        list_id: int,
        *,
        name: str | None = None,
        icon: str | None = None,
        description: str | None = None,
    ) -> TaskList:
        current = self.get(list_id)
        if current is None:
            raise KeyError(f"List {list_id} not found")
        new_name = current.name if name is None else name
        new_icon = current.icon if icon is None else (icon.strip() or "📁")
        new_description = current.description if description is None else description
        with write(self._conn):
            self._conn.execute(
                """
                UPDATE lists SET name = ?, icon = ?, description = ?
                WHERE id = ?
                """,
                (new_name, new_icon, new_description, list_id),
            )
        result = self.get(list_id)
        assert result is not None
        return result

    def set_icon(self, list_id: int, icon: str) -> TaskList:
        return self.update(list_id, icon=icon)


def _list_from_row(row: sqlite3.Row) -> TaskList:
    key = row["key"]
    return TaskList(
        id=int(row["id"]),
        name=str(row["name"]),
        position=int(row["position"]),
        is_system=bool(row["is_system"]),
        key=None if key is None else str(key),
        icon=str(row["icon"] or "📁"),
        description=str(row["description"] or ""),
    )
