#!/usr/bin/env bash
# REQUIRED after every plasmoid UI fix (see plasma/README.md).
#
# Removes EVERY org.tiqo.work instance (desktop + all panels), wipes the full
# plasmashell QML cache, reinstalls the package, adds one fresh panel copy.
# Prefer this over install-dev.sh alone — otherwise the panel keeps stale QML.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
ID="org.tiqo.work"

if command -v qdbus6 >/dev/null; then
  QDBUS=(qdbus6)
elif command -v qdbus >/dev/null; then
  QDBUS=(qdbus)
else
  echo "qdbus6 not found" >&2
  exit 1
fi

echo "== 1/5 remove all ${ID} instances from desktop + panels =="
REMOVE_SCRIPT=$(cat <<'EOF'
var id = "org.tiqo.work";
var removed = 0;

function scrubPanel(panel) {
    var widgets = panel.widgets();
    for (var i = widgets.length - 1; i >= 0; --i) {
        if (widgets[i].type === id) {
            widgets[i].remove();
            removed += 1;
        }
    }
}

if (typeof panelIds !== "undefined") {
    for (var p = 0; p < panelIds.length; ++p)
        scrubPanel(panelById(panelIds[p]));
}

// Desktop containments (formFactor 0) also hold applets.
if (typeof desktopById !== "undefined" && typeof desktops !== "undefined") {
    var desks = desktops();
    for (var d = 0; d < desks.length; ++d) {
        var desk = desks[d];
        var widgets = desk.widgets();
        for (var i = widgets.length - 1; i >= 0; --i) {
            if (widgets[i].type === id) {
                widgets[i].remove();
                removed += 1;
            }
        }
    }
}

print("OK: removed " + removed + " instance(s) of " + id);
EOF
)
"${QDBUS[@]}" org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript "${REMOVE_SCRIPT}"

echo "== 2/5 wipe plasmashell QML cache =="
CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/plasmashell"
if [[ -d "${CACHE}/qmlcache" ]]; then
  rm -rf "${CACHE}/qmlcache"
  mkdir -p "${CACHE}/qmlcache"
  echo "cleared ${CACHE}/qmlcache"
fi
# Also drop plasmawindowed cache so previews stay honest
rm -rf "${XDG_CACHE_HOME:-$HOME/.cache}/plasmawindowed/qmlcache" 2>/dev/null || true

echo "== 3/5 reinstall package =="
bash "${ROOT}/install-dev.sh"

echo "== 4/5 add one fresh instance to the first panel =="
bash "${ROOT}/add-to-panel.sh"

echo "== 5/5 restart plasmashell =="
# Always restart the shell so it cannot retain an older QML engine or D-Bus
# call path after a widget reset.
kquitapp6 plasmashell || true
kstart plasmashell

echo
echo "Plasmashell restarted. Check the panel popup after it returns."
