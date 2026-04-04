"""Runtime UI metrics for QML (padding, control sizes, tree gutter)."""

from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot


class UiMetrics(QObject):
    """Single source for spacing and control sizes bound from QML as ``ui.*``."""

    changed = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._pad_sm = 8
        self._pad_md = 12
        self._pad_lg = 16
        self._radius = 8
        self._list_width = 220
        self._row_height = 40
        self._control_height = 36
        self._button_pad_h = 14
        self._button_pad_v = 8
        self._field_pad_h = 10
        self._field_pad_v = 8
        self._tree_step = 28
        self._tree_line = 2

    def _set(self, attr: str, value: int) -> None:
        if getattr(self, attr) == value:
            return
        setattr(self, attr, value)
        self.changed.emit()

    @Property(int, notify=changed)
    def padSm(self) -> int:  # noqa: N802
        return self._pad_sm

    @Slot(int)
    def setPadSm(self, value: int) -> None:  # noqa: N802
        self._set("_pad_sm", max(0, int(value)))

    @Property(int, notify=changed)
    def padMd(self) -> int:  # noqa: N802
        return self._pad_md

    @Slot(int)
    def setPadMd(self, value: int) -> None:  # noqa: N802
        self._set("_pad_md", max(0, int(value)))

    @Property(int, notify=changed)
    def padLg(self) -> int:  # noqa: N802
        return self._pad_lg

    @Slot(int)
    def setPadLg(self, value: int) -> None:  # noqa: N802
        self._set("_pad_lg", max(0, int(value)))

    @Property(int, notify=changed)
    def radius(self) -> int:
        return self._radius

    @Slot(int)
    def setRadius(self, value: int) -> None:  # noqa: N802
        self._set("_radius", max(0, int(value)))

    @Property(int, notify=changed)
    def listWidth(self) -> int:  # noqa: N802
        return self._list_width

    @Slot(int)
    def setListWidth(self, value: int) -> None:  # noqa: N802
        self._set("_list_width", max(120, int(value)))

    @Property(int, notify=changed)
    def rowHeight(self) -> int:  # noqa: N802
        return self._row_height

    @Slot(int)
    def setRowHeight(self, value: int) -> None:  # noqa: N802
        self._set("_row_height", max(24, int(value)))

    @Property(int, notify=changed)
    def controlHeight(self) -> int:  # noqa: N802
        return self._control_height

    @Slot(int)
    def setControlHeight(self, value: int) -> None:  # noqa: N802
        self._set("_control_height", max(24, int(value)))

    @Property(int, notify=changed)
    def buttonPadH(self) -> int:  # noqa: N802
        return self._button_pad_h

    @Slot(int)
    def setButtonPadH(self, value: int) -> None:  # noqa: N802
        self._set("_button_pad_h", max(0, int(value)))

    @Property(int, notify=changed)
    def buttonPadV(self) -> int:  # noqa: N802
        return self._button_pad_v

    @Slot(int)
    def setButtonPadV(self, value: int) -> None:  # noqa: N802
        self._set("_button_pad_v", max(0, int(value)))

    @Property(int, notify=changed)
    def fieldPadH(self) -> int:  # noqa: N802
        return self._field_pad_h

    @Slot(int)
    def setFieldPadH(self, value: int) -> None:  # noqa: N802
        self._set("_field_pad_h", max(0, int(value)))

    @Property(int, notify=changed)
    def fieldPadV(self) -> int:  # noqa: N802
        return self._field_pad_v

    @Slot(int)
    def setFieldPadV(self, value: int) -> None:  # noqa: N802
        self._set("_field_pad_v", max(0, int(value)))

    @Property(int, notify=changed)
    def treeStep(self) -> int:  # noqa: N802
        return self._tree_step

    @Slot(int)
    def setTreeStep(self, value: int) -> None:  # noqa: N802
        self._set("_tree_step", max(12, int(value)))

    @Property(int, notify=changed)
    def treeLine(self) -> int:  # noqa: N802
        return self._tree_line

    @Slot(int)
    def setTreeLine(self, value: int) -> None:  # noqa: N802
        self._set("_tree_line", max(1, int(value)))
