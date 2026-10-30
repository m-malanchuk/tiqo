import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import form 1.0
import controls 1.0

AppToolWindow {
    id: dialog
    titleText: t("dialog.new_task")
    bodyWidth: 480
    onOpened: titleField.forceActiveFocus()
    onRejected: app.closeCreateDialog()

    FormHint { text: app.createListHint }

    FormField {
        label: t("field.group")
        FormComboBox {
            id: groupCombo
            model: app.listPicker
            textRole: "title"
            valueRole: "taskId"
            onActivated: app.setCreateListId(currentValue)
            Component.onCompleted: syncGroup()
            function syncGroup() {
                for (var i = 0; i < count; i++) {
                    if (model.data(model.index(i, 0), 257) === app.createListId) {
                        currentIndex = i
                        return
                    }
                }
            }
        }
    }

    FormCheckBox {
        text: t("action.add_to_favorites")
        checked: app.createIsFavorite
        onClicked: app.setCreateFavorite(checked)
    }

    FormField {
        label: t("field.title")
        FormTextField {
            id: titleField
            text: app.createTitle
            placeholderText: t("ph.task_title")
            onTextChanged: app.setCreateTitle(text)
        }
    }

    FormField {
        label: t("field.description")
        FormTextArea {
            Layout.preferredHeight: ui.controlHeight * 2
            text: app.createDescription
            placeholderText: t("ph.task_desc_short")
            onTextChanged: app.setCreateDescription(text)
        }
    }

    ColumnLayout {
        spacing: Math.max(2, ui.padSm / 2)
        Layout.fillWidth: true
        FormLabel { text: t("field.task_kind") }
        RowLayout {
            spacing: ui.padMd
            FormRadioButton {
                text: t("task_kind.timed")
                checked: app.createKind === "timed"
                onClicked: app.setCreateKind("timed")
            }
            FormRadioButton {
                text: t("task_kind.checklist")
                checked: app.createKind === "checklist"
                onClicked: app.setCreateKind("checklist")
            }
        }
    }

    ColumnLayout {
        visible: app.createKind === "timed"
        spacing: Math.max(2, ui.padSm / 2)
        Layout.fillWidth: true
        FormLabel { text: t("field.type") }
        RowLayout {
            spacing: ui.padMd
            FormRadioButton {
                text: t("mode.stopwatch")
                checked: app.createMode === "stopwatch"
                onClicked: app.setCreateMode("stopwatch")
            }
            FormRadioButton {
                text: t("mode.countdown")
                checked: app.createMode === "countdown"
                onClicked: app.setCreateMode("countdown")
            }
        }
    }

    RowLayout {
        visible: app.createKind === "timed" && app.createMode === "countdown"
        spacing: ui.padSm
        FormLabel { text: t("field.duration") }
        FormSpinBox {
            from: 0; to: 23; value: app.createHours
            onValueModified: app.setCreateHours(value)
        }
        FormLabel { text: t("field.hours") }
        FormSpinBox {
            from: 0; to: 59; value: app.createMinutes
            onValueModified: app.setCreateMinutes(value)
        }
        FormLabel { text: t("field.minutes") }
    }

    RecurrenceFields {
        kind: app.createRecurrenceKind
        interval: app.createRecurrenceInterval
        weekdays: app.createRecurrenceWeekdays
        onKindChosen: app.setCreateRecurrenceKind(value)
        onIntervalChosen: app.setCreateRecurrenceInterval(value)
        onWeekdayToggled: app.toggleCreateWeekday(isoDay)
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
                app.submitCreateDialog()
                if (!app.createDialogOpen) dialog.close()
            }
        }
    }
}
