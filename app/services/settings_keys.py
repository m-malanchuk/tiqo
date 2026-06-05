"""Well-known settings keys."""

from __future__ import annotations

# system = Freedesktop/KDE notification sound; preset:<stem> = file under sounds/
TIMER_SOUND = "timer_sound"
TIMER_SOUND_SYSTEM = "system"

# close_to_tray | quit
CLOSE_BEHAVIOR = "close_behavior"
CLOSE_TO_TRAY = "close_to_tray"
CLOSE_QUIT = "quit"

# 1 = copy the user-level desktop entry, 0 = remove it
AUTOSTART = "autostart"
AUTOSTART_ENABLED = "1"
AUTOSTART_DISABLED = "0"

# auto | tray-dark | tray-light | color (app mark)
TRAY_ICON = "tray_icon"
TRAY_ICON_AUTO = "auto"
TRAY_ICON_DARK = "tray-dark"
TRAY_ICON_LIGHT = "tray-light"
TRAY_ICON_COLOR = "color"

# small | medium | large
FONT_SIZE = "font_size"
FONT_SMALL = "small"
FONT_MEDIUM = "medium"
FONT_LARGE = "large"

# BCP-47-ish short codes we ship
UI_LANGUAGE = "ui_language"
LANG_DEFAULT = "ru"
