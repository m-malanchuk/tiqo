"""QAbstractListModel of tasks for QML (flat rows with depth for nesting)."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt

from app.application.models import TaskRow


def _structure_key(row: TaskRow) -> tuple:
    """Identity that requires a full model reset (scroll would jump anyway)."""
    return (
        row.id,
        row.depth,
        row.is_nested,
        row.is_last_sibling,
        row.ancestor_continues,
        row.has_children,
        row.is_expanded,
        row.title,
        row.description,
        row.mode,
        row.kind,
        row.is_completed,
        row.can_complete,
        row.is_scheduled_today,
    )


class TaskModel(QAbstractListModel):
    IdRole = Qt.ItemDataRole.UserRole + 1
    TitleRole = Qt.ItemDataRole.UserRole + 2
    DescriptionRole = Qt.ItemDataRole.UserRole + 3
    ModeRole = Qt.ItemDataRole.UserRole + 4
    TimeTodayRole = Qt.ItemDataRole.UserRole + 5
    WorkStateRole = Qt.ItemDataRole.UserRole + 6
    CanStartRole = Qt.ItemDataRole.UserRole + 7
    CanPauseRole = Qt.ItemDataRole.UserRole + 8
    CanStopRole = Qt.ItemDataRole.UserRole + 9
    DepthRole = Qt.ItemDataRole.UserRole + 10
    IsNestedRole = Qt.ItemDataRole.UserRole + 11
    IsLastSiblingRole = Qt.ItemDataRole.UserRole + 12
    AncestorContinuesRole = Qt.ItemDataRole.UserRole + 13
    HasChildrenRole = Qt.ItemDataRole.UserRole + 14
    IsExpandedRole = Qt.ItemDataRole.UserRole + 15
    KindRole = Qt.ItemDataRole.UserRole + 16
    IsCompletedRole = Qt.ItemDataRole.UserRole + 17
    CanCompleteRole = Qt.ItemDataRole.UserRole + 18
    IsScheduledTodayRole = Qt.ItemDataRole.UserRole + 19

    _LIVE_ROLES = (
        TimeTodayRole,
        WorkStateRole,
        CanStartRole,
        CanPauseRole,
        CanStopRole,
        IsCompletedRole,
        CanCompleteRole,
    )

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._items: list[TaskRow] = []

    def rowCount(self, parent: QModelIndex | None = None) -> int:  # noqa: N802
        if parent is not None and parent.isValid():
            return 0
        return len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return None
        item = self._items[index.row()]
        mapping = {
            self.IdRole: item.id,
            Qt.ItemDataRole.UserRole: item.id,
            self.TitleRole: item.title,
            Qt.ItemDataRole.DisplayRole: item.title,
            self.DescriptionRole: item.description,
            self.ModeRole: item.mode,
            self.TimeTodayRole: item.time_today,
            self.WorkStateRole: item.work_state,
            self.CanStartRole: item.can_start,
            self.CanPauseRole: item.can_pause,
            self.CanStopRole: item.can_stop,
            self.DepthRole: item.depth,
            self.IsNestedRole: item.is_nested,
            self.IsLastSiblingRole: item.is_last_sibling,
            self.AncestorContinuesRole: list(item.ancestor_continues),
            self.HasChildrenRole: item.has_children,
            self.IsExpandedRole: item.is_expanded,
            self.KindRole: item.kind,
            self.IsCompletedRole: item.is_completed,
            self.CanCompleteRole: item.can_complete,
            self.IsScheduledTodayRole: item.is_scheduled_today,
        }
        return mapping.get(role)

    def roleNames(self) -> dict[int, bytes]:  # noqa: N802
        return {
            self.IdRole: b"taskId",
            self.TitleRole: b"title",
            self.DescriptionRole: b"description",
            self.ModeRole: b"mode",
            self.TimeTodayRole: b"timeToday",
            self.WorkStateRole: b"workState",
            self.CanStartRole: b"canStart",
            self.CanPauseRole: b"canPause",
            self.CanStopRole: b"canStop",
            self.DepthRole: b"depth",
            self.IsNestedRole: b"isNested",
            self.IsLastSiblingRole: b"isLastSibling",
            self.AncestorContinuesRole: b"ancestorContinues",
            self.HasChildrenRole: b"hasChildren",
            self.IsExpandedRole: b"isExpanded",
            self.KindRole: b"kind",
            self.IsCompletedRole: b"isCompleted",
            self.CanCompleteRole: b"canComplete",
            self.IsScheduledTodayRole: b"isScheduledToday",
        }

    def reset_items(self, items: list[TaskRow]) -> None:
        """Replace rows; preserves scroll when only live fields (clock/buttons) change."""
        new_items = list(items)
        if len(self._items) == len(new_items) and all(
            _structure_key(old) == _structure_key(new)
            for old, new in zip(self._items, new_items, strict=True)
        ):
            if self._items == new_items:
                return
            self._items = new_items
            if self._items:
                top = self.index(0, 0)
                bottom = self.index(len(self._items) - 1, 0)
                self.dataChanged.emit(top, bottom, list(self._LIVE_ROLES))
            return
        self.beginResetModel()
        self._items = new_items
        self.endResetModel()
