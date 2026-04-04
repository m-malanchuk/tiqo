import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import form 1.0
import controls 1.0

AppToolWindow {
    id: dialog
    titleText: t("dialog.new_group")
    bodyWidth: 440
    onOpened: nameField.forceActiveFocus()
    onRejected: app.closeCreateListDialog()

    FormField {
        label: t("field.title")
        FormTextField {
            id: nameField
            text: app.listName
            placeholderText: t("ph.group_name")
            onTextChanged: app.setListName(text)
        }
    }

    FormLabel { text: t("dialog.icon") }
    RowLayout {
        spacing: ui.padSm
        FormIconButton {
            text: app.listIcon
            font.pixelSize: 22
            Layout.preferredWidth: ui.controlHeight + 12
            implicitWidth: ui.controlHeight + 12
            tip: t("hint.tip_pick_emoji")
            onClicked: app.openListEmojiPicker()
        }
        FormHint { text: t("hint.pick_emoji") }
    }

    FormField {
        label: t("field.description")
        FormTextArea {
            Layout.preferredHeight: ui.controlHeight * 2
            text: app.listDescription
            placeholderText: t("ph.group_desc")
            onTextChanged: app.setListDescription(text)
        }
    }

    RowLayout {
        Layout.alignment: Qt.AlignRight
        spacing: ui.padSm
        FormButton {
            text: t("action.cancel")
            onClicked: dialog.reject()
        }
        FormButton {
            text: t("action.create")
            highlighted: true
            onClicked: {
                app.submitCreateListDialog()
                if (!app.listDialogOpen) dialog.close()
            }
        }
    }
}
