import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import form 1.0
import controls 1.0

AppToolWindow {
    id: dialog
    titleText: t("dialog.start_session")
    bodyWidth: 480
    onOpened: noteField.forceActiveFocus()
    onRejected: app.closeStartDialog()

    FormLabel {
        text: app.startTaskTitle
        font.bold: true
        font.pixelSize: 15
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
    }

    FormField {
        label: t("field.session_note")
        FormTextArea {
            id: noteField
            Layout.preferredHeight: ui.controlHeight * 2.5
            text: app.startNote
            placeholderText: t("ph.session_note")
            onTextChanged: app.setStartNote(text)
        }
    }

    FormHint { text: t("hint.start_tracking") }

    RowLayout {
        Layout.alignment: Qt.AlignRight
        spacing: ui.padSm
        FormButton {
            text: t("action.cancel")
            onClicked: dialog.reject()
        }
        FormButton {
            text: t("action.begin")
            highlighted: true
            onClicked: {
                app.confirmStart()
                if (!app.startDialogOpen) dialog.close()
            }
        }
    }
}
