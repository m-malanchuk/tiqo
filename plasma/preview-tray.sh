#!/usr/bin/env bash
# Show org.tiqo.work in the real KDE Notification Area (system tray)
# without touching plasmashell / panels / your session.
#
# Uses plasmawindowed --statusnotifier: the plasmoid stays in the tray
# even if you close the preview window. Quit this process (Ctrl+C or
# close the remaining window) to remove that tray entry.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
ID="org.tiqo.work"

if ! kpackagetool6 --type Plasma/Applet --show "${ID}" &>/dev/null; then
  bash "${ROOT}/install-dev.sh"
fi

echo "Starting tray preview for ${ID}"
echo "  • Icon appears in the system tray / notification area"
echo "  • LMB opens the same popup as the panel widget"
echo "  • No plasmashell restart; your session stays put"
echo "  • Stop: Ctrl+C in this terminal (or quit plasmawindowed)"
echo
exec plasmawindowed --statusnotifier "${ID}"
