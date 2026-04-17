import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

TextField {
    id: root
    Layout.fillWidth: true
    Layout.preferredHeight: ui.controlHeight
    implicitHeight: ui.controlHeight
    leftPadding: ui.fieldPadH
    rightPadding: ui.fieldPadH
    topPadding: ui.fieldPadV
    bottomPadding: ui.fieldPadV
    selectByMouse: true

    HoverHandler {
        enabled: root.enabled
        cursorShape: Qt.IBeamCursor
    }
}
