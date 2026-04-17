import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// ListView/Flickable often steals the first press. preventStealing keeps clicks reliable.
Button {
    id: root
    Layout.preferredHeight: ui.controlHeight
    implicitHeight: ui.controlHeight
    leftPadding: ui.buttonPadH
    rightPadding: ui.buttonPadH
    topPadding: ui.buttonPadV
    bottomPadding: ui.buttonPadV

    MouseArea {
        anchors.fill: parent
        enabled: root.enabled
        preventStealing: true
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onPressed: root.down = true
        onReleased: root.down = false
        onCanceled: root.down = false
        onClicked: root.clicked()
    }
}
