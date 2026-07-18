import QtQuick
import QtQuick.Layouts

import form 1.0
import controls 1.0

AppToolWindow {
    id: dialog
    titleText: t("dialog.history_note")
    bodyWidth: 560
    height: 420
    onRejected: app.closeHistoryNoteDialog()
    onOpened: noteField.forceActiveFocus()

    FormLabel {
        text: app.historyNoteTaskTitle
        font.bold: true
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
    }

    FormTextArea {
        id: noteField
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.minimumHeight: ui.controlHeight * 7
        text: app.historyNote
        placeholderText: t("ph.history_note")
        onTextChanged: app.setHistoryNote(text)
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
                app.saveHistoryNote()
                if (!app.historyNoteDialogOpen)
                    dialog.close()
            }
        }
    }
}
