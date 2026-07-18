import QtQuick
import QtQuick.Layouts

import form 1.0
import controls 1.0

AppToolWindow {
    id: dialog
    titleText: t("dialog.session_note")
    bodyWidth: 480
    onRejected: app.closeSessionNoteDialog()
    onOpened: noteField.forceActiveFocus()

    FormLabel {
        text: app.sessionNoteTaskTitle
        font.bold: true
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
    }

    FormTextArea {
        id: noteField
        Layout.fillWidth: true
        Layout.preferredHeight: ui.controlHeight * 3
        text: app.sessionNote
        placeholderText: t("ph.session_note")
        onTextChanged: app.setSessionNote(text)
    }

    RowLayout {
        Layout.alignment: Qt.AlignRight
        spacing: ui.padSm
        FormButton {
            text: t("action.cancel")
            onClicked: dialog.reject()
        }
        FormButton {
            text: t("action.save")
            highlighted: true
            onClicked: {
                app.saveSessionNote()
                if (!app.sessionNoteDialogOpen) dialog.close()
            }
        }
    }
}
