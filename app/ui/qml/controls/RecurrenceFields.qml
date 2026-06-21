import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import form 1.0

// Recurrence block for create/edit. Bind kind/interval/weekdays + handlers.
ColumnLayout {
    id: root
    spacing: ui.padSm
    Layout.fillWidth: true

    property string kind: "none"
    property int interval: 1
    property int weekdays: 0

    signal kindChosen(string value)
    signal intervalChosen(int value)
    signal weekdayToggled(int isoDay)

    readonly property string _lang: typeof i18n !== "undefined" ? i18n.language : "ru"
    function t(key) { var _ = _lang; return i18n.t(key) }

    readonly property var kindModel: [
        { value: "none", title: t("recurrence.none") },
        { value: "daily", title: t("recurrence.daily") },
        { value: "every_n_days", title: t("recurrence.every_n") },
        { value: "weekly", title: t("recurrence.weekly") },
        { value: "monthly", title: t("recurrence.monthly") }
    ]

    FormField {
        label: t("field.recurrence")
        Layout.fillWidth: true
        FormComboBox {
            id: kindCombo
            model: root.kindModel.map(function (item) { return item.title })
            onActivated: root.kindChosen(root.kindModel[currentIndex].value)
            Component.onCompleted: syncKind()
            function syncKind() {
                for (var i = 0; i < root.kindModel.length; i++) {
                    if (root.kindModel[i].value === root.kind) {
                        currentIndex = i
                        return
                    }
                }
                currentIndex = 0
            }
            Connections {
                target: root
                function onKindChanged() { kindCombo.syncKind() }
            }
        }
    }

    RowLayout {
        visible: root.kind === "every_n_days"
        spacing: ui.padSm
        Layout.fillWidth: true
        FormLabel { text: t("recurrence.every") }
        FormSpinBox {
            from: 1
            to: 365
            value: Math.max(1, root.interval)
            onValueModified: root.intervalChosen(value)
        }
        FormLabel { text: t("recurrence.days") }
        Item { Layout.fillWidth: true }
    }

    RowLayout {
        visible: root.kind === "monthly"
        spacing: ui.padSm
        Layout.fillWidth: true
        FormLabel { text: t("recurrence.day_number") }
        FormSpinBox {
            from: 1
            to: 31
            value: Math.min(31, Math.max(1, root.interval))
            onValueModified: root.intervalChosen(value)
        }
        FormLabel { text: t("recurrence.of_month") }
        Item { Layout.fillWidth: true }
    }

    ColumnLayout {
        visible: root.kind === "weekly"
        spacing: Math.max(2, ui.padSm / 2)
        Layout.fillWidth: true
        FormLabel { text: t("recurrence.weekdays") }
        RowLayout {
            spacing: ui.padSm
            Layout.fillWidth: true
            Repeater {
                model: [
                    { day: 1, label: t("weekday.mon") },
                    { day: 2, label: t("weekday.tue") },
                    { day: 3, label: t("weekday.wed") },
                    { day: 4, label: t("weekday.thu") },
                    { day: 5, label: t("weekday.fri") },
                    { day: 6, label: t("weekday.sat") },
                    { day: 7, label: t("weekday.sun") }
                ]
                delegate: FormButton {
                    required property var modelData
                    text: modelData.label
                    highlighted: (root.weekdays & (1 << (modelData.day - 1))) !== 0
                    Layout.fillWidth: true
                    onClicked: root.weekdayToggled(modelData.day)
                }
            }
        }
    }
}
