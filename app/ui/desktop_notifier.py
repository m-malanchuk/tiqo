"""Desktop notifier via notify-send (KDE / Freedesktop) + optional preset file."""

from __future__ import annotations

import contextlib
import shutil
import subprocess
from pathlib import Path

from app.services.sound_presets import resolve_preset_path


class DesktopNotifier:
    """Uses ``notify-send`` so we stay free of Qt inside services and of Addons."""

    def __init__(self, *, app_name: str = "tiqo", desktop_entry: str = "tiqo") -> None:
        self._app_name = app_name
        self._desktop_entry = desktop_entry
        self._bin = shutil.which("notify-send")

    def notify_timer_finished(self, task_title: str, *, sound: str) -> None:
        if self._bin is None:
            return

        cmd = [
            self._bin,
            f"--app-name={self._app_name}",
            "--icon=appointment-soon",
            "-h",
            f"string:desktop-entry:{self._desktop_entry}",
            "tiqo",
            task_title,
        ]
        preset_path = resolve_preset_path(sound) if sound.startswith("preset:") else None
        if preset_path is None:
            # System theme sound (or unknown value).
            cmd.extend(["-h", "string:sound-name:complete"])

        with contextlib.suppress(OSError, subprocess.TimeoutExpired):
            subprocess.run(cmd, check=False, timeout=5)  # noqa: S603

        if preset_path is not None:
            self._play_file(preset_path)

    @staticmethod
    def _play_file(path: Path) -> None:
        for binary, args in (
            ("paplay", [str(path)]),
            ("ffplay", ["-nodisp", "-autoexit", "-loglevel", "quiet", str(path)]),
            ("mpv", ["--no-terminal", "--really-quiet", str(path)]),
        ):
            exe = shutil.which(binary)
            if exe is None:
                continue
            try:
                subprocess.Popen(  # noqa: S603
                    [exe, *args],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return
            except OSError:
                continue
