import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import form 1.0
import controls 1.0

AppToolWindow {
    id: dialog
    titleText: t("dialog.icon")
    bodyWidth: 520
    // Fixed window so the grid has a real viewport to scroll inside.
    height: 520
    minimumHeight: 400
    onRejected: app.closeEmojiPicker()

    readonly property int cellMin: ui.controlHeight + ui.padSm * 2
    readonly property int scrollBarWidth: 12

    FormTextField {
        placeholderText: t("ph.emoji_search")
        text: app.emojiQuery
        onTextChanged: app.setEmojiQuery(text)
        Layout.fillWidth: true
    }

    Item {
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.minimumHeight: 280

        GridView {
            id: grid
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.right: emojiScrollBar.left
            anchors.rightMargin: ui.padSm
            clip: true
            cellWidth: {
                const cols = Math.max(1, Math.floor(width / dialog.cellMin));
                return Math.floor(width / cols);
            }
            cellHeight: cellWidth
            model: app.emojiModel
            boundsBehavior: Flickable.StopAtBounds
            boundsMovement: Flickable.StopAtBounds
            flickDeceleration: 2500
            maximumFlickVelocity: 4500
            rebound: Transition {}
            // Lightweight cells — FormIconButton's MouseArea(preventStealing)
            // blocked flick/drag scroll over the grid.
            delegate: Item {
                id: cell
                required property string glyph
                required property string codes
                width: grid.cellWidth
                height: grid.cellHeight

                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 2
                    radius: 6
                    color: cellMouse.containsMouse ? Qt.rgba(0.5, 0.5, 0.5, 0.18) : "transparent"
                    border.width: cellMouse.containsMouse ? 1 : 0
                    border.color: Qt.rgba(0.5, 0.5, 0.5, 0.4)
                }

                Text {
                    anchors.centerIn: parent
                    text: cell.glyph
                    font.pixelSize: Math.round(Math.min(cell.width, cell.height) * 0.45)
                }

                MouseArea {
                    id: cellMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    preventStealing: false
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        app.chooseEmoji(cell.glyph)
                        dialog.close()
                    }
                    ToolTip.visible: containsMouse && cell.codes.length > 0
                    ToolTip.text: cell.codes
                    ToolTip.delay: 400
                }
            }

            WheelHandler {
                acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
                onWheel: (event) => {
                    const dy = event.angleDelta.y !== 0
                        ? event.angleDelta.y
                        : event.pixelDelta.y
                    if (dy === 0)
                        return
                    const maxY = Math.max(0, grid.contentHeight - grid.height)
                    grid.contentY = Math.max(0, Math.min(maxY, grid.contentY - dy))
                    event.accepted = true
                }
            }
        }

        ScrollBar {
            id: emojiScrollBar
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            width: dialog.scrollBarWidth
            orientation: Qt.Vertical
            policy: grid.contentHeight > grid.height + 1
                    ? ScrollBar.AlwaysOn
                    : ScrollBar.AlwaysOff
            size: grid.visibleArea.heightRatio
            position: grid.visibleArea.yPosition
            onPositionChanged: {
                if (!pressed)
                    return
                var maxY = Math.max(0, grid.contentHeight - grid.height)
                grid.contentY = position * maxY
            }
        }
    }
}
