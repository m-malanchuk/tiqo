"""tiqo application entrypoint — main window, tray, settings bridge."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, QUrl, Slot
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication, QFileDialog

from app.api.dbus_service import register_tiqo_dbus
from app.api.session_facade import SessionFacade
from app.domain.models import HEARTBEAT_INTERVAL_SECONDS
from app.storage.db import open_database, open_memory_database
from app.storage.settings_repo import SettingsRepo
from app.ui.app_icons import app_icon, ensure_desktop_app_icon
from app.ui.desktop_notifier import DesktopNotifier
from app.ui.single_instance import SingleInstance
from app.ui.tray_controller import TrayController
from app.ui.viewmodels.app_view_model import AppViewModel
from app.ui.viewmodels.settings_bridge import SettingsBridge
from app.ui.viewmodels.ui_metrics import UiMetrics


def _open_connection():
    override = os.environ.get("TIQO_DB")
    if override == ":memory:":
        return open_memory_database()
    if override:
        return open_database(override)
    return open_database()


class WindowBridge(QObject):
    """Small bridge so QML can hide/show without quitting."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._window: QObject | None = None

    def bind(self, window: QObject) -> None:
        self._window = window

    @Slot()
    def showWindow(self) -> None:  # noqa: N802
        if self._window is None:
            return
        self._window.setProperty("visible", True)
        # raise/activate if available
        for name in ("raise", "requestActivate"):
            method = getattr(self._window, name, None)
            if callable(method):
                method()

    @Slot()
    def hideWindow(self) -> None:  # noqa: N802
        if self._window is None:
            return
        self._window.setProperty("visible", False)

    @Slot(str, str, result=str)
    def chooseSaveFile(self, title: str, default_name: str) -> str:  # noqa: N802
        """Ask the user where to save a file and return an empty path on cancel."""
        initial = Path.home() / Path(default_name).name
        path, _ = QFileDialog.getSaveFileName(
            None,
            title,
            str(initial),
            "CSV files (*.csv);;All files (*)",
        )
        return path

    @Slot(str)
    def copyText(self, value: str) -> None:  # noqa: N802
        """Copy text through the desktop clipboard from QML."""
        QApplication.clipboard().setText(value)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("tiqo")
    app.setOrganizationName("tiqo")
    app.setDesktopFileName("tiqo")
    # KWin title bar resolves Icon=tiqo from the icon theme — install SVG there.
    ensure_desktop_app_icon()
    window_icon = app_icon()
    app.setWindowIcon(window_icon)
    app.setQuitOnLastWindowClosed(False)

    instance = SingleInstance(app)
    if not instance.ensure_primary():
        return 0

    conn = _open_connection()
    view_model = AppViewModel(conn, notifier=DesktopNotifier())
    ui_metrics = UiMetrics()
    bridge = WindowBridge(app)

    settings_holder: dict[str, SettingsBridge | TrayController | None] = {
        "settings": None,
        "tray": None,
    }

    def refresh_tray_icon() -> None:
        tray = settings_holder["tray"]
        if isinstance(tray, TrayController):
            tray._refresh_icon()

    def retranslate() -> None:
        tray = settings_holder["tray"]
        if isinstance(tray, TrayController):
            tray._rebuild_menu()
        # Refresh list titles + force QML dialog labels (createListHint, etc.).
        view_model.refresh_lists()
        view_model.refresh_tasks()
        view_model.retranslateUi()

    settings = SettingsBridge(
        SettingsRepo(conn),
        on_tray_icon=refresh_tray_icon,
        on_retranslate=retranslate,
        parent=app,
    )
    settings_holder["settings"] = settings

    engine = QQmlApplicationEngine()
    qml_root = Path(__file__).resolve().parent / "qml"
    engine.addImportPath(str(qml_root))
    engine.rootContext().setContextProperty("app", view_model)
    engine.rootContext().setContextProperty("ui", ui_metrics)
    engine.rootContext().setContextProperty("windowBridge", bridge)
    engine.rootContext().setContextProperty("settings", settings)
    # Alias: all QML (main + tool windows) bind translations via i18n.language.
    engine.rootContext().setContextProperty("i18n", settings)

    qml_path = qml_root / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        print(f"Failed to load QML: {qml_path}", file=sys.stderr)
        return 1

    window = engine.rootObjects()[0]
    # QML ApplicationWindow is a QWindow — set pixmap icon explicitly too.
    set_icon = getattr(window, "setIcon", None)
    if callable(set_icon):
        set_icon(window_icon)
    bridge.bind(window)

    def quit_app() -> None:
        app.quit()

    instance.raiseRequested.connect(bridge.showWindow)

    tray = TrayController(
        app,
        view_model,
        settings,
        on_show_window=bridge.showWindow,
        on_quit=quit_app,
    )
    settings_holder["tray"] = tray

    # IPC for Plasma widget / scripts (best-effort; app runs without it).
    facade = SessionFacade(conn, engine=view_model.engine)
    dbus_api = register_tiqo_dbus(
        facade,
        on_show_window=bridge.showWindow,
        parent=app,
    )
    if dbus_api is not None:
        view_model.workChanged.connect(dbus_api.notify_work_changed)

    ui_timer = QTimer()
    ui_timer.setInterval(1000)
    ui_timer.timeout.connect(view_model.tick)
    ui_timer.timeout.connect(tray.refresh)
    ui_timer.start()

    heartbeat = QTimer()
    heartbeat.setInterval(HEARTBEAT_INTERVAL_SECONDS * 1000)
    heartbeat.timeout.connect(view_model.heartbeat)
    heartbeat.start()

    _ = (
        ui_timer,
        heartbeat,
        view_model,
        ui_metrics,
        tray,
        instance,
        bridge,
        settings,
        facade,
        dbus_api,
    )

    code = app.exec()
    conn.close()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
