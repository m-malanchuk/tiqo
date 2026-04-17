import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Templates as T

import ".." as Root

ComboBox {
    id: control

    // +3px: glyph/text was clipping at plain controlHeight on some themes
    readonly property int comboHeight: ui.controlHeight + 3

    Layout.fillWidth: true
    Layout.preferredHeight: comboHeight
    implicitHeight: comboHeight
    implicitWidth: 120
    leftPadding: ui.fieldPadH
    rightPadding: ui.fieldPadH + indicator.width + ui.padSm
    topPadding: 0
    bottomPadding: 0
    padding: 0

    Root.Theme { id: theme }

    // Custom chrome: Breeze/Fusion focus frame was shifting down after reselect.
    background: Rectangle {
        implicitHeight: control.comboHeight
        implicitWidth: 120
        radius: ui.radius
        color: theme.paneBg
        border.width: control.activeFocus || control.down ? 2 : 1
        border.color: control.activeFocus || control.down ? theme.accent : theme.border
    }

    contentItem: T.TextField {
        // KDE's desktop ComboBox style uses TextField APIs for its mobile
        // cursor helper. A plain Text item lacks positionToRectangle().
        text: control.displayText
        font: control.font
        color: theme.text
        opacity: 1.0
        enabled: false
        readOnly: true
        visible: true
        verticalAlignment: Text.AlignVCenter
        clip: true
        leftPadding: 0
        rightPadding: 0
    }

    indicator: Item {
        x: control.width - width - ui.fieldPadH
        y: 0
        height: control.height
        width: 16
        Text {
            anchors.centerIn: parent
            text: "▾"
            color: theme.muted
            font.pixelSize: 12
        }
    }

    HoverHandler {
        enabled: control.enabled
        cursorShape: Qt.PointingHandCursor
    }
}
