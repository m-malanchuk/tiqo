pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts

import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PlasmaComponents
import org.kde.plasma.plasmoid

MouseArea {
    id: root

    required property var plasmoidItem

    property bool wasExpanded: false

    readonly property bool showIcon: Plasmoid.configuration.showTrayIcon
    readonly property bool showCount: Plasmoid.configuration.showTrayCount
    readonly property bool showTimer: Plasmoid.configuration.showTrayTimer
    readonly property bool showToday: Plasmoid.configuration.showTrayTodayProgress

    // Exact size from settings — do not shrink to panel height.
    readonly property int iconPx: Math.max(8, Number(Plasmoid.configuration.trayIconSize) || 16)
    readonly property int fontPt: Number(Plasmoid.configuration.trayFontPointSize) || 0
    readonly property int fontPixel: {
        if (fontPt > 0)
            return Math.round(fontPt * 1.3);
        return Math.round(Kirigami.Theme.smallFont.pixelSize);
    }

    readonly property int contentW: {
        let w = 0;
        if (showIcon)
            w += iconPx;
        if (showTimer)
            w += timerLabel.implicitWidth;
        if (showCount)
            w += countLabel.implicitWidth;
        if (showToday)
            w += todayLabel.implicitWidth;
        let parts = (showIcon ? 1 : 0) + (showTimer ? 1 : 0)
                  + (showCount ? 1 : 0) + (showToday ? 1 : 0);
        if (parts > 1)
            w += 2 * (parts - 1);
        return Math.max(w, 1);
    }

    // Panel thickness vertically. Width locked to content so the panel cell
    // does not become a tall square with empty space beside the neighbour.
    Layout.fillHeight: true
    Layout.minimumHeight: 0
    Layout.preferredHeight: 0
    Layout.maximumHeight: Infinity
    Layout.minimumWidth: contentW
    Layout.preferredWidth: contentW
    Layout.maximumWidth: contentW
    Layout.margins: 0

    implicitWidth: contentW
    implicitHeight: Math.max(iconPx, fontPixel)

    hoverEnabled: true
    acceptedButtons: Qt.LeftButton

    onPressed: wasExpanded = plasmoidItem.expanded
    onClicked: plasmoidItem.expanded = !wasExpanded

    Row {
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        height: Math.max(root.iconPx, root.fontPixel)
        spacing: 2

        // Slot is exactly iconPx. Breeze chronometer has ~14% empty margin in the
        // SVG; paint larger + clip so the face fills the slot. Slot size stays
        // iconPx (configured) — we do not shrink the control, only crop theme padding.
        Item {
            visible: root.showIcon
            width: root.iconPx
            height: root.iconPx
            anchors.verticalCenter: parent.verticalCenter
            clip: true

            Kirigami.Icon {
                anchors.centerIn: parent
                width: Math.round(root.iconPx * 1.4)
                height: Math.round(root.iconPx * 1.4)
                source: "chronometer"
                active: root.containsMouse
            }
        }

        PlasmaComponents.Label {
            id: timerLabel
            visible: root.showTimer
            anchors.verticalCenter: parent.verticalCenter
            verticalAlignment: Text.AlignVCenter
            text: plasmoidItem.trayClockText
            font.pointSize: root.fontPt > 0 ? root.fontPt : Kirigami.Theme.smallFont.pointSize
            width: Math.min(implicitWidth, Kirigami.Units.gridUnit * 8)
            elide: Text.ElideRight
            leftPadding: 0
            rightPadding: 0
        }

        PlasmaComponents.Label {
            id: countLabel
            visible: root.showCount
            anchors.verticalCenter: parent.verticalCenter
            verticalAlignment: Text.AlignVCenter
            text: plasmoidItem.trayCountText
            font.pointSize: root.fontPt > 0 ? root.fontPt : Kirigami.Theme.smallFont.pointSize
            leftPadding: 0
            rightPadding: 0
        }

        PlasmaComponents.Label {
            id: todayLabel
            visible: root.showToday
            anchors.verticalCenter: parent.verticalCenter
            verticalAlignment: Text.AlignVCenter
            text: plasmoidItem.trayTodayText
            font.pointSize: root.fontPt > 0 ? root.fontPt : Kirigami.Theme.smallFont.pointSize
            leftPadding: 0
            rightPadding: 0
        }
    }
}
