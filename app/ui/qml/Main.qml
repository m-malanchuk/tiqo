import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import form 1.0
import controls 1.0

ApplicationWindow {
    id: root
    visible: true
    width: 1100
    height: 700
    minimumWidth: 1000
    minimumHeight: 720
    title: t("app.name")
    color: theme.panelBg
    // Title-bar mark: set from Python via setIcon + hicolor ``tiqo`` (KWin).
    // QML ApplicationWindow here has no assignable ``icon.source``.

    readonly property string _lang: typeof i18n !== "undefined" ? i18n.language : "ru"
    function t(key) { var _ = _lang; return i18n.t(key) }
    function t1(key, a) { var _ = _lang; return i18n.t1(key, String(a)) }
    function t2(key, a, b) { var _ = _lang; return i18n.t2(key, String(a), String(b)) }

    // Close → tray (default) or quit — from settings.closeToTray
    onClosing: function (close) {
        if (typeof settings !== "undefined" && settings && !settings.closeToTray) {
            close.accepted = true
            Qt.quit()
            return
        }
        close.accepted = false
        if (typeof windowBridge !== "undefined" && windowBridge)
            windowBridge.hideWindow()
        else
            root.visible = false
    }

    Theme { id: theme }

    // Tool windows (separate Plasma/Qt windows — not overlay Dialogs)
    CreateTaskDialog { id: createDialog }
    CreateListDialog { id: createListDialog }
    EditTaskDialog { id: editDialog }
    DeleteConfirmDialog { id: deleteDialog }
    StartSessionDialog { id: startDialog }
    EmojiPickerDialog { id: emojiDialog }
    SettingsWindow { id: settingsWindow }
    HistoryWindow { id: historyWindow }
    HistoryNoteDialog { id: historyNoteDialog }
    ScheduleDialog { id: scheduleDialog }
    SessionNoteDialog { id: sessionNoteDialog }

    Connections {
        target: app
        function onCreateDialogOpenChanged() {
            if (app.createDialogOpen) createDialog.open(); else createDialog.close()
        }
        function onListDialogOpenChanged() {
            if (app.listDialogOpen) createListDialog.open(); else createListDialog.close()
        }
        function onEditDialogOpenChanged() {
            if (app.editDialogOpen) editDialog.open(); else editDialog.close()
        }
        function onDeleteDialogOpenChanged() {
            if (app.deleteDialogOpen) deleteDialog.open(); else deleteDialog.close()
        }
        function onStartDialogOpenChanged() {
            if (app.startDialogOpen) startDialog.open(); else startDialog.close()
        }
        function onEmojiPickerOpenChanged() {
            if (app.emojiPickerOpen) emojiDialog.open(); else emojiDialog.close()
        }
        function onHistoryDialogOpenChanged() {
            if (app.historyDialogOpen) historyWindow.open(); else historyWindow.close()
        }
        function onHistoryNoteDialogChanged() {
            if (app.historyNoteDialogOpen) historyNoteDialog.open(); else historyNoteDialog.close()
        }
        function onScheduleDialogOpenChanged() {
            if (app.scheduleDialogOpen) scheduleDialog.open(); else scheduleDialog.close()
        }
        function onSessionNoteDialogOpenChanged() {
            if (app.sessionNoteDialogOpen) sessionNoteDialog.open(); else sessionNoteDialog.close()
        }
    }

    Connections {
        target: settings
        function onOpenChanged() {
            if (settings.open) settingsWindow.open(); else settingsWindow.close()
        }
    }

    footer: Rectangle {
        color: theme.panelBg
        implicitHeight: statusLabel.implicitHeight + ui.padSm + ui.padLg
        Label {
            id: statusLabel
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.leftMargin: ui.padMd
            anchors.rightMargin: ui.padMd
            anchors.topMargin: ui.padSm
            text: app.statusMessage
            color: theme.text
            font.bold: true
            elide: Text.ElideRight
            opacity: app.statusMessage.length > 0 ? 1.0 : 0.35
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: ui.padSm
        spacing: ui.padSm

        ColumnLayout {
            id: groupsColumn
            Layout.preferredWidth: groupSideBar.paneWidth
            Layout.minimumWidth: groupSideBar.paneWidth
            Layout.maximumWidth: groupSideBar.paneWidth
            Layout.fillHeight: true
            Layout.fillWidth: false
            spacing: ui.padSm

            GroupSideBar {
                id: groupSideBar
                Layout.fillWidth: true
                Layout.fillHeight: true
            }

            FormButton {
                visible: !groupSideBar.collapsed
                Layout.fillWidth: true
                text: t("list.completed")
                highlighted: false
                onClicked: app.openHistory()
            }
            FormIconButton {
                visible: groupSideBar.collapsed
                Layout.alignment: Qt.AlignHCenter
                text: "☷"
                tip: t("list.completed")
                onClicked: app.openHistory()
            }
        }

        Frame {
            Layout.fillWidth: true
            Layout.fillHeight: true
            background: Rectangle {
                color: theme.paneBg
                radius: ui.radius
                border.color: theme.border
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: ui.padMd
                spacing: ui.padMd

                RowLayout {
                    Layout.fillWidth: true
                    FormLabel {
                        text: t("app.name")
                        font.bold: true
                        font.pixelSize: 18
                    }
                    Item { Layout.fillWidth: true }
                    FormButton {
                        text: t("action.add_task")
                        highlighted: true
                        onClicked: app.openCreateDialog()
                    }
                }

                EmptyState {
                    visible: taskView.count === 0
                    listId: app.selectedListId
                    Layout.fillWidth: true
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    ListView {
                        id: taskView
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        anchors.right: taskScrollBar.left
                        anchors.rightMargin: 4
                        clip: true
                        model: app.tasks
                        spacing: 0
                        pressDelay: 120
                        boundsBehavior: Flickable.StopAtBounds
                        boundsMovement: Flickable.StopAtBounds
                        flickDeceleration: 3000
                        maximumFlickVelocity: 4000
                        rebound: Transition {}
                        delegate: TaskCard { }
                        // Wheel / touchpad drive contentY; scrollbar follows via Binding below
                    }

                    ScrollBar {
                        id: taskScrollBar
                        anchors.top: parent.top
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        width: 10
                        orientation: Qt.Vertical
                        policy: taskView.contentHeight > taskView.height
                                ? ScrollBar.AlwaysOn
                                : ScrollBar.AlwaysOff
                        size: taskView.visibleArea.heightRatio
                        position: taskView.visibleArea.yPosition
                        onPositionChanged: {
                            if (!pressed)
                                return
                            var maxY = Math.max(0, taskView.contentHeight - taskView.height)
                            taskView.contentY = position * maxY
                        }
                    }
                }
            }
        }
    }
}
