import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "../" as Root

CheckBox {
    id: root
    Layout.fillWidth: true
    implicitHeight: ui.controlHeight
    spacing: ui.padSm

    Root.Theme { id: theme }

    indicator: Rectangle {
        implicitWidth: 18
        implicitHeight: 18
        x: root.leftPadding
        y: parent ? parent.height / 2 - height / 2 : 0
        radius: 3
        color: root.checked ? theme.accent : "transparent"
        border.width: 2
        border.color: root.checked || root.hovered ? theme.accent : theme.border
        opacity: root.enabled ? 1.0 : 0.45

        Text {
            anchors.centerIn: parent
            text: "✓"
            color: theme.accentText
            font.bold: true
            visible: root.checked
        }
    }

    // The KDE style's default label treats a custom indicator's width as the
    // complete label offset. Add the visual gap explicitly so the caption
    // never touches the checkmark.
    contentItem: Text {
        text: root.text
        font: root.font
        color: theme.text
        leftPadding: root.indicator ? root.indicator.width + root.spacing : 0
        rightPadding: root.mirrored && root.indicator ? root.indicator.width + root.spacing : 0
        wrapMode: Text.WordWrap
        verticalAlignment: Text.AlignVCenter
    }

    HoverHandler {
        enabled: root.enabled
        cursorShape: Qt.PointingHandCursor
    }
}
