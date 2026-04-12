import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import form 1.0
import controls 1.0

AppToolWindow {
    id: dialog
    titleText: t("dialog.delete_task")
    bodyWidth: 460
    onRejected: app.closeDeleteDialog()

    FormLabel {
        text: t1("delete.quote", app.deleteTaskTitle)
        font.bold: true
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
    }

    FormHint {
        text: app.deleteHasChildren
              ? t2("delete.stats_tree", app.deleteChildCount, app.deleteSessionCount)
              : t1("delete.stats_one", app.deleteSessionCount)
    }

    ColumnLayout {
        spacing: Math.max(2, ui.padSm / 2)
        visible: app.deleteHasChildren
        Layout.fillWidth: true

        FormLabel { text: t("delete.what") }
        FormRadioButton {
            text: t("delete.this_only")
            checked: app.deleteMode === "this_only"
            onClicked: app.setDeleteMode("this_only")
        }
        FormRadioButton {
            text: t("delete.cascade")
            checked: app.deleteMode === "cascade"
            onClicked: app.setDeleteMode("cascade")
        }
    }

    FormHint {
        visible: !app.deleteHasChildren
        text: t("delete.warn_simple")
    }

    FormHint {
        visible: app.deleteHasChildren && app.deleteMode === "this_only"
        text: t("delete.warn_this_only")
    }

    FormHint {
        visible: app.deleteHasChildren && app.deleteMode === "cascade"
        text: t("delete.warn_cascade")
    }

    RowLayout {
        Layout.alignment: Qt.AlignRight
        spacing: ui.padSm
        FormButton {
            text: t("action.cancel")
            onClicked: dialog.reject()
        }
        FormButton {
            text: t("action.delete")
            highlighted: true
            onClicked: {
                app.confirmDeleteTask()
                if (!app.deleteDialogOpen) dialog.close()
            }
        }
    }
}
