"""History rows for the completed-events window."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt

from app.application.models import HistoryRow


class HistoryModel(QAbstractListModel):
    IdRole = Qt.ItemDataRole.UserRole + 1
    TaskIdRole = Qt.ItemDataRole.UserRole + 2
    TitleRole = Qt.ItemDataRole.UserRole + 3
    KindRole = Qt.ItemDataRole.UserRole + 4
    CompletionKindRole = Qt.ItemDataRole.UserRole + 5
    CompletionDateRole = Qt.ItemDataRole.UserRole + 6
    CompletedAtRole = Qt.ItemDataRole.UserRole + 7
    StartRole = Qt.ItemDataRole.UserRole + 8
    EndRole = Qt.ItemDataRole.UserRole + 9
    DurationRole = Qt.ItemDataRole.UserRole + 10
    NoteRole = Qt.ItemDataRole.UserRole + 11
    TimedRole = Qt.ItemDataRole.UserRole + 12
    DayStartRole = Qt.ItemDataRole.UserRole + 13

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._items: list[HistoryRow] = []

    def rowCount(self, parent: QModelIndex | None = None) -> int:  # noqa: N802
        if parent is not None and parent.isValid():
            return 0
        return len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return None
        item = self._items[index.row()]
        values = {
            self.IdRole: item.id,
            self.TaskIdRole: item.task_id,
            self.TitleRole: item.title,
            self.KindRole: item.kind,
            self.CompletionKindRole: item.completion_kind,
            self.CompletionDateRole: item.completion_date,
            self.CompletedAtRole: item.completed_at,
            self.StartRole: item.started_at,
            self.EndRole: item.ended_at,
            self.DurationRole: item.duration,
            self.NoteRole: item.note,
            self.TimedRole: item.is_timed,
            self.DayStartRole: index.row() == 0
            or item.completion_date != self._items[index.row() - 1].completion_date,
            Qt.ItemDataRole.DisplayRole: item.title,
        }
        return values.get(role)

    def roleNames(self) -> dict[int, bytes]:  # noqa: N802
        return {
            self.IdRole: b"completionId",
            self.TaskIdRole: b"taskId",
            self.TitleRole: b"title",
            self.KindRole: b"kind",
            self.CompletionKindRole: b"completionKind",
            self.CompletionDateRole: b"completionDate",
            self.CompletedAtRole: b"completedAt",
            self.StartRole: b"startedAt",
            self.EndRole: b"endedAt",
            self.DurationRole: b"duration",
            self.NoteRole: b"note",
            self.TimedRole: b"isTimed",
            self.DayStartRole: b"isDayStart",
        }

    def reset_items(self, items: list[HistoryRow]) -> None:
        self.beginResetModel()
        self._items = list(items)
        self.endResetModel()
