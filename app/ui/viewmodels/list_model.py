"""QAbstractListModel of task lists for QML."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt

from app.domain.models import TaskList


class ListModel(QAbstractListModel):
    IdRole = Qt.ItemDataRole.UserRole + 1
    NameRole = Qt.ItemDataRole.UserRole + 2
    IsSystemRole = Qt.ItemDataRole.UserRole + 3
    IconRole = Qt.ItemDataRole.UserRole + 4

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._items: list[TaskList] = []

    def rowCount(self, parent: QModelIndex | None = None) -> int:  # noqa: N802
        if parent is not None and parent.isValid():
            return 0
        return len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return None
        item = self._items[index.row()]
        if role in (self.IdRole, Qt.ItemDataRole.UserRole):
            return item.id
        if role in (self.NameRole, Qt.ItemDataRole.DisplayRole):
            return item.name
        if role == self.IsSystemRole:
            return item.is_system
        if role == self.IconRole:
            return item.icon
        return None

    def roleNames(self) -> dict[int, bytes]:  # noqa: N802
        return {
            self.IdRole: b"listId",
            self.NameRole: b"name",
            self.IsSystemRole: b"isSystem",
            self.IconRole: b"listIcon",
        }

    def reset_items(self, items: list[TaskList]) -> None:
        self.beginResetModel()
        self._items = list(items)
        self.endResetModel()
