pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2

import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PlasmaComponents
import org.kde.plasma.extras as PlasmaExtras

Item {
    id: root

    required property var plasmoidItem
    required property ListModel taskModel
    required property ListModel listModel

    readonly property int listSpacing: Kirigami.Units.smallSpacing
    readonly property int maxVisibleRows: 5
    property int blockHeight: Math.round(Kirigami.Units.gridUnit * 4.75)

    readonly property int chromeHeight: {
        const margins = Kirigami.Units.smallSpacing * 2;
        const gaps = Kirigami.Units.smallSpacing * 4;
        const err = errorLabel.visible ? (errorLabel.implicitHeight + Kirigami.Units.smallSpacing) : 0;
        return margins
            + heading.implicitHeight
            + listPickerRow.implicitHeight
            + headerSep.implicitHeight
            + gaps
            + footerRow.implicitHeight
            + err;
    }

    readonly property int contentRows: Math.max(1, Math.min(taskModel.count, maxVisibleRows))

    function heightForRows(n) {
        const rows = Math.max(1, n);
        return chromeHeight + rows * blockHeight + (rows - 1) * listSpacing;
    }

    function rowsForHeight(h) {
        const avail = h - chromeHeight;
        if (avail <= 0)
            return 1;
        const n = Math.round((avail + listSpacing) / (blockHeight + listSpacing));
        const cap = Math.max(1, taskModel.count > 0 ? Math.min(taskModel.count, maxVisibleRows) : 1);
        return Math.max(1, Math.min(cap, n));
    }

    readonly property int preferredPopupHeight: heightForRows(contentRows)
    readonly property int minimumPopupHeight: heightForRows(1)
    readonly property int maximumPopupHeight: heightForRows(Math.min(maxVisibleRows, Math.max(1, taskModel.count)))

    onHeightChanged: {
        if (taskModel.count <= 0)
            return;
        const target = heightForRows(rowsForHeight(height));
        if (Math.abs(Layout.preferredHeight - target) > 2)
            Layout.preferredHeight = target;
    }

    onBlockHeightChanged: Layout.preferredHeight = preferredPopupHeight
    onContentRowsChanged: Layout.preferredHeight = preferredPopupHeight

    WorkItemDelegate {
        id: sizeProbe
        visible: false
        width: Math.max(root.width - Kirigami.Units.smallSpacing * 2, Kirigami.Units.gridUnit * 16)
        ordinal: 1
        showSeparator: true
        plasmoidItem: root.plasmoidItem
        item: ({
            task_id: 0,
            title: "Probe",
            state: "paused",
            clock: "0:00",
            is_countdown: false,
            progress: null,
            can_start: true,
            can_pause: false,
            can_stop: true,
            kind: "timed",
            is_completed: false,
            can_complete: false,
        })
        onImplicitHeightChanged: {
            if (implicitHeight > 0)
                root.blockHeight = Math.ceil(implicitHeight);
        }
    }

    function listComboIndex() {
        const want = Number(plasmoidItem.selectedListId);
        for (let i = 0; i < listModel.count; i++) {
            if (Number(listModel.get(i).list_id) === want)
                return i;
        }
        return 0;
    }

    ColumnLayout {
        id: mainCol
        anchors.fill: parent
        anchors.margins: Kirigami.Units.smallSpacing
        spacing: Kirigami.Units.smallSpacing

        PlasmaExtras.Heading {
            id: heading
            Layout.fillWidth: true
            level: 3
            text: {
                const idx = root.listComboIndex();
                const name = (idx >= 0 && idx < listModel.count)
                    ? String(listModel.get(idx).name)
                    : i18n("Tasks");
                return name + " [" + plasmoidItem.taskCount + "]";
            }
            elide: Text.ElideRight
        }

        RowLayout {
            id: listPickerRow
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing

            QQC2.Label {
                text: i18n("List:")
                Layout.alignment: Qt.AlignVCenter
            }

            QQC2.ComboBox {
                id: listCombo
                Layout.preferredWidth: Kirigami.Units.gridUnit * 14
                Layout.maximumWidth: Kirigami.Units.gridUnit * 16
                Layout.fillWidth: false
                model: root.listModel
                textRole: "name"
                currentIndex: root.listComboIndex()
                onActivated: {
                    if (currentIndex >= 0 && currentIndex < root.listModel.count)
                        plasmoidItem.setSelectedListId(root.listModel.get(currentIndex).list_id);
                }
            }

            Item { Layout.fillWidth: true }
        }

        Kirigami.Separator {
            id: headerSep
            Layout.fillWidth: true
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: false
            visible: !plasmoidItem.appOnline
            spacing: Kirigami.Units.smallSpacing

            PlasmaComponents.Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
                text: "tiqo не запущен"
                opacity: 0.8
            }

            Item { Layout.fillHeight: true }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: false
            visible: plasmoidItem.appOnline && plasmoidItem.taskCount === 0
            spacing: Kirigami.Units.smallSpacing

            PlasmaComponents.Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
                text: i18n("No tasks in this list")
                opacity: 0.8
            }

            PlasmaComponents.Button {
                Layout.alignment: Qt.AlignHCenter
                text: "Открыть tiqo"
                icon.name: "window"
                onClicked: plasmoidItem.showWindow()
            }

            Item { Layout.fillHeight: true }
        }

        ListView {
            id: list
            Layout.fillWidth: true
            // Never taller than the real task count — avoids empty gap under the last row.
            Layout.preferredHeight: {
                const count = root.taskModel.count;
                if (count <= 0)
                    return 0;
                const fitted = Math.min(count, root.rowsForHeight(root.height));
                const n = Math.max(1, fitted);
                return n * root.blockHeight + Math.max(0, n - 1) * list.spacing;
            }
            Layout.maximumHeight: {
                const count = root.taskModel.count;
                if (count <= 0)
                    return 0;
                return count * root.blockHeight + Math.max(0, count - 1) * list.spacing;
            }
            Layout.fillHeight: false
            Layout.alignment: Qt.AlignTop
            visible: plasmoidItem.appOnline && plasmoidItem.taskCount > 0
            clip: true
            spacing: root.listSpacing
            model: root.taskModel
            boundsBehavior: Flickable.StopAtBounds
            snapMode: ListView.SnapToItem
            cacheBuffer: root.blockHeight * 3

            delegate: WorkItemDelegate {
                required property int index
                required property int task_id
                required property string title
                required property string state
                required property string clock
                required property bool is_countdown
                required property real progress
                required property bool can_start
                required property bool can_pause
                required property bool can_stop
                required property int depth
                required property string kind
                required property bool is_completed
                required property bool can_complete

                width: list.width
                height: root.blockHeight
                plasmoidItem: root.plasmoidItem
                ordinal: index + 1
                showSeparator: index < root.taskModel.count - 1
                item: ({
                    task_id: task_id,
                    title: title,
                    state: state,
                    clock: clock,
                    is_countdown: is_countdown,
                    progress: progress < 0 ? null : progress,
                    can_start: can_start,
                    can_pause: can_pause,
                    can_stop: can_stop,
                    depth: depth,
                    kind: kind,
                    is_completed: is_completed,
                    can_complete: can_complete,
                })
            }
        }

        PlasmaComponents.Label {
            id: errorLabel
            Layout.fillWidth: true
            visible: plasmoidItem.lastError.length > 0
            text: plasmoidItem.lastError
            wrapMode: Text.WordWrap
            color: Kirigami.Theme.negativeTextColor
            font: Kirigami.Theme.smallFont
        }

        RowLayout {
            id: footerRow
            Layout.fillWidth: true
            visible: plasmoidItem.appOnline

            Item { Layout.fillWidth: true }

            PlasmaComponents.ToolButton {
                icon.name: "window"
                display: PlasmaComponents.AbstractButton.IconOnly
                PlasmaComponents.ToolTip.text: "Открыть tiqo"
                onClicked: plasmoidItem.showWindow()
            }

            PlasmaComponents.ToolButton {
                icon.name: "view-refresh"
                display: PlasmaComponents.AbstractButton.IconOnly
                PlasmaComponents.ToolTip.text: "Обновить"
                onClicked: plasmoidItem.refreshAll()
            }
        }
    }

    Connections {
        target: root.listModel
        function onCountChanged() {
            listCombo.currentIndex = root.listComboIndex();
        }
    }

    Connections {
        target: plasmoidItem
        function onSelectedListIdChanged() {
            listCombo.currentIndex = root.listComboIndex();
        }
    }
}
