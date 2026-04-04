import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import form 1.0
import "../" as Root

// One task row: tree gutter + card. Expects ListView model roles in scope.
Item {
    id: root
    width: ListView.view ? ListView.view.width : parent.width
    height: card.height + ui.padSm / 2

    readonly property string _lang: typeof i18n !== "undefined" ? i18n.language : "ru"
    function t(key) { var _ = _lang; return i18n.t(key) }

    readonly property int step: ui.treeStep
    readonly property int line: ui.treeLine
    readonly property int gutterWidth: depth * step
    readonly property int branchMidY: Math.floor(card.height / 2)

    function colX(col) {
        return col * step + Math.floor(step / 2) - 1
    }

    Root.Theme { id: theme }

    Item {
        id: gutter
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: gutterWidth

        readonly property int joinY: root.branchMidY
        readonly property int col: root.colX(Math.max(0, depth - 1))

        Repeater {
            model: ancestorContinues
            delegate: Rectangle {
                required property int index
                required property var modelData
                visible: !!modelData
                x: root.colX(index)
                y: 0
                width: root.line
                height: gutter.height
                color: theme.border
            }
        }

        // No overlapping fills (overlap + opacity looked like a bright square).
        Rectangle {
            visible: isNested
            x: gutter.col
            y: 0
            width: root.line
            height: gutter.joinY
            color: theme.border
        }
        Rectangle {
            visible: isNested && !isLastSibling
            x: gutter.col
            y: gutter.joinY + root.line
            width: root.line
            height: Math.max(0, gutter.height - gutter.joinY - root.line)
            color: theme.border
        }
        Rectangle {
            visible: isNested
            x: gutter.col
            y: gutter.joinY
            width: Math.max(root.line + 4, root.step - Math.floor(root.step / 2) + 2)
            height: root.line
            color: theme.border
        }
    }

    Rectangle {
        id: card
        anchors.left: gutter.right
        anchors.right: parent.right
        anchors.top: parent.top
        height: Math.max(ui.controlHeight + ui.padMd, body.implicitHeight + ui.padMd)
        radius: ui.radius
        color: workState === "running"
               ? Qt.rgba(theme.accent.r, theme.accent.g, theme.accent.b, 0.12)
               : theme.paneBg
        border.color: workState !== "" ? theme.accent : theme.border
        border.width: 1

        // RMB anywhere on the card → same edit dialog as ✎
        TapHandler {
            acceptedButtons: Qt.RightButton
            cursorShape: Qt.PointingHandCursor
            onTapped: app.openEditDialog(taskId)
        }

        RowLayout {            id: body
            anchors.fill: parent
            anchors.margins: ui.padSm
            spacing: ui.padSm

            FormIconButton {
                visible: hasChildren
                filled: true
                text: isExpanded ? "▾" : "▸"
                tip: isExpanded ? t("tip.collapse") : t("tip.expand")
                font.bold: false
                onClicked: app.toggleExpanded(taskId)
            }

            Item {
                Layout.fillWidth: true
                Layout.fillHeight: false
                Layout.alignment: Qt.AlignVCenter
                Layout.minimumWidth: 80
                implicitHeight: textCol.implicitHeight

                ColumnLayout {
                    id: textCol
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 2
                    Label {
                        text: title
                        font.bold: workState === "running" || depth === 0
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                    Label {
                        visible: description.length > 0
                        text: description
                        color: theme.muted
                        wrapMode: Text.WordWrap
                        maximumLineCount: 2
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                }
                // TapHandler only — MouseArea was stealing presses from nearby controls
                TapHandler {
                    cursorShape: Qt.PointingHandCursor
                    onDoubleTapped: app.openEditDialog(taskId)
                }
            }

            Label {
                text: kind === "checklist"
                      ? t("task_kind.checklist")
                      : (mode === "countdown" ? t("mode.countdown") : t("mode.stopwatch"))
                color: theme.muted
                font.pixelSize: 12
                Layout.fillWidth: false
                Layout.minimumWidth: implicitWidth
                // Extra gap before clock / pause so «Секундомер» + status do not melt together
                Layout.rightMargin: ui.padMd
            }
            Label {
                id: clockLabel
                visible: kind !== "checklist"
                text: timeToday
                // Digits stay mono; pause label uses the normal UI font
                font.family: workState === "paused" ? Qt.application.font.family : "monospace"
                color: workState === "paused" ? theme.muted : theme.text
                Layout.preferredWidth: workState === "paused" ? Math.max(72, implicitWidth) : 72
                Layout.minimumWidth: 72
                Layout.fillWidth: false
                Layout.leftMargin: ui.padSm
                horizontalAlignment: Text.AlignRight
            }

            // Keep action cluster from shrinking so far-right clicks always hit
            RowLayout {
                id: actions
                spacing: ui.padSm
                Layout.fillWidth: false
                Layout.minimumWidth: implicitWidth
                Layout.alignment: Qt.AlignVCenter

                FormIconButton {
                    filled: true
                    text: "+"
                    tip: t("tip.subtask")
                    Layout.fillWidth: false
                    onClicked: app.openCreateSubtask(taskId)
                }
                FormIconButton {
                    filled: true
                    text: "✎"
                    tip: t("tip.edit")
                    font.bold: false
                    Layout.fillWidth: false
                    onClicked: app.openEditDialog(taskId)
                }
                FormIconButton {
                    filled: true
                    text: isScheduledToday ? "✓" : "📅"
                    tip: isScheduledToday ? t("action.remove_today") : t("action.add_today")
                    font.bold: false
                    Layout.fillWidth: false
                    onClicked: app.openScheduleDialog(taskId)
                }
                FormIconButton {
                    visible: workState !== ""
                    filled: true
                    text: "✐"
                    tip: t("tip.session_note")
                    font.bold: false
                    Layout.fillWidth: false
                    onClicked: app.openSessionNoteDialog(taskId)
                }
                FormButton {
                    visible: kind !== "checklist"
                    text: t("action.start")
                    enabled: canStart
                    Layout.fillWidth: false
                    Layout.minimumWidth: implicitWidth
                    onClicked: app.startTask(taskId)
                }
                FormButton {
                    visible: kind !== "checklist"
                    text: t("action.pause")
                    enabled: canPause
                    Layout.fillWidth: false
                    Layout.minimumWidth: implicitWidth
                    onClicked: app.pauseTask(taskId)
                }
                FormButton {
                    visible: kind !== "checklist"
                    text: t("action.stop")
                    enabled: canStop
                    Layout.fillWidth: false
                    Layout.minimumWidth: implicitWidth
                    onClicked: app.stopTask(taskId)
                }
                FormButton {
                    id: completeButton
                    visible: kind === "checklist"
                    text: "✓  " + (isCompleted ? t("action.complete_again") : t("action.complete"))
                    highlighted: false
                    Layout.fillWidth: false
                    Layout.preferredWidth: 140
                    Layout.minimumWidth: 132
                    onClicked: app.completeChecklist(taskId)
                }
            }
        }
    }
}
