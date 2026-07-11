"""Simple id/title list model for pickers (parent, group, …)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt


@dataclass(slots=True)
class PickerRow:
    id: int
    title: str


class PickerModel(QAbstractListModel):
    IdRole = Qt.ItemDataRole.UserRole + 1
    TitleRole = Qt.ItemDataRole.UserRole + 2

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._items: list[PickerRow] = []

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
        if role in (self.TitleRole, Qt.ItemDataRole.DisplayRole):
            return item.title
        return None

    def roleNames(self) -> dict[int, bytes]:  # noqa: N802
        return {self.IdRole: b"taskId", self.TitleRole: b"title"}

    def reset_items(self, items: list[PickerRow]) -> None:
        self.beginResetModel()
        self._items = list(items)
        self.endResetModel()
