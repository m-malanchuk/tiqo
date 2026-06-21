import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import form 1.0
import controls 1.0

AppToolWindow {
    id: dialog
    titleText: t("dialog.schedule")
    bodyWidth: 420
    onRejected: app.closeScheduleDialog()

    FormLabel {
        text: app.scheduleTaskTitle
        font.bold: true
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
    }

    DateCalendar {
        id: calendar
        Layout.fillWidth: true
        Layout.preferredHeight: 300
        selectedDate: new Date(app.scheduleDate + "T00:00:00")
        onDateClicked: {
            function pad(value) { return value < 10 ? "0" + value : String(value) }
            app.setScheduleDate(
                date.getFullYear() + "-" + pad(date.getMonth() + 1) + "-" + pad(date.getDate())
            )
        }
    }

    FormLabel {
        text: app.scheduleDate
        Layout.fillWidth: true
        horizontalAlignment: Text.AlignHCenter
    }

    RowLayout {
        Layout.alignment: Qt.AlignRight
        spacing: ui.padSm
        FormButton {
            text: t("action.cancel")
            onClicked: dialog.reject()
        }
        FormButton {
            text: app.scheduleDateAssigned ? t("action.remove_assignment") : t("action.schedule")
            highlighted: !app.scheduleDateAssigned
            onClicked: app.toggleScheduleDate()
        }
    }
}
