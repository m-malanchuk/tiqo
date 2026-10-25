import QtQuick
import QtQuick.Controls

import "../" as Root

// Custom indicator — Breeze Dark system radio rings are nearly invisible.
RadioButton {
    id: root
    implicitHeight: ui.controlHeight
    spacing: ui.padSm

    Root.Theme { id: theme }

    indicator: Rectangle {
        implicitWidth: 18
        implicitHeight: 18
        x: root.leftPadding
        y: parent ? parent.height / 2 - height / 2 : 0
        radius: width / 2
        color: "transparent"
        border.width: 2
        border.color: root.checked || root.hovered ? theme.accent : theme.border
        opacity: root.enabled ? 1.0 : 0.45

        Rectangle {
            anchors.centerIn: parent
            width: 8
            height: 8
            radius: 4
            color: theme.accent
            visible: root.checked
        }
    }

    // The KDE style's default label does not always reserve the gap when a
    // custom indicator is supplied. Add the offset explicitly so the caption
    // stays readable next to the radio ring.
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
