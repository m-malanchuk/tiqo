import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import form 1.0
import "../" as Root

// Qt 6 exposes Controls.Calendar as a style singleton, not a constructible
// control. This small picker is built on the constructible MonthGrid instead.
Item {
    id: root

    property date selectedDate: new Date()
    property int displayedMonth: selectedDate.getMonth() + 1
    property int displayedYear: selectedDate.getFullYear()
    signal dateClicked(var date)

    Root.Theme { id: theme }

    implicitWidth: 300
    width: 300
    implicitHeight: header.implicitHeight + monthGrid.height + ui.padSm

    function pad(value) { return value < 10 ? "0" + value : String(value) }
    function monthTitle() {
        return displayedYear + "-" + pad(displayedMonth)
    }
    function previousMonth() {
        if (displayedMonth === 1) {
            displayedMonth = 12
            displayedYear -= 1
        } else {
            displayedMonth -= 1
        }
    }
    function nextMonth() {
        if (displayedMonth === 12) {
            displayedMonth = 1
            displayedYear += 1
        } else {
            displayedMonth += 1
        }
    }
    function choose(year, month, day) {
        var picked = new Date(year, month - 1, day)
        selectedDate = picked
        dateClicked(picked)
    }

    onSelectedDateChanged: {
        displayedMonth = selectedDate.getMonth() + 1
        displayedYear = selectedDate.getFullYear()
    }

    RowLayout {
        id: header
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: ui.padSm

        FormButton {
            text: "‹"
            Layout.preferredWidth: ui.controlHeight
            onClicked: root.previousMonth()
        }
        FormLabel {
            text: root.monthTitle()
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            font.bold: true
        }
        FormButton {
            text: "›"
            Layout.preferredWidth: ui.controlHeight
            onClicked: root.nextMonth()
        }
    }

    MonthGrid {
        id: monthGrid
        x: 0
        width: root.width
        anchors.top: header.bottom
        anchors.topMargin: ui.padSm
        height: 6 * ui.controlHeight + 5 * (ui.padSm / 2)
        month: root.displayedMonth
        year: root.displayedYear
        spacing: ui.padSm / 2
        delegate: Item {
            required property var model
            width: Math.max(1, (root.width - 6 * monthGrid.spacing) / 7)
            height: ui.controlHeight
            opacity: model.month === root.displayedMonth ? 1 : 0.35

            Rectangle {
                anchors.fill: parent
                radius: ui.radius / 2
                color: model.year === root.selectedDate.getFullYear()
                       && model.month === root.selectedDate.getMonth() + 1
                       && model.day === root.selectedDate.getDate()
                       ? theme.accent
                       : theme.paneBg
                border.width: 1
                border.color: theme.border
                Text {
                    anchors.fill: parent
                    text: String(model.day)
                    color: theme.text
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                MouseArea {
                    anchors.fill: parent
                    enabled: model.month === root.displayedMonth
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.choose(model.year, model.month, model.day)
                }
            }
        }
    }
}
