import QtQuick
import QtQuick.Layouts

import form 1.0
import controls 1.0

AppToolWindow {
    id: dialog
    titleText: t("dialog.checklist_completion")
    bodyWidth: 560
    height: 420
    onRejected: app.cancelChecklistCompletion()
    onOpened: noteField.forceActiveFocus()

    FormLabel {
        text: app.checklistCompletionTaskTitle
        font.bold: true
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
    }

    FormTextArea {
        id: noteField
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.minimumHeight: ui.controlHeight * 7
        text: app.checklistCompletionNote
        placeholderText: t("ph.checklist_note")
        onTextChanged: app.setChecklistCompletionNote(text)
    }

    RowLayout {
        Layout.alignment: Qt.AlignRight
        spacing: ui.padSm
        FormButton {
            text: t("action.cancel")
            onClicked: dialog.reject()
        }
        FormButton {
            text: t("action.complete")
            highlighted: true
            onClicked: {
                app.confirmChecklistCompletion()
                if (!app.checklistCompletionDialogOpen)
                    dialog.close()
            }
        }
    }
}
