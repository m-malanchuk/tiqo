import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import form 1.0
import controls 1.0

AppToolWindow {
    id: dialog
    titleText: t("dialog.history")
    bodyWidth: 1240
    width: Math.max(bodyWidth, minimumHistoryWidth)
    minimumWidth: minimumHistoryWidth
    height: 720
    property var selectedCompletionIds: []
    property int selectionAnchorIndex: -1
    property bool updatingCurrentIndex: false
    property int customDateColumnWidth: 0
    property int customTaskColumnWidth: 0
    property int customTypeColumnWidth: 0
    property int customDurationColumnWidth: 0
    property int customStartColumnWidth: 0
    property int customEndColumnWidth: 0
    property int customNoteColumnWidth: 0

    // The base widths define readable proportions; every data column grows
    // together when the window is widened. The note column receives the
    // rounding remainder so the grid always closes exactly at its edge.
    readonly property int baseDataTableWidth: 1001
    readonly property int dateTextWidth: Math.ceil(dateMetrics.width)
    readonly property int timestampTextWidth: Math.ceil(timestampMetrics.width)
    readonly property int minimumDateColumnWidth: Math.max(108, dateTextWidth + 2 * 6 + 4)
    readonly property int minimumTimestampColumnWidth: Math.max(160, timestampTextWidth + 2 * ui.fieldPadH + 4)
    readonly property int dateColumnWidth: customDateColumnWidth > 0
        ? customDateColumnWidth
        : Math.max(minimumDateColumnWidth, Math.round(dataTableWidth * 94 / baseDataTableWidth))
    readonly property int taskColumnWidth: customTaskColumnWidth > 0
        ? customTaskColumnWidth
        : Math.round(dataTableWidth * 210 / baseDataTableWidth)
    readonly property int typeColumnWidth: customTypeColumnWidth > 0
        ? customTypeColumnWidth
        : Math.round(dataTableWidth * 115 / baseDataTableWidth)
    readonly property int durationColumnWidth: customDurationColumnWidth > 0
        ? customDurationColumnWidth
        : Math.max(124, Math.round(dataTableWidth * 112 / baseDataTableWidth))
    readonly property int startColumnWidth: customStartColumnWidth > 0
        ? customStartColumnWidth
        : Math.max(minimumTimestampColumnWidth, Math.round(dataTableWidth * 145 / baseDataTableWidth))
    readonly property int endColumnWidth: customEndColumnWidth > 0
        ? customEndColumnWidth
        : Math.max(minimumTimestampColumnWidth, Math.round(dataTableWidth * 145 / baseDataTableWidth))
    readonly property int actionColumnWidth: 124
    readonly property color selectionBackground: Qt.rgba(
        historyTheme.accent.r,
        historyTheme.accent.g,
        historyTheme.accent.b,
        0.18
    )
    readonly property int tableWidth: Math.max(0, dialog.width - 2 * ui.padMd)
    readonly property int actionAreaWidth: 2 * actionColumnWidth + 2 * ui.padSm
    readonly property int minimumDataTableWidth: minimumDateColumnWidth + 180 + 100 + 124
        + 2 * minimumTimestampColumnWidth + 120
    readonly property int minimumHistoryWidth: minimumDataTableWidth + actionAreaWidth + 2 * ui.padMd
    // Reserve the action area first. This keeps both buttons inside the
    // window even while the user is shrinking it.
    readonly property int dataTableWidth: Math.max(0, tableWidth - actionAreaWidth)
    readonly property int noteColumnWidth: customNoteColumnWidth > 0
        ? customNoteColumnWidth
        : dataTableWidth - dateColumnWidth - taskColumnWidth - typeColumnWidth
            - durationColumnWidth - startColumnWidth - endColumnWidth
    onRejected: app.closeHistory()
    onOpened: {
        app.refreshHistory()
        historyView.forceActiveFocus()
    }

    Theme { id: historyTheme }

    TextMetrics {
        id: dateMetrics
        text: "0000-00-00"
        font: Qt.application.font
    }
    TextMetrics {
        id: timestampMetrics
        text: "0000-00-00 00:00"
        font: Qt.application.font
    }

    Connections {
        target: app
        function onHistoryDialogChanged() { dialog.clearSelection() }
    }

    function formatDate(value) {
        function pad(number) { return number < 10 ? "0" + number : String(number) }
        return value.getFullYear() + "-" + pad(value.getMonth() + 1) + "-" + pad(value.getDate())
    }

    function dateFromText(value) {
        return value.length > 0 ? new Date(value + "T00:00:00") : new Date()
    }

    function sortIndicator(key) {
        if (app.historySortKey === key)
            return app.historySortAscending ? "▲" : "▼"
        return "▲▼"
    }

    function sortColumn(key) {
        app.setHistorySort(key)
    }

    function isSelected(completionId) {
        return selectedCompletionIds.indexOf(completionId) >= 0
    }

    function selectRow(completionId, rowIndex, modifiers) {
        var ids = selectedCompletionIds.slice()
        if (modifiers & Qt.ShiftModifier && selectionAnchorIndex >= 0) {
            var first = Math.min(selectionAnchorIndex, rowIndex)
            var last = Math.max(selectionAnchorIndex, rowIndex)
            ids = []
            for (var i = first; i <= last; i++) {
                var completionIdAt = app.historyIdAt(i)
                if (completionIdAt > 0)
                    ids.push(completionIdAt)
            }
        } else if (modifiers & Qt.ControlModifier) {
            var existing = ids.indexOf(completionId)
            if (existing >= 0)
                ids.splice(existing, 1)
            else
                ids.push(completionId)
            selectionAnchorIndex = rowIndex
        } else {
            ids = [completionId]
            selectionAnchorIndex = rowIndex
        }
        selectedCompletionIds = ids
        updatingCurrentIndex = true
        historyView.currentIndex = rowIndex
        historyView.forceActiveFocus()
        updatingCurrentIndex = false
    }

    function clearSelection() {
        selectedCompletionIds = []
        selectionAnchorIndex = -1
    }

    function copySelection() {
        var ids = selectedCompletionIds.slice()
        if (ids.length === 0 && historyView.currentItem)
            ids = [historyView.currentItem.completionId]
        if (ids.length === 0 || typeof windowBridge === "undefined" || !windowBridge)
            return
        var lines = []
        for (var i = 0; i < ids.length; i++) {
            var line = app.historyRowText(ids[i])
            if (line.length > 0)
                lines.push(line)
        }
        if (lines.length > 0)
            windowBridge.copyText(lines.join("\n"))
    }

    function columnMinimum(key) {
        if (key === "date") return minimumDateColumnWidth
        if (key === "start" || key === "end") return minimumTimestampColumnWidth
        if (key === "duration") return 124
        if (key === "task") return 120
        if (key === "type") return 90
        return 100
    }

    function columnWidth(key) {
        if (key === "date") return dateColumnWidth
        if (key === "task") return taskColumnWidth
        if (key === "type") return typeColumnWidth
        if (key === "duration") return durationColumnWidth
        if (key === "start") return startColumnWidth
        if (key === "end") return endColumnWidth
        return noteColumnWidth
    }

    function resizeColumn(key, delta) {
        var current = columnWidth(key)
        if (key === "note") {
            var maxDelta = endColumnWidth - minimumTimestampColumnWidth
            var minDelta = 100 - current
            var noteDelta = Math.max(minDelta, Math.min(delta, maxDelta))
            customNoteColumnWidth = current + noteDelta
            customEndColumnWidth = endColumnWidth - noteDelta
            return
        }
        var availableGrowth = key === "note" ? 0 : Math.max(0, noteColumnWidth - 100)
        var next = Math.max(columnMinimum(key), Math.min(current + delta, current + availableGrowth))
        if (key === "date") customDateColumnWidth = next
        else if (key === "task") customTaskColumnWidth = next
        else if (key === "type") customTypeColumnWidth = next
        else if (key === "duration") customDurationColumnWidth = next
        else if (key === "start") customStartColumnWidth = next
        else if (key === "end") customEndColumnWidth = next
        else customNoteColumnWidth = next
    }

    readonly property var historyTypeValues: ["", "checklist", "countdown", "stopwatch"]
    readonly property var historyTypeTitles: [
        t("history.filter_all_types"),
        t("history.type.checklist"),
        t("history.type.countdown"),
        t("history.type.stopwatch")
    ]

    RowLayout {
        Layout.fillWidth: true
        spacing: ui.padSm
        FormTextField {
            id: historySearch
            Layout.fillWidth: true
            placeholderText: t("history.search")
            text: app.historyQuery
            onTextChanged: app.setHistoryQuery(text)
            background: Rectangle {
                radius: ui.radius / 2
                color: historyTheme.paneBg
                border.width: 2
                border.color: historyTheme.accent
            }
        }
        FormButton {
            Layout.preferredWidth: 32
            text: "×"
            onClicked: app.setHistoryQuery("")
        }
        FormButton {
            id: fromButton
            Layout.preferredWidth: 150
            text: app.historyFrom.length > 0 ? app.historyFrom : t("history.from")
            onClicked: fromPopup.open()
        }
        FormButton {
            Layout.preferredWidth: 28
            text: "×"
            enabled: app.historyFrom.length > 0
            onClicked: app.setHistoryFrom("")
        }
        FormButton {
            id: toButton
            Layout.preferredWidth: 150
            text: app.historyTo.length > 0 ? app.historyTo : t("history.to")
            onClicked: toPopup.open()
        }
        FormButton {
            Layout.preferredWidth: 28
            text: "×"
            enabled: app.historyTo.length > 0
            onClicked: app.setHistoryTo("")
        }
        FormComboBox {
            id: historyTypeFilter
            Layout.preferredWidth: 150
            model: dialog.historyTypeTitles
            function syncTypeFilter() {
                var index = dialog.historyTypeValues.indexOf(app.historyTypeFilter)
                currentIndex = index >= 0 ? index : 0
            }
            Component.onCompleted: syncTypeFilter()
            Connections {
                target: app
                function onHistoryDialogChanged() { historyTypeFilter.syncTypeFilter() }
            }
            onActivated: app.setHistoryTypeFilter(dialog.historyTypeValues[currentIndex])
        }
        FormButton {
            text: t("history.reset_filters")
            enabled: app.historyQuery.length > 0
                     || app.historyFrom.length > 0
                     || app.historyTo.length > 0
                     || app.historyTypeFilter.length > 0
            onClicked: app.clearHistoryFilters()
        }
        FormButton {
            text: t("history.copy")
            enabled: dialog.selectedCompletionIds.length > 0 || historyView.currentIndex >= 0
            onClicked: dialog.copySelection()
        }
        FormButton {
            text: t("history.export")
            onClicked: {
                if (typeof windowBridge === "undefined" || !windowBridge)
                    return
                var path = windowBridge.chooseSaveFile(t("history.export"), "tiqo-export.csv")
                if (path.length > 0)
                    app.exportHistory(path, dialog.selectedCompletionIds)
            }
        }
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: ui.padSm
        FormLabel { text: t("history.duration_readonly") }
        Item { Layout.fillWidth: true }
        FormButton {
            text: t("action.close")
            onClicked: dialog.close()
        }
    }

    ColumnLayout {
        Layout.fillWidth: true
        spacing: 2
        FormLabel {
            text: app.historySummary
            Layout.fillWidth: true
            elide: Text.ElideRight
        }
        FormLabel {
            text: app.historyDaySummary
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            opacity: 0.8
        }
        FormLabel {
            text: app.historyTypeSummary
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            opacity: 0.8
        }
        FormLabel {
            visible: app.historyFilterSummary.length > 0
            text: app.historyFilterSummary
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: historyTheme.accent
        }
    }

    Row {
        id: tableHeader
        Layout.fillWidth: true
        width: dialog.dataTableWidth
        height: ui.controlHeight

        Rectangle {
            width: dialog.dateColumnWidth
            height: tableHeader.height
            color: historyTheme.chipBg
            border.color: historyTheme.border
            Text { anchors.fill: parent; text: t("history.column_date") + "  " + dialog.sortIndicator("date"); color: historyTheme.text; leftPadding: 6; rightPadding: 6; verticalAlignment: Text.AlignVCenter; clip: true; elide: Text.ElideRight; font.bold: true }
            MouseArea { anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: dialog.sortColumn("date") }
            MouseArea { width: 7; anchors.right: parent.right; anchors.top: parent.top; anchors.bottom: parent.bottom; z: 2; cursorShape: Qt.SizeHorCursor; property real lastX: 0; onPressed: function(mouse) { lastX = mouse.x }; onPositionChanged: function(mouse) { if (pressed) { dialog.resizeColumn("date", mouse.x - lastX); lastX = mouse.x } } }
        }
        Rectangle {
            width: dialog.taskColumnWidth
            height: tableHeader.height
            color: historyTheme.chipBg
            border.color: historyTheme.border
            Text { anchors.fill: parent; text: t("history.column_task") + "  " + dialog.sortIndicator("task"); color: historyTheme.text; leftPadding: 6; rightPadding: 6; verticalAlignment: Text.AlignVCenter; clip: true; elide: Text.ElideRight; font.bold: true }
            MouseArea { anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: dialog.sortColumn("task") }
            MouseArea { width: 7; anchors.right: parent.right; anchors.top: parent.top; anchors.bottom: parent.bottom; z: 2; cursorShape: Qt.SizeHorCursor; property real lastX: 0; onPressed: function(mouse) { lastX = mouse.x }; onPositionChanged: function(mouse) { if (pressed) { dialog.resizeColumn("task", mouse.x - lastX); lastX = mouse.x } } }
        }
        Rectangle {
            width: dialog.typeColumnWidth
            height: tableHeader.height
            color: historyTheme.chipBg
            border.color: historyTheme.border
            Text { anchors.fill: parent; text: t("history.column_type") + "  " + dialog.sortIndicator("type"); color: historyTheme.text; leftPadding: 6; rightPadding: 6; verticalAlignment: Text.AlignVCenter; clip: true; elide: Text.ElideRight; font.bold: true }
            MouseArea { anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: dialog.sortColumn("type") }
            MouseArea { width: 7; anchors.right: parent.right; anchors.top: parent.top; anchors.bottom: parent.bottom; z: 2; cursorShape: Qt.SizeHorCursor; property real lastX: 0; onPressed: function(mouse) { lastX = mouse.x }; onPositionChanged: function(mouse) { if (pressed) { dialog.resizeColumn("type", mouse.x - lastX); lastX = mouse.x } } }
        }
        Rectangle {
            width: dialog.durationColumnWidth
            height: tableHeader.height
            color: historyTheme.chipBg
            border.color: historyTheme.border
            Text { anchors.fill: parent; text: t("history.column_duration") + "  " + dialog.sortIndicator("duration"); color: historyTheme.text; leftPadding: 6; rightPadding: 6; verticalAlignment: Text.AlignVCenter; clip: true; elide: Text.ElideRight; font.bold: true }
            MouseArea { anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: dialog.sortColumn("duration") }
            MouseArea { width: 7; anchors.right: parent.right; anchors.top: parent.top; anchors.bottom: parent.bottom; z: 2; cursorShape: Qt.SizeHorCursor; property real lastX: 0; onPressed: function(mouse) { lastX = mouse.x }; onPositionChanged: function(mouse) { if (pressed) { dialog.resizeColumn("duration", mouse.x - lastX); lastX = mouse.x } } }
        }
        Rectangle {
            width: dialog.startColumnWidth
            height: tableHeader.height
            color: historyTheme.chipBg
            border.color: historyTheme.border
            Text { anchors.fill: parent; text: t("history.column_start") + "  " + dialog.sortIndicator("start"); color: historyTheme.text; leftPadding: 6; rightPadding: 6; verticalAlignment: Text.AlignVCenter; clip: true; elide: Text.ElideRight; font.bold: true }
            MouseArea { anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: dialog.sortColumn("start") }
            MouseArea { width: 7; anchors.right: parent.right; anchors.top: parent.top; anchors.bottom: parent.bottom; z: 2; cursorShape: Qt.SizeHorCursor; property real lastX: 0; onPressed: function(mouse) { lastX = mouse.x }; onPositionChanged: function(mouse) { if (pressed) { dialog.resizeColumn("start", mouse.x - lastX); lastX = mouse.x } } }
        }
        Rectangle {
            width: dialog.endColumnWidth
            height: tableHeader.height
            color: historyTheme.chipBg
            border.color: historyTheme.border
            Text { anchors.fill: parent; text: t("history.column_end") + "  " + dialog.sortIndicator("end"); color: historyTheme.text; leftPadding: 6; rightPadding: 6; verticalAlignment: Text.AlignVCenter; clip: true; elide: Text.ElideRight; font.bold: true }
            MouseArea { anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: dialog.sortColumn("end") }
            MouseArea { width: 7; anchors.right: parent.right; anchors.top: parent.top; anchors.bottom: parent.bottom; z: 2; cursorShape: Qt.SizeHorCursor; property real lastX: 0; onPressed: function(mouse) { lastX = mouse.x }; onPositionChanged: function(mouse) { if (pressed) { dialog.resizeColumn("end", mouse.x - lastX); lastX = mouse.x } } }
        }
        Rectangle {
            width: dialog.noteColumnWidth
            height: tableHeader.height
            color: historyTheme.chipBg
            border.color: historyTheme.border
            Text { anchors.fill: parent; text: t("history.column_note") + "  " + dialog.sortIndicator("note"); color: historyTheme.text; leftPadding: 6; rightPadding: 6; verticalAlignment: Text.AlignVCenter; clip: true; elide: Text.ElideRight; font.bold: true }
            MouseArea { anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: dialog.sortColumn("note") }
            MouseArea { width: 7; anchors.right: parent.right; anchors.top: parent.top; anchors.bottom: parent.bottom; z: 2; cursorShape: Qt.SizeHorCursor; property real lastX: 0; onPressed: function(mouse) { lastX = mouse.x }; onPositionChanged: function(mouse) { if (pressed) { dialog.resizeColumn("note", mouse.x - lastX); lastX = mouse.x } } }
        }
    }

    ListView {
        id: historyView
        Layout.fillWidth: true
        Layout.fillHeight: true
        clip: true
        spacing: 0
        focus: true
        activeFocusOnTab: true
        model: app.history
        Keys.onPressed: function(event) {
            if ((event.modifiers & Qt.ControlModifier) && event.key === Qt.Key_C) {
                dialog.copySelection()
                event.accepted = true
            } else if ((event.modifiers & Qt.ControlModifier) && event.key === Qt.Key_A) {
                var allIds = []
                for (var row = 0; row < count; row++) {
                    var idAt = app.historyIdAt(row)
                    if (idAt > 0)
                        allIds.push(idAt)
                }
                dialog.selectedCompletionIds = allIds
                event.accepted = true
            } else if (event.key === Qt.Key_Escape) {
                dialog.clearSelection()
                event.accepted = true
            } else if (event.key === Qt.Key_F2
                       || event.key === Qt.Key_Return
                       || event.key === Qt.Key_Enter) {
                if (currentItem)
                    app.openHistoryNoteDialog(currentItem.completionId)
                event.accepted = true
            }
        }
        onCurrentIndexChanged: {
            if (!dialog.updatingCurrentIndex && activeFocus && currentItem)
                dialog.selectRow(currentItem.completionId, currentIndex, 0)
        }
        delegate: Item {
            id: historyCard
            required property int index
            required property int completionId
            required property string title
            required property string completionKind
            required property string completionDate
            required property string completedAt
            required property string startedAt
            required property string endedAt
            required property string duration
            required property string note
            required property bool isTimed
            required property bool isDayStart
            readonly property bool selected: dialog.isSelected(completionId)
            width: dialog.tableWidth
            height: ui.controlHeight + ui.padSm

            Rectangle {
                width: dialog.dataTableWidth
                height: parent.height
                color: selected ? Qt.rgba(historyTheme.accent.r, historyTheme.accent.g, historyTheme.accent.b, 0.16) : historyTheme.paneBg
                border.color: selected || isDayStart ? historyTheme.accent : historyTheme.border
                border.width: selected || isDayStart ? 2 : 1
            }

            Rectangle {
                x: 0; y: 0; width: dialog.dateColumnWidth; height: parent.height
                color: selected ? dialog.selectionBackground : "transparent"; border.color: historyTheme.border
                Text { anchors.fill: parent; text: completionDate; color: historyTheme.text; leftPadding: 6; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight; font.bold: isDayStart }
                MouseArea { anchors.fill: parent; onClicked: function(mouse) { dialog.selectRow(completionId, index, mouse.modifiers) }; cursorShape: Qt.PointingHandCursor }
            }
            Rectangle {
                x: dialog.dateColumnWidth; y: 0; width: dialog.taskColumnWidth; height: parent.height
                color: selected ? dialog.selectionBackground : "transparent"; border.color: historyTheme.border
                Text { anchors.fill: parent; text: title; color: historyTheme.text; leftPadding: 6; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight; font.bold: true }
                MouseArea { anchors.fill: parent; onClicked: function(mouse) { dialog.selectRow(completionId, index, mouse.modifiers) }; cursorShape: Qt.PointingHandCursor }
            }
            Rectangle {
                x: dialog.dateColumnWidth + dialog.taskColumnWidth; y: 0; width: dialog.typeColumnWidth; height: parent.height
                color: selected ? dialog.selectionBackground : "transparent"; border.color: historyTheme.border
                Text { anchors.fill: parent; text: completionKind; color: historyTheme.muted; leftPadding: 6; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
                MouseArea { anchors.fill: parent; onClicked: function(mouse) { dialog.selectRow(completionId, index, mouse.modifiers) }; cursorShape: Qt.PointingHandCursor }
            }
            Rectangle {
                x: dialog.dateColumnWidth + dialog.taskColumnWidth + dialog.typeColumnWidth; y: 0; width: dialog.durationColumnWidth; height: parent.height
                color: selected ? dialog.selectionBackground : "transparent"; border.color: historyTheme.border
                Text { anchors.fill: parent; text: duration; color: historyTheme.muted; leftPadding: 6; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
                MouseArea { anchors.fill: parent; onClicked: function(mouse) { dialog.selectRow(completionId, index, mouse.modifiers) }; cursorShape: Qt.PointingHandCursor }
            }

            FormTextField {
                id: startField
                x: dialog.dateColumnWidth + dialog.taskColumnWidth + dialog.typeColumnWidth + dialog.durationColumnWidth
                y: 0; width: dialog.startColumnWidth; height: parent.height
                visible: isTimed
                text: startedAt
                placeholderText: t("history.start")
                onActiveFocusChanged: if (activeFocus) dialog.selectRow(completionId, index, 0)
                background: Rectangle { color: selected ? dialog.selectionBackground : historyTheme.paneBg; border.color: historyTheme.border; border.width: 1 }
            }
            Rectangle {
                visible: !isTimed
                x: dialog.dateColumnWidth + dialog.taskColumnWidth + dialog.typeColumnWidth + dialog.durationColumnWidth
                y: 0; width: dialog.startColumnWidth; height: parent.height
                color: selected ? dialog.selectionBackground : "transparent"; border.color: historyTheme.border
            }
            FormTextField {
                id: endField
                x: dialog.dateColumnWidth + dialog.taskColumnWidth + dialog.typeColumnWidth + dialog.durationColumnWidth + dialog.startColumnWidth
                y: 0; width: dialog.endColumnWidth; height: parent.height
                text: endedAt
                placeholderText: t("history.end")
                onActiveFocusChanged: if (activeFocus) dialog.selectRow(completionId, index, 0)
                background: Rectangle { color: selected ? dialog.selectionBackground : historyTheme.paneBg; border.color: historyTheme.border; border.width: 1 }
            }
            Item {
                id: noteCell
                x: dialog.dateColumnWidth + dialog.taskColumnWidth + dialog.typeColumnWidth + dialog.durationColumnWidth + dialog.startColumnWidth + dialog.endColumnWidth
                y: 0; width: dialog.noteColumnWidth; height: parent.height

                Rectangle {
                    anchors.fill: parent
                    color: selected ? dialog.selectionBackground : historyTheme.paneBg
                    border.color: noteMouse.containsMouse ? historyTheme.accent : historyTheme.border
                    border.width: noteMouse.containsMouse ? 2 : 1
                }
                Text {
                    anchors.fill: parent
                    leftPadding: 6
                    rightPadding: 6
                    text: note.length > 0 ? note : t("history.note_empty")
                    color: note.length > 0 ? historyTheme.text : historyTheme.muted
                    elide: Text.ElideRight
                    clip: true
                    verticalAlignment: Text.AlignVCenter
                }
                MouseArea {
                    id: noteMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: app.openHistoryNoteDialog(completionId)
                    onPressed: function(mouse) { dialog.selectRow(completionId, index, mouse.modifiers) }
                    ToolTip.visible: containsMouse && note.length > 0
                    ToolTip.text: note
                    ToolTip.delay: 500
                }
            }
            // Actions live beside the data grid rather than becoming table columns.
            Item {
                x: dialog.dataTableWidth
                y: 0
                width: dialog.actionAreaWidth
                height: parent.height

                Row {
                    anchors.left: parent.left
                    anchors.leftMargin: ui.padSm
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: ui.padSm

                    FormButton {
                        id: saveHistoryButton
                        width: Math.max(dialog.actionColumnWidth, implicitWidth)
                        text: t("action.save")
                        highlighted: false
                        onClicked: app.updateHistory(completionId, startField.text, endField.text, note)
                    }
                    FormButton {
                        id: deleteHistoryButton
                        width: Math.max(dialog.actionColumnWidth, implicitWidth)
                        text: t("action.delete")
                        highlighted: false
                        onClicked: app.deleteHistory(completionId)
                    }
                }
            }
            Rectangle {
                x: 0
                y: 0
                width: dialog.dataTableWidth
                height: parent.height
                color: "transparent"
                border.color: selected ? historyTheme.accent : "transparent"
                border.width: selected ? 2 : 0
                z: 10
            }
        }
    }

    Popup {
        id: fromPopup
        modal: true
        focus: true
        padding: 0
        contentItem: DateCalendar {
            selectedDate: dialog.dateFromText(app.historyFrom)
            onDateClicked: {
                app.setHistoryFrom(dialog.formatDate(date))
                fromPopup.close()
            }
        }
    }

    Popup {
        id: toPopup
        modal: true
        focus: true
        padding: 0
        contentItem: DateCalendar {
            selectedDate: dialog.dateFromText(app.historyTo)
            onDateClicked: {
                app.setHistoryTo(dialog.formatDate(date))
                toPopup.close()
            }
        }
    }
}
