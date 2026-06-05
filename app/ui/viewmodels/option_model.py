"""Simple string-option list model for settings combos."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt


@dataclass(slots=True)
class OptionRow:
    value: str
    title: str


class OptionModel(QAbstractListModel):
    ValueRole = Qt.ItemDataRole.UserRole + 1
    TitleRole = Qt.ItemDataRole.UserRole + 2

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._items: list[OptionRow] = []

    def rowCount(self, parent: QModelIndex | None = None) -> int:  # noqa: N802
        if parent is not None and parent.isValid():
            return 0
        return len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return None
        item = self._items[index.row()]
        if role in (self.TitleRole, Qt.ItemDataRole.DisplayRole):
            return item.title
        if role == self.ValueRole:
            return item.value
        return None

    def roleNames(self) -> dict[int, bytes]:  # noqa: N802
        return {
            self.ValueRole: b"value",
            self.TitleRole: b"title",
        }

    def reset_items(self, items: list[OptionRow]) -> None:
        self.beginResetModel()
        self._items = list(items)
        self.endResetModel()
