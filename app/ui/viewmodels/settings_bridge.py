"""Settings window state — persisted via SettingsRepo."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import QApplication

from app.i18n import available_locales, set_locale, tr
from app.services import autostart
from app.services import settings_keys as keys
from app.services.sound_presets import list_sound_presets, preset_setting_value
from app.storage.paths import user_sounds_dir
from app.storage.settings_repo import SettingsRepo
from app.ui.app_icons import tray_icon
from app.ui.viewmodels.option_model import OptionModel, OptionRow


class SettingsBridge(QObject):
    changed = Signal()
    openChanged = Signal()
    languageChanged = Signal()

    def __init__(
        self,
        settings: SettingsRepo,
        *,
        on_tray_icon: Callable[[], None] | None = None,
        on_retranslate: Callable[[], None] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings = settings
        self._on_tray_icon = on_tray_icon
        self._on_retranslate = on_retranslate
        self._open = False
        self._sound_model = OptionModel(self)
        self._language_model = OptionModel(self)
        self._tray_model = OptionModel(self)
        self._font_model = OptionModel(self)
        self._close_model = OptionModel(self)
        self._ensure_defaults()
        self._apply_locale(persist=False)
        self._apply_font()
        self._sync_autostart()
        self._reload_models()

    def _ensure_defaults(self) -> None:
        defaults = {
            keys.TIMER_SOUND: keys.TIMER_SOUND_SYSTEM,
            keys.CLOSE_BEHAVIOR: keys.CLOSE_TO_TRAY,
            keys.TRAY_ICON: keys.TRAY_ICON_AUTO,
            keys.FONT_SIZE: keys.FONT_MEDIUM,
            keys.UI_LANGUAGE: keys.LANG_DEFAULT,
        }
        for key, value in defaults.items():
            if self._settings.get(key) is None:
                self._settings.set(key, value)
        if self._settings.get(keys.AUTOSTART) is None:
            # Preserve an existing user entry when upgrading from a package
            # that enabled autostart outside the application settings.
            enabled = autostart.is_enabled()
            self._settings.set(
                keys.AUTOSTART,
                keys.AUTOSTART_ENABLED if enabled else keys.AUTOSTART_DISABLED,
            )
        # Ensure user sounds dir exists so people know where to drop files.
        user_sounds_dir().mkdir(parents=True, exist_ok=True)

    def _sync_autostart(self) -> None:
        desired = self._settings.get(keys.AUTOSTART) == keys.AUTOSTART_ENABLED
        try:
            actual = autostart.set_enabled(desired)
        except OSError:
            # A read-only or unavailable config directory should not prevent
            # the settings window from opening. The next toggle retries it.
            return
        if actual != desired:
            self._settings.set(
                keys.AUTOSTART,
                keys.AUTOSTART_ENABLED if actual else keys.AUTOSTART_DISABLED,
            )

    def _reload_models(self) -> None:
        self._sound_model.reset_items(
            [
                OptionRow(keys.TIMER_SOUND_SYSTEM, tr("settings.sound_system")),
                *[OptionRow(preset_setting_value(p.id), p.label) for p in list_sound_presets()],
            ]
        )
        self._language_model.reset_items(
            [
                OptionRow(loc.code, f"{loc.flag_emoji}  {loc.native_name}")
                for loc in available_locales()
            ]
        )
        self._tray_model.reset_items(
            [
                OptionRow(keys.TRAY_ICON_AUTO, tr("settings.tray_icon_auto")),
                OptionRow(keys.TRAY_ICON_DARK, tr("settings.tray_icon_dark")),
                OptionRow(keys.TRAY_ICON_LIGHT, tr("settings.tray_icon_light")),
                OptionRow(keys.TRAY_ICON_COLOR, tr("settings.tray_icon_color")),
            ]
        )
        self._font_model.reset_items(
            [
                OptionRow(keys.FONT_SMALL, tr("settings.font_small")),
                OptionRow(keys.FONT_MEDIUM, tr("settings.font_medium")),
                OptionRow(keys.FONT_LARGE, tr("settings.font_large")),
            ]
        )
        self._close_model.reset_items(
            [
                OptionRow(keys.CLOSE_TO_TRAY, tr("settings.close_to_tray")),
                OptionRow(keys.CLOSE_QUIT, tr("settings.close_quit")),
            ]
        )
        self.changed.emit()

    def _apply_locale(self, *, persist: bool) -> None:
        code = self._settings.get(keys.UI_LANGUAGE) or keys.LANG_DEFAULT
        set_locale(code)
        if persist:
            self._settings.set(keys.UI_LANGUAGE, code)
        self.languageChanged.emit()
        if self._on_retranslate:
            self._on_retranslate()

    def _apply_font(self) -> None:
        size = self._settings.get(keys.FONT_SIZE) or keys.FONT_MEDIUM
        app = QApplication.instance()
        if not isinstance(app, QApplication):
            return
        base = QGuiApplication.font()
        # Keep family; adjust point size relative to system default once.
        default_pt = max(9, base.pointSize() or 10)
        # Store original once on the QApplication instance.
        if not hasattr(app, "_tiqo_base_point_size"):
            app._tiqo_base_point_size = default_pt  # type: ignore[attr-defined]
        base_pt = int(app._tiqo_base_point_size)  # type: ignore[attr-defined]
        delta = {
            keys.FONT_SMALL: -2,
            keys.FONT_MEDIUM: 0,
            keys.FONT_LARGE: 3,
        }.get(size, 0)
        font = QFont(base)
        font.setPointSize(max(8, base_pt + delta))
        app.setFont(font)

    def tray_icon_variant(self) -> str:
        return self._settings.get(keys.TRAY_ICON) or keys.TRAY_ICON_AUTO

    def current_tray_icon(self):
        return tray_icon(variant=self.tray_icon_variant())

    # --- dialog open ---
    @Property(bool, notify=openChanged)
    def open(self) -> bool:
        return self._open

    @Slot()
    def openSettings(self) -> None:  # noqa: N802
        self._reload_models()
        self._open = True
        self.openChanged.emit()

    @Slot()
    def closeSettings(self) -> None:  # noqa: N802
        self._open = False
        self.openChanged.emit()

    # --- models ---
    @Property(QObject, notify=changed)
    def soundModel(self) -> QObject:  # noqa: N802
        return self._sound_model

    @Property(QObject, notify=changed)
    def languageModel(self) -> QObject:  # noqa: N802
        return self._language_model

    @Property(QObject, notify=changed)
    def trayIconModel(self) -> QObject:  # noqa: N802
        return self._tray_model

    @Property(QObject, notify=changed)
    def fontModel(self) -> QObject:  # noqa: N802
        return self._font_model

    @Property(QObject, notify=changed)
    def closeModel(self) -> QObject:  # noqa: N802
        return self._close_model

    # --- values ---
    @Property(str, notify=changed)
    def closeBehavior(self) -> str:  # noqa: N802
        return self._settings.get(keys.CLOSE_BEHAVIOR) or keys.CLOSE_TO_TRAY

    @Slot(str)
    def setCloseBehavior(self, value: str) -> None:  # noqa: N802
        if value not in (keys.CLOSE_TO_TRAY, keys.CLOSE_QUIT):
            return
        self._settings.set(keys.CLOSE_BEHAVIOR, value)
        self.changed.emit()

    @Property(bool, notify=changed)
    def closeToTray(self) -> bool:  # noqa: N802
        return self.closeBehavior == keys.CLOSE_TO_TRAY

    @Property(bool, notify=changed)
    def autostart(self) -> bool:
        return self._settings.get(keys.AUTOSTART) == keys.AUTOSTART_ENABLED

    @Slot(bool)
    def setAutostart(self, enabled: bool) -> None:  # noqa: N802
        try:
            actual = autostart.set_enabled(bool(enabled))
        except OSError:
            return
        self._settings.set(
            keys.AUTOSTART,
            keys.AUTOSTART_ENABLED if actual else keys.AUTOSTART_DISABLED,
        )
        self.changed.emit()

    @Property(str, notify=changed)
    def timerSound(self) -> str:  # noqa: N802
        return self._settings.get(keys.TIMER_SOUND) or keys.TIMER_SOUND_SYSTEM

    @Slot(str)
    def setTimerSound(self, value: str) -> None:  # noqa: N802
        self._settings.set(keys.TIMER_SOUND, value)
        self.changed.emit()

    @Property(str, notify=changed)
    def trayIcon(self) -> str:  # noqa: N802
        return self.tray_icon_variant()

    @Slot(str)
    def setTrayIcon(self, value: str) -> None:  # noqa: N802
        if value not in (
            keys.TRAY_ICON_AUTO,
            keys.TRAY_ICON_DARK,
            keys.TRAY_ICON_LIGHT,
            keys.TRAY_ICON_COLOR,
        ):
            return
        self._settings.set(keys.TRAY_ICON, value)
        self.changed.emit()
        if self._on_tray_icon:
            self._on_tray_icon()

    @Property(str, notify=changed)
    def fontSize(self) -> str:  # noqa: N802
        return self._settings.get(keys.FONT_SIZE) or keys.FONT_MEDIUM

    @Slot(str)
    def setFontSize(self, value: str) -> None:  # noqa: N802
        if value not in (keys.FONT_SMALL, keys.FONT_MEDIUM, keys.FONT_LARGE):
            return
        self._settings.set(keys.FONT_SIZE, value)
        self._apply_font()
        self.changed.emit()

    @Property(str, notify=languageChanged)
    def language(self) -> str:
        return self._settings.get(keys.UI_LANGUAGE) or keys.LANG_DEFAULT

    @Slot(str)
    def setLanguage(self, value: str) -> None:  # noqa: N802
        codes = {loc.code for loc in available_locales()}
        if value not in codes:
            return
        self._settings.set(keys.UI_LANGUAGE, value)
        self._apply_locale(persist=False)
        self._reload_models()

    @Property(str, notify=changed)
    def soundsPathHint(self) -> str:  # noqa: N802
        return str(user_sounds_dir())

    @Slot(str, result=str)
    def t(self, msgid: str) -> str:
        """Translate for QML bindings that should follow ``language`` / ``languageChanged``."""
        return tr(msgid)

    @Slot(str, str, result=str)
    def t1(self, msgid: str, v1: str) -> str:
        return tr(msgid, v1=v1)

    @Slot(str, str, str, result=str)
    def t2(self, msgid: str, v1: str, v2: str) -> str:
        return tr(msgid, v1=v1, v2=v2)
