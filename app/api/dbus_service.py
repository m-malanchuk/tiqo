"""Session D-Bus service for Plasma widgets and external clients.

Service: ``org.tiqo.App``
Path: ``/org/tiqo/App``
Interface: ``org.tiqo.App1``

Uses QtDBus (ships with PySide6 Essentials on Linux). Registration is best-effort:
if the session bus is unavailable, the app still runs without IPC.

Contract details: ``docs/DBUS.md`` and ``app/api/org.tiqo.App1.xml``.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable

from PySide6.QtCore import ClassInfo, QObject, Signal, Slot
from PySide6.QtDBus import QDBusConnection

from app.api.session_facade import (
    HierarchyConflictError,
    NoActiveSessionError,
    SessionFacade,
)

log = logging.getLogger(__name__)

SERVICE_NAME = "org.tiqo.App"
OBJECT_PATH = "/org/tiqo/App"
INTERFACE = "org.tiqo.App1"
# Bump when breaking the IPC shape (methods, signal meaning, JSON fields).
# 5: checklist task snapshots, correction toggle, and repeated completion.
API_VERSION = "5"


@ClassInfo({"D-Bus Interface": INTERFACE})
class TiqoDBusAdaptor(QObject):
    """Qt D-Bus adaptor methods (introspectable via Qt meta-object)."""

    WorkChanged = Signal()

    def __init__(
        self,
        facade: SessionFacade,
        *,
        on_show_window: Callable[[], None] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._facade = facade
        self._on_show = on_show_window

    @Slot(result=str)
    def Ping(self) -> str:  # noqa: N802
        """Liveness check. Returns ``pong`` when the service is up."""
        return "pong"

    @Slot(result=str)
    def Version(self) -> str:  # noqa: N802
        """IPC contract version (``API_VERSION``)."""
        return API_VERSION

    @Slot(result=str)
    def ListWork(self) -> str:  # noqa: N802
        """Return JSON array of work snapshots (clocks are live — poll ~1s)."""
        return json.dumps(self._facade.list_work_dicts(), ensure_ascii=False)

    @Slot(result=str)
    def ListLists(self) -> str:  # noqa: N802
        """Return JSON array of lists ``{list_id, name, icon, is_system}``."""
        return json.dumps(self._facade.list_lists_dicts(), ensure_ascii=False)

    @Slot(int, result=str)
    def ListTasks(self, list_id: int) -> str:  # noqa: N802
        """Return JSON array of tasks for ``list_id`` (same virtual lists as the app)."""
        return json.dumps(self._facade.list_tasks_dicts(int(list_id)), ensure_ascii=False)

    @Slot(int, result=str)
    def TodayStats(self, list_id: int) -> str:  # noqa: N802
        """Return JSON ``{done, total}`` for **leaf** tasks in ``list_id`` (done = worked today)."""
        return json.dumps(self._facade.list_progress_dict(int(list_id)), ensure_ascii=False)

    @Slot(int, result=str)
    def Resume(self, task_id: int) -> str:  # noqa: N802
        try:
            self._facade.resume(int(task_id))
            return "ok"
        except (HierarchyConflictError, NoActiveSessionError) as exc:
            return f"error:{exc}"
        except Exception as exc:
            log.exception("Unexpected failure while resuming task %s", task_id)
            return f"error:{exc}"

    @Slot(int, result=str)
    def Pause(self, task_id: int) -> str:  # noqa: N802
        try:
            self._facade.pause(int(task_id))
            return "ok"
        except NoActiveSessionError as exc:
            return f"error:{exc}"
        except Exception as exc:
            log.exception("Unexpected failure while pausing task %s", task_id)
            return f"error:{exc}"

    @Slot(int, result=str)
    def Stop(self, task_id: int) -> str:  # noqa: N802
        try:
            self._facade.stop(int(task_id))
            return "ok"
        except Exception as exc:
            log.exception("Unexpected failure while stopping task %s", task_id)
            return f"error:{exc}"

    @Slot(int, result=str)
    def ToggleChecklist(self, task_id: int) -> str:  # noqa: N802
        """Toggle a binary task's done/not-done state."""
        try:
            self._facade.toggle_checklist(int(task_id))
            return "ok"
        except Exception as exc:
            log.exception("Unexpected failure while toggling checklist %s", task_id)
            return f"error:{exc}"

    @Slot(int, result=str)
    def CompleteChecklist(self, task_id: int) -> str:  # noqa: N802
        """Record one checklist execution (repeated executions are allowed)."""
        try:
            self._facade.complete_checklist(int(task_id))
            return "ok"
        except Exception as exc:
            log.exception("Unexpected failure while completing checklist %s", task_id)
            return f"error:{exc}"

    @Slot()
    def ShowWindow(self) -> None:  # noqa: N802
        if self._on_show is not None:
            self._on_show()

    def notify_work_changed(self) -> None:
        self.WorkChanged.emit()


def register_tiqo_dbus(
    facade: SessionFacade,
    *,
    on_show_window: Callable[[], None] | None = None,
    parent: QObject | None = None,
) -> TiqoDBusAdaptor | None:
    """Register ``org.tiqo.App`` on the session bus. Returns None on failure."""
    bus = QDBusConnection.sessionBus()
    if not bus.isConnected():
        log.warning("D-Bus session bus unavailable; Plasma IPC disabled")
        return None

    adaptor = TiqoDBusAdaptor(facade, on_show_window=on_show_window, parent=parent)
    options = (
        QDBusConnection.RegisterOption.ExportAllSlots
        | QDBusConnection.RegisterOption.ExportAllSignals
    )
    if not bus.registerObject(OBJECT_PATH, adaptor, options):
        log.warning("Failed to register D-Bus object %s", OBJECT_PATH)
        return None
    if not bus.registerService(SERVICE_NAME):
        log.warning("Failed to register D-Bus service %s (already taken?)", SERVICE_NAME)
        bus.unregisterObject(OBJECT_PATH)
        return None
    log.info("D-Bus service %s at %s ready (interface %s)", SERVICE_NAME, OBJECT_PATH, INTERFACE)
    return adaptor
