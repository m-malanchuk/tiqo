#!/usr/bin/env bash
# Install / upgrade the tiqo work plasmoid into the user Plasma prefix.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PKG="${ROOT}/org.tiqo.work"
ID="org.tiqo.work"

if [[ ! -f "${PKG}/metadata.json" ]]; then
  echo "missing ${PKG}/metadata.json" >&2
  exit 1
fi

# Prefer remove+install: --upgrade has left the package missing for us before.
if kpackagetool6 --type Plasma/Applet --show "${ID}" &>/dev/null; then
  kpackagetool6 --type Plasma/Applet --remove "${ID}" || true
fi
kpackagetool6 --type Plasma/Applet --install "${PKG}"
echo "Installed ${ID} → ~/.local/share/plasma/plasmoids/${ID}/"

CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/plasmashell/qmlcache"
if [[ -d "${CACHE}" ]]; then
  find "${CACHE}" -iname '*tiqo*' -delete 2>/dev/null || true
fi

kbuildsycoca6 >/dev/null 2>&1 || true

echo
echo "Verify package:"
kpackagetool6 --type Plasma/Applet --list | grep -F "${ID}" || {
  echo "ERROR: ${ID} not in kpackagetool list" >&2
  exit 1
}

echo
echo "After a UI fix prefer the full reset (instances + qmlcache + one panel copy):"
echo "  bash plasma/reset-widget.sh"
echo
echo "Preview only:  plasmawindowed ${ID}"
echo "Add one copy:  bash plasma/add-to-panel.sh"
echo "tiqo must be running for the roster (D-Bus org.tiqo.App)."
