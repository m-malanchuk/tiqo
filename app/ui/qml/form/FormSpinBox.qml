import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

SpinBox {
    id: root
    Layout.preferredHeight: ui.controlHeight
    implicitHeight: ui.controlHeight
    leftPadding: ui.fieldPadH
    rightPadding: ui.fieldPadH

    HoverHandler {
        enabled: root.enabled
        cursorShape: Qt.PointingHandCursor
    }
}
