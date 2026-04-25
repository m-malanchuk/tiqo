"""System tray for tiqo (KDE StatusNotifier via QSystemTrayIcon).

Minimal tray: keep the process alive when the window is closed.
- Left-click / double-click → show main window
- Right-click → Show / Settings / Quit

Tray glyph follows settings (auto / dark / light / color).
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtGui import QAction, QGuiApplication
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from app.i18n import tr
from app.ui.viewmodels.app_view_model import AppViewModel
from app.ui.viewmodels.settings_bridge import SettingsBridge


class TrayController:
    def __init__(
        self,
        app: QApplication,
        view_model: AppViewModel,
        settings: SettingsBridge,
        *,
        on_show_window: Callable[[], None],
        on_quit: Callable[[], None],
    ) -> None:
        self._vm = view_model
        self._settings = settings
        self._on_show = on_show_window
        self._on_quit = on_quit

        self._tray = QSystemTrayIcon(app)
        self._tray.setIcon(settings.current_tray_icon())
        self._tray.setToolTip("tiqo")
        self._tray.activated.connect(self._on_activated)

        hints = QGuiApplication.styleHints()
        hints.colorSchemeChanged.connect(self._on_color_scheme_changed)
        settings.changed.connect(self._refresh_icon)
        settings.languageChanged.connect(self._rebuild_menu)

        self._menu = QMenu()
        self._show_action = QAction(self._menu)
        self._show_action.triggered.connect(self._on_show)
        self._menu.addAction(self._show_action)
        self._settings_action = QAction(self._menu)
        self._settings_action.triggered.connect(self._settings.openSettings)
        self._menu.addAction(self._settings_action)
        self._quit_action = QAction(self._menu)
        self._quit_action.triggered.connect(self._on_quit)
        self._menu.addAction(self._quit_action)
        self._tray.setContextMenu(self._menu)
        self._rebuild_menu()

        self._vm.workChanged.connect(self.refresh)
        self.refresh()
        self._tray.show()

    def refresh(self) -> None:
        roster = self._vm.work_roster()
        if not roster:
            self._tray.setToolTip("tiqo")
            return
        tip_parts = [f"{r.title} · {r.clock}" for r in roster[:3]]
        tip = "tiqo — " + " | ".join(tip_parts)
        extra = len(roster) - 3
        if extra > 0:
            tip += f" (+{extra})"
        self._tray.setToolTip(tip)

    def _refresh_icon(self) -> None:
        self._tray.setIcon(self._settings.current_tray_icon())

    def _rebuild_menu(self) -> None:
        self._show_action.setText(tr("tray.show_window"))
        self._settings_action.setText(tr("tray.settings"))
        self._quit_action.setText(tr("tray.quit"))

    def _on_color_scheme_changed(self, *_args: object) -> None:
        if self._settings.tray_icon_variant() == "auto":
            self._refresh_icon()

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._on_show()
