"""Emoji grid model for the picker."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt

from app.domain.emoji_catalog import EmojiItem, filter_emojis


class EmojiModel(QAbstractListModel):
    GlyphRole = Qt.ItemDataRole.UserRole + 1
    CodesRole = Qt.ItemDataRole.UserRole + 2

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._items: list[EmojiItem] = filter_emojis("")

    def rowCount(self, parent: QModelIndex | None = None) -> int:  # noqa: N802
        if parent is not None and parent.isValid():
            return 0
        return len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return None
        item = self._items[index.row()]
        if role in (self.GlyphRole, Qt.ItemDataRole.DisplayRole):
            return item.glyph
        if role == self.CodesRole:
            return ", ".join(f":{c}:" for c in item.shortcodes)
        return None

    def roleNames(self) -> dict[int, bytes]:  # noqa: N802
        return {self.GlyphRole: b"glyph", self.CodesRole: b"codes"}

    def set_query(self, query: str) -> None:
        self.beginResetModel()
        self._items = filter_emojis(query)
        self.endResetModel()
