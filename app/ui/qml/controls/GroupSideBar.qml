import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import form 1.0
import "../" as Root

Frame {
    id: root
    property bool collapsed: false

    readonly property string _lang: typeof i18n !== "undefined" ? i18n.language : "ru"
    function t(key) { var _ = _lang; return i18n.t(key) }

    // Do not bind min/max to preferredWidth (binding loop → width stuck open).
    readonly property int paneWidth: collapsed
                                     ? Math.max(ui.controlHeight + 2 * ui.padSm, 48)
                                     : ui.listWidth

    Layout.preferredWidth: paneWidth
    Layout.minimumWidth: paneWidth
    Layout.maximumWidth: paneWidth
    Layout.fillHeight: true
    Layout.fillWidth: false

    padding: 0

    background: Rectangle {
        color: sideTheme.paneBg
        radius: ui.radius
        border.color: sideTheme.border
    }

    Root.Theme { id: sideTheme }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: ui.padSm
        spacing: root.collapsed ? 4 : ui.padSm / 2

        RowLayout {
            Layout.fillWidth: true
            Layout.alignment: root.collapsed ? Qt.AlignHCenter : Qt.AlignLeft
            spacing: ui.padSm / 2

            FormIconButton {
                text: root.collapsed ? "▸" : "◂"
                tip: root.collapsed ? t("groups.expand") : t("groups.collapse")
                font.bold: false
                onClicked: root.collapsed = !root.collapsed
            }
            FormLabel {
                visible: !root.collapsed
                text: t("groups.title")
                font.bold: true
                Layout.fillWidth: true
            }
            FormIconButton {
                visible: !root.collapsed
                text: "⚙"
                tip: t("tip.settings")
                font.bold: false
                onClicked: settings.openSettings()
            }
        }

        FormIconButton {
            visible: root.collapsed
            Layout.alignment: Qt.AlignHCenter
            text: "⚙"
            tip: t("tip.settings")
            font.bold: false
            onClicked: settings.openSettings()
        }

        FormIconButton {
            visible: root.collapsed
            Layout.alignment: Qt.AlignHCenter
            text: "+"
            tip: t("dialog.new_group")
            font.bold: true
            onClicked: app.openCreateListDialog()
        }

        ItemDelegate {
            visible: !root.collapsed
            Layout.fillWidth: true
            Layout.preferredHeight: ui.rowHeight
            onClicked: app.openCreateListDialog()
            HoverHandler { cursorShape: Qt.PointingHandCursor }
            contentItem: RowLayout {
                spacing: ui.padSm
                Label {
                    text: "+"
                    font.pixelSize: 18
                    font.bold: true
                    Layout.preferredWidth: 28
                    horizontalAlignment: Text.AlignHCenter
                }
                Label {
                    text: t("dialog.new_group")
                    color: sideTheme.muted
                    Layout.fillWidth: true
                }
            }
        }

        ListView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: app.lists
            spacing: root.collapsed ? 2 : 0
            boundsBehavior: Flickable.StopAtBounds
            delegate: ItemDelegate {
                width: ListView.view.width
                height: root.collapsed
                        ? ui.controlHeight + 4
                        : ui.rowHeight
                highlighted: listId === app.selectedListId
                padding: root.collapsed ? 2 : 6
                onClicked: app.selectList(listId)
                HoverHandler { cursorShape: Qt.PointingHandCursor }
                contentItem: RowLayout {
                    spacing: ui.padSm
                    anchors.horizontalCenter: root.collapsed ? parent.horizontalCenter : undefined

                    FormIconButton {
                        text: listIcon
                        font.bold: false
                        font.pixelSize: 18
                        Layout.alignment: Qt.AlignHCenter
                        tip: root.collapsed ? name : t("groups.change_icon")
                        onClicked: {
                            if (root.collapsed)
                                app.selectList(listId)
                            else
                                app.openEmojiPicker(listId)
                        }
                    }
                    Label {
                        visible: !root.collapsed
                        text: name
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                        font.bold: listId === app.selectedListId
                    }
                }
            }
        }

    }
}
