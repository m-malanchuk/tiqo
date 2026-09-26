pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts

import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PlasmaComponents

Item {
    id: root

    required property var plasmoidItem
    required property var item
    property int ordinal: 0
    property bool showSeparator: false

    readonly property bool running: item && item.state === "running"
    readonly property bool canStart: !!(item && item.can_start)
    readonly property bool canPause: !!(item && item.can_pause)
    readonly property bool canStop: !!(item && item.can_stop)
    readonly property bool checklist: !!(item && item.kind === "checklist")
    readonly property bool completed: !!(item && item.is_completed)

    // Countdown: elapsed/target. Stopwatch / no target: always full.
    readonly property real progressValue: {
        if (!item)
            return 0;
        if (root.checklist)
            return root.completed ? 1 : 0;
        if (!item.is_countdown)
            return 1;
        if (item.progress === null || item.progress === undefined)
            return 0;
        const p = Number(item.progress);
        if (!isFinite(p) || p < 0)
            return 0;
        return Math.min(p, 1);
    }

    // Between raw highlight (too deep) and 1.55 (too bright).
    readonly property color barFill: Qt.lighter(Kirigami.Theme.highlightColor, 1.28)

    // Separator slot is always reserved so every row has the same height.
    implicitHeight: col.implicitHeight + Kirigami.Units.smallSpacing * 2
    implicitWidth: parent ? parent.width : Kirigami.Units.gridUnit * 16

    ColumnLayout {
        id: col
        anchors.fill: parent
        anchors.margins: Kirigami.Units.smallSpacing
        spacing: Kirigami.Units.smallSpacing

        RowLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing

            PlasmaComponents.Label {
                id: titleLabel
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignVCenter
                text: "[" + root.ordinal + "]  " + (item ? String(item.title) : "")
                elide: Text.ElideRight
                maximumLineCount: 1
                font.bold: root.running
            }

            PlasmaComponents.Label {
                Layout.alignment: Qt.AlignVCenter
                visible: !root.checklist
                text: item ? String(item.clock) : ""
                font.pointSize: titleLabel.font.pointSize
                opacity: 0.85
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: Math.max(14, Math.round(Kirigami.Units.smallSpacing * 2.5))
            clip: true

            Rectangle {
                anchors.fill: parent
                radius: height / 2
                color: Kirigami.Theme.textColor
                opacity: 0.18
            }

            Rectangle {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                width: Math.round(parent.width * root.progressValue)
                radius: height / 2
                color: root.barFill
                visible: width > 0
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignRight
            spacing: Kirigami.Units.smallSpacing

            PlasmaComponents.ToolButton {
                visible: !root.checklist
                icon.name: "media-playback-start"
                enabled: root.canStart
                display: PlasmaComponents.AbstractButton.IconOnly
                PlasmaComponents.ToolTip.text: "Старт"
                onClicked: plasmoidItem.resumeTask(item.task_id)
            }

            PlasmaComponents.ToolButton {
                visible: !root.checklist
                icon.name: "media-playback-pause"
                enabled: root.canPause
                display: PlasmaComponents.AbstractButton.IconOnly
                PlasmaComponents.ToolTip.text: "Пауза"
                onClicked: plasmoidItem.pauseTask(item.task_id)
            }

            PlasmaComponents.ToolButton {
                visible: !root.checklist
                icon.name: "media-playback-stop"
                enabled: root.canStop
                display: PlasmaComponents.AbstractButton.IconOnly
                PlasmaComponents.ToolTip.text: "Стоп"
                onClicked: plasmoidItem.stopTask(item.task_id)
            }

            PlasmaComponents.ToolButton {
                visible: root.checklist
                text: "✓"
                display: PlasmaComponents.AbstractButton.TextOnly
                PlasmaComponents.ToolTip.text: root.completed ? "Выполнить ещё раз" : "Выполнить"
                onClicked: plasmoidItem.completeChecklist(item.task_id)
            }
        }

        Kirigami.Separator {
            id: separator
            Layout.fillWidth: true
            opacity: root.showSeparator ? 0.6 : 0
        }
    }
}
