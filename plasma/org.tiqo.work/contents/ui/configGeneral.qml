pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts

import org.kde.kirigami as Kirigami
import org.kde.kcmutils as KCMUtils
import org.kde.plasma.workspace.dbus as DBus

KCMUtils.SimpleKCM {
    id: root

    property alias cfg_showTrayIcon: showTrayIcon.checked
    property alias cfg_showTrayCount: showTrayCount.checked
    property alias cfg_showTrayTimer: showTrayTimer.checked
    property alias cfg_showTrayTodayProgress: showTrayTodayProgress.checked
    property alias cfg_trayIconSize: trayIconSize.value
    property alias cfg_trayFontPointSize: trayFontPointSize.value
    property int cfg_trackedTaskId: 0
    property int cfg_selectedListId: 3

    ListModel {
        id: taskChoices
    }

    function rebuildTaskChoices(rows) {
        taskChoices.clear();
        taskChoices.append({
            task_id: 0,
            label: i18n("Automatic (first in work)"),
        });
        for (let i = 0; i < rows.length; i++) {
            const row = rows[i];
            if (row && row.blocked_by_descendant)
                continue;
            const tid = Number(row.task_id);
            const title = String(row.title || ("#" + tid));
            const clock = String(row.clock || "");
            taskChoices.append({
                task_id: tid,
                label: title + (clock ? (" · " + clock) : ""),
            });
        }
        let idx = 0;
        for (let i = 0; i < taskChoices.count; i++) {
            if (Number(taskChoices.get(i).task_id) === Number(cfg_trackedTaskId)) {
                idx = i;
                break;
            }
        }
        trackedCombo.currentIndex = idx;
    }

    function refreshTasksFromApp() {
        const pending = DBus.SessionBus.asyncCall({
            service: "org.tiqo.App",
            path: "/org/tiqo/App",
            iface: "org.tiqo.App1",
            member: "ListWork",
            arguments: [],
            signature: "",
        });
        pending.finished.connect(() => {
            if (pending.isError) {
                rebuildTaskChoices([]);
            } else {
                try {
                    const raw = typeof pending.value === "string" ? pending.value : String(pending.value);
                    const parsed = JSON.parse(raw);
                    rebuildTaskChoices(Array.isArray(parsed) ? parsed : []);
                } catch (e) {
                    rebuildTaskChoices([]);
                }
            }
            pending.destroy();
        });
    }

    Component.onCompleted: refreshTasksFromApp()

    // Column layout — FormLayout wideMode stretched the combo across the dialog.
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Kirigami.Units.smallSpacing
        spacing: Kirigami.Units.largeSpacing

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing

            Kirigami.Heading {
                level: 4
                text: i18n("Compact representation")
                Layout.fillWidth: true
            }

            QQC2.CheckBox {
                id: showTrayIcon
                text: i18n("Show icon")
            }

            QQC2.CheckBox {
                id: showTrayTimer
                text: i18n("Show timer of the tracked task")
            }

            QQC2.CheckBox {
                id: showTrayCount
                text: i18n("Show in-work count [N] on the tray")
            }

            QQC2.CheckBox {
                id: showTrayTodayProgress
                text: i18n("Show list progress ([done/total]; Favorites: done counter only)")
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing

                QQC2.Label {
                    text: i18n("Tracked task:")
                    Layout.alignment: Qt.AlignVCenter
                }

                QQC2.ComboBox {
                    id: trackedCombo
                    model: taskChoices
                    textRole: "label"
                    Layout.preferredWidth: Kirigami.Units.gridUnit * 14
                    Layout.maximumWidth: Kirigami.Units.gridUnit * 14
                    Layout.fillWidth: false
                    onActivated: {
                        if (currentIndex >= 0 && currentIndex < taskChoices.count)
                            cfg_trackedTaskId = Number(taskChoices.get(currentIndex).task_id);
                    }
                }

                QQC2.Button {
                    text: i18n("Refresh")
                    icon.name: "view-refresh"
                    display: QQC2.AbstractButton.TextBesideIcon
                    onClicked: refreshTasksFromApp()
                }

                Item { Layout.fillWidth: true }
            }

            QQC2.Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                font: Kirigami.Theme.smallFont
                opacity: 0.7
                text: i18n("If the chosen task leaves «In work», the first task is used. Empty roster: timer shows --:--, count shows [0].")
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing

            Kirigami.Heading {
                level: 4
                text: i18n("Appearance")
                Layout.fillWidth: true
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing

                QQC2.Label {
                    text: i18n("Icon size:")
                    Layout.alignment: Qt.AlignVCenter
                }

                QQC2.SpinBox {
                    id: trayIconSize
                    from: 8
                    to: 64
                    stepSize: 2
                    Layout.preferredWidth: Kirigami.Units.gridUnit * 8
                    textFromValue: (value) => value + " px"
                    valueFromText: (text) => parseInt(text, 10)
                }

                Item { Layout.fillWidth: true }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing

                QQC2.Label {
                    text: i18n("Font size:")
                    Layout.alignment: Qt.AlignVCenter
                }

                QQC2.SpinBox {
                    id: trayFontPointSize
                    from: 0
                    to: 24
                    stepSize: 1
                    Layout.preferredWidth: Kirigami.Units.gridUnit * 10
                    textFromValue: (value) => value === 0 ? i18n("Theme default") : (value + " pt")
                    valueFromText: (text) => {
                        const n = parseInt(text, 10);
                        return isNaN(n) ? 0 : n;
                    }
                }

                Item { Layout.fillWidth: true }
            }

            QQC2.Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                font: Kirigami.Theme.smallFont
                opacity: 0.7
                text: i18n("Applies to the compact face on the panel or in the system tray.")
            }
        }

        Item { Layout.fillHeight: true }
    }
}
