import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import form 1.0
import controls 1.0

AppToolWindow {
    id: dialog
    titleText: t("dialog.edit_task")
    bodyWidth: 520
    onRejected: app.closeEditDialog()

    FormField {
        label: t("field.title")
        Layout.fillWidth: true
        FormTextField {
            text: app.editTitle
            onTextChanged: app.setEditTitle(text)
        }
    }

    FormCheckBox {
        text: t("action.add_to_favorites")
        checked: app.editIsFavorite
        enabled: app.editListId !== 1
        onClicked: app.setEditFavorite(checked)
    }

    FormField {
        label: t("field.group")
        hint: t("hint.edit_group")
        Layout.fillWidth: true
        FormComboBox {
            id: editGroupCombo
            model: app.listPicker
            textRole: "title"
            valueRole: "taskId"
            onActivated: app.setEditListId(currentValue)
            Component.onCompleted: syncGroup()
            function syncGroup() {
                for (var i = 0; i < count; i++) {
                    if (model.data(model.index(i, 0), 257) === app.editListId) {
                        currentIndex = i
                        return
                    }
                }
            }
            Connections {
                target: app
                function onEditDialogOpenChanged() {
                    if (app.editDialogOpen)
                        editGroupCombo.syncGroup()
                }
                function onEditListIdChanged() { editGroupCombo.syncGroup() }
            }
        }
    }

    FormField {
        label: t("field.description")
        Layout.fillWidth: true
        FormTextArea {
            Layout.preferredHeight: ui.controlHeight * 2.5
            text: app.editDescription
            placeholderText: t("ph.task_desc_full")
            onTextChanged: app.setEditDescription(text)
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
                checked: app.editKind === "timed"
                onClicked: app.setEditKind("timed")
            }
            FormRadioButton {
                text: t("task_kind.checklist")
                checked: app.editKind === "checklist"
                onClicked: app.setEditKind("checklist")
            }
        }
    }

    ColumnLayout {
        visible: app.editKind === "timed"
        spacing: Math.max(2, ui.padSm / 2)
        Layout.fillWidth: true
        FormLabel { text: t("field.type") }
        RowLayout {
            spacing: ui.padMd
            FormRadioButton {
                text: t("mode.stopwatch")
                checked: app.editMode === "stopwatch"
                onClicked: app.setEditMode("stopwatch")
            }
            FormRadioButton {
                text: t("mode.countdown")
                checked: app.editMode === "countdown"
                onClicked: app.setEditMode("countdown")
            }
        }
    }

    RowLayout {
        visible: app.editKind === "timed" && app.editMode === "countdown"
        spacing: ui.padSm
        Layout.fillWidth: true
        FormLabel { text: t("field.duration") }
        FormSpinBox {
            from: 0; to: 23; value: app.editHours
            onValueModified: app.setEditHours(value)
        }
        FormLabel { text: t("field.hours") }
        FormSpinBox {
            from: 0; to: 59; value: app.editMinutes
            onValueModified: app.setEditMinutes(value)
        }
        FormLabel { text: t("field.minutes") }
    }

    RecurrenceFields {
        kind: app.editRecurrenceKind
        interval: app.editRecurrenceInterval
        weekdays: app.editRecurrenceWeekdays
        onKindChosen: app.setEditRecurrenceKind(value)
        onIntervalChosen: app.setEditRecurrenceInterval(value)
        onWeekdayToggled: app.toggleEditWeekday(isoDay)
    }

    FormButton {
        Layout.fillWidth: true
        text: t("action.schedule")
        onClicked: app.openScheduleDialog(app.editTaskId)
    }

    ParentPicker { Layout.fillWidth: true }

    Flow {
        Layout.fillWidth: true
        spacing: ui.padSm
        FormButton {
            text: t("action.remove_from_group")
            visible: app.editCanRemoveFromGroup
            onClicked: app.removeEditTaskFromGroup()
        }
        FormButton {
            text: t("action.unparent")
            visible: app.editCanUnparent
            onClicked: app.unparentEditTask()
        }
        FormButton {
            text: t("action.delete")
            onClicked: app.requestDeleteTask()
        }
    }

    RowLayout {
        Layout.fillWidth: true
        Item { Layout.fillWidth: true }
        FormButton {
            text: t("action.cancel")
            onClicked: dialog.reject()
        }
        FormButton {
            text: t("action.save")
            highlighted: true
            onClicked: {
                app.submitEditDialog()
                if (!app.editDialogOpen) dialog.close()
            }
        }
    }
}
