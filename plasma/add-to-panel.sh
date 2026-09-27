#!/usr/bin/env bash
# Add org.tiqo.work to the first panel via plasmashell scripting.
# Works even when the widget is missing from the "Add widgets" browser
# (Plasma often does not rescan packages until plasmashell restarts).
set -euo pipefail

ID="org.tiqo.work"

if ! kpackagetool6 --type Plasma/Applet --show "${ID}" &>/dev/null; then
  echo "Package ${ID} is not installed. Run: bash plasma/install-dev.sh" >&2
  exit 1
fi

# Prefer qdbus6, fall back to qdbus.
if command -v qdbus6 >/dev/null; then
  QDBUS=(qdbus6)
elif command -v qdbus >/dev/null; then
  QDBUS=(qdbus)
else
  echo "qdbus6 not found" >&2
  exit 1
fi

SCRIPT=$(cat <<'EOF'
var id = "org.tiqo.work";
if (typeof panelIds === "undefined" || panelIds.length === 0) {
    print("ERROR: no panels");
} else {
    var panel = panelById(panelIds[0]);
    panel.addWidget(id);
    print("OK: added " + id + " to panel " + panelIds[0]);
}
EOF
)

echo "Adding ${ID} to the first panel…"
"${QDBUS[@]}" org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript "${SCRIPT}"
echo "Done. Look at the panel (usually near the system tray / clock)."
