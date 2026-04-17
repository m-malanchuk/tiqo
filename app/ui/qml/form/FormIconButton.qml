import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Square control-height button. Use filled: true for chrome like «Старт».
Button {
    id: root
    property string tip: ""
    property bool filled: false

    Layout.preferredHeight: ui.controlHeight
    Layout.preferredWidth: ui.controlHeight
    implicitHeight: ui.controlHeight
    implicitWidth: ui.controlHeight
    flat: !filled
    padding: 0
    font.bold: true

    ToolTip.visible: tip.length > 0 && (hovered || guard.containsMouse)
    ToolTip.text: tip

    MouseArea {
        id: guard
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
