import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "../" as Root

// Same horizontal padding as FormTextField (Breeze TextArea defaults look indented).
TextArea {
    id: root
    Layout.fillWidth: true
    wrapMode: TextEdit.Wrap
    leftPadding: ui.fieldPadH
    rightPadding: ui.fieldPadH
    topPadding: ui.fieldPadV
    bottomPadding: ui.fieldPadV
    selectByMouse: true

    HoverHandler {
        enabled: root.enabled
        cursorShape: Qt.IBeamCursor
    }

    background: Rectangle {
        implicitHeight: ui.controlHeight * 2
        color: root.palette.base
        border.color: root.activeFocus ? root.palette.highlight : fieldTheme.border
        border.width: 1
        radius: ui.radius
    }

    Root.Theme { id: fieldTheme }
}
