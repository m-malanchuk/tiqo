pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts

import org.kde.kirigami as Kirigami
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.plasmoid
import org.kde.plasma.workspace.dbus as DBus

PlasmoidItem {
    id: root

    readonly property string serviceName: "org.tiqo.App"
    readonly property string objectPath: "/org/tiqo/App"
    readonly property string ifaceName: "org.tiqo.App1"

    // System list ids (app.domain.models).
    readonly property int listFavoritesId: 1
    readonly property int listInWorkId: 3

    property bool appOnline: serviceWatcher.registered
    property string lastError: ""

    property int todayDone: 0
    property int todayTotal: 0

    ListModel { id: workModel }
    ListModel { id: taskModel }
    ListModel { id: listModel }

    readonly property int visibleCount: workModel.count
    readonly property int taskCount: taskModel.count

    readonly property int selectedListId: {
        const v = Number(Plasmoid.configuration.selectedListId);
        return v > 0 ? v : listInWorkId;
    }

    readonly property int trackedTaskId: Plasmoid.configuration.trackedTaskId

    readonly property var trackedItem: {
        const preferred = Number(trackedTaskId);
        if (preferred) {
            for (let i = 0; i < workModel.count; i++) {
                const row = workModel.get(i);
                if (Number(row.task_id) === preferred)
                    return row;
            }
        }
        return workModel.count > 0 ? workModel.get(0) : null;
    }

    readonly property string trayClockText: trackedItem ? String(trackedItem.clock) : "--:--"
    readonly property string trayCountText: "[" + visibleCount + "]"
    // Favorites stay in the list → only today's done counter (0, 1, 2…).
    // Other lists: done/total. In-work [N] is a separate tray toggle (off by default).
    readonly property string trayTodayText: {
        if (Number(selectedListId) === listFavoritesId)
            return "[" + todayDone + "]";
        return "[" + todayDone + "/" + todayTotal + "]";
    }
    readonly property string trayTitleText: trackedItem ? String(trackedItem.title) : ""

    switchWidth: Kirigami.Units.gridUnit * 12
    switchHeight: Kirigami.Units.gridUnit * 8

    toolTipMainText: "tiqo"
    toolTipSubText: {
        if (!appOnline)
            return i18n("tiqo is not running");
        const bits = [];
        if (Plasmoid.configuration.showTrayTodayProgress)
            bits.push(trayTodayText);
        if (trackedItem)
            bits.push(trayTitleText + " · " + trayClockText);
        else if (visibleCount > 0)
            bits.push(trayCountText + " · " + trayClockText);
        else
            bits.push(i18n("Nothing in work"));
        return bits.join(" · ");
    }

    Plasmoid.icon: "chronometer"
    Plasmoid.status: {
        if (!appOnline)
            return PlasmaCore.Types.PassiveStatus;
        if (trackedItem && trackedItem.state === "running")
            return PlasmaCore.Types.ActiveStatus;
        if (visibleCount > 0 || todayTotal > 0)
            return PlasmaCore.Types.ActiveStatus;
        return PlasmaCore.Types.PassiveStatus;
    }

    preferredRepresentation: compactRepresentation

    compactRepresentation: CompactRepresentation {
        plasmoidItem: root
    }

    fullRepresentation: FullRepresentation {
        id: fullRep
        plasmoidItem: root
        taskModel: taskModel
        listModel: listModel
        Layout.minimumWidth: Kirigami.Units.gridUnit * 16
        Layout.preferredWidth: Kirigami.Units.gridUnit * 20
        Layout.maximumWidth: Kirigami.Units.gridUnit * 28
        Layout.minimumHeight: fullRep.minimumPopupHeight
        Layout.preferredHeight: fullRep.preferredPopupHeight
        Layout.maximumHeight: fullRep.maximumPopupHeight
    }

    DBus.DBusServiceWatcher {
        id: serviceWatcher
        busType: DBus.BusType.Session
        watchedService: root.serviceName
        onRegisteredChanged: {
            if (registered) {
                root.refreshAll();
                // Config / first D-Bus round-trip can lag; pull stats again shortly.
                statsRetry.restart();
            } else {
                workModel.clear();
                taskModel.clear();
                listModel.clear();
                root.todayDone = 0;
                root.todayTotal = 0;
                root.lastError = "";
            }
        }
    }

    Timer {
        id: pollTimer
        interval: 1000
        repeat: true
        running: root.appOnline
        onTriggered: root.refreshAll()
    }

    Timer {
        id: statsRetry
        interval: 250
        repeat: false
        onTriggered: {
            if (root.appOnline)
                root.refreshTodayStats();
        }
    }

    // KConfig may resolve after Component.onCompleted — refresh when it settles.
    onSelectedListIdChanged: {
        if (!appOnline)
            return;
        refreshTasks();
        refreshTodayStats();
    }

    Component.onCompleted: {
        if (appOnline) {
            refreshAll();
            statsRetry.restart();
        }
    }

    function callTiqo(member, args, signature, onOk, onErr) {
        const pending = DBus.SessionBus.asyncCall({
            service: serviceName,
            path: objectPath,
            iface: ifaceName,
            member: member,
            arguments: args || [],
            signature: signature || "",
        });
        pending.finished.connect(() => {
            if (pending.isError) {
                const msg = pending.error.message || pending.error.name || "D-Bus error";
                console.warn("tiqo D-Bus", member, msg);
                if (onErr)
                    onErr(msg);
                else
                    root.lastError = msg;
            } else if (onOk) {
                onOk(pending.value, pending.values);
            }
            pending.destroy();
        });
    }

    function apiTooOldError(msg) {
        const m = String(msg || "");
        if (m.indexOf("ListLists") >= 0 || m.indexOf("ListTasks") >= 0 || m.indexOf("TodayStats") >= 0
            || m.indexOf("Unknown method") >= 0 || m.indexOf("No such method") >= 0) {
            root.lastError = i18n("tiqo is too old for this widget — restart the app (need D-Bus API v5).");
            return true;
        }
        return false;
    }

    function normalizeTaskRow(row) {
        return {
            task_id: Number(row.task_id),
            title: String(row.title || ""),
            state: String(row.state || ""),
            clock: String(row.clock || ""),
            is_countdown: !!row.is_countdown,
            progress: (row.progress === null || row.progress === undefined) ? -1 : Number(row.progress),
            can_start: !!row.can_start,
            can_pause: !!row.can_pause,
            can_stop: !!row.can_stop,
            depth: Number(row.depth) || 0,
            blocked_by_descendant: !!row.blocked_by_descendant,
            kind: String(row.kind || "timed"),
            is_completed: !!row.is_completed,
            can_complete: !!row.can_complete,
        };
    }

    function syncListModel(model, rows, filterBlocked) {
        const visible = [];
        for (let i = 0; i < rows.length; i++) {
            const row = rows[i];
            if (filterBlocked && row && row.blocked_by_descendant)
                continue;
            visible.push(normalizeTaskRow(row));
        }

        let sameIds = model.count === visible.length;
        if (sameIds) {
            for (let i = 0; i < visible.length; i++) {
                if (Number(model.get(i).task_id) !== visible[i].task_id) {
                    sameIds = false;
                    break;
                }
            }
        }

        if (!sameIds) {
            model.clear();
            for (let i = 0; i < visible.length; i++)
                model.append(visible[i]);
            return;
        }

        for (let i = 0; i < visible.length; i++) {
            const row = visible[i];
            model.setProperty(i, "title", row.title);
            model.setProperty(i, "state", row.state);
            model.setProperty(i, "clock", row.clock);
            model.setProperty(i, "is_countdown", row.is_countdown);
            model.setProperty(i, "progress", row.progress);
            model.setProperty(i, "can_start", row.can_start);
            model.setProperty(i, "can_pause", row.can_pause);
            model.setProperty(i, "can_stop", row.can_stop);
            model.setProperty(i, "depth", row.depth);
            model.setProperty(i, "blocked_by_descendant", row.blocked_by_descendant);
            model.setProperty(i, "kind", row.kind);
            model.setProperty(i, "is_completed", row.is_completed);
            model.setProperty(i, "can_complete", row.can_complete);
        }
    }

    function syncLists(parsed) {
        const rows = Array.isArray(parsed) ? parsed : [];
        let same = listModel.count === rows.length;
        if (same) {
            for (let i = 0; i < rows.length; i++) {
                if (Number(listModel.get(i).list_id) !== Number(rows[i].list_id)) {
                    same = false;
                    break;
                }
            }
        }
        if (!same) {
            listModel.clear();
            for (let i = 0; i < rows.length; i++) {
                listModel.append({
                    list_id: Number(rows[i].list_id),
                    name: String(rows[i].name || ""),
                    icon: String(rows[i].icon || ""),
                    is_system: !!rows[i].is_system,
                });
            }
        } else {
            for (let i = 0; i < rows.length; i++) {
                listModel.setProperty(i, "name", String(rows[i].name || ""));
                listModel.setProperty(i, "icon", String(rows[i].icon || ""));
            }
        }
        // First fill / list set change: re-pull progress for the resolved
        // selection (avoids sticky [0/0] until the user picks another category).
        if (!same)
            refreshTodayStats();
    }

    function refreshAll() {
        if (!appOnline)
            return;
        refreshWork();
        refreshLists();
        refreshTasks();
        refreshTodayStats();
    }

    function refreshWork() {
        callTiqo("ListWork", [], "", (value) => {
            try {
                const parsed = JSON.parse(typeof value === "string" ? value : String(value));
                syncListModel(workModel, Array.isArray(parsed) ? parsed : [], true);
                root.lastError = "";
            } catch (e) {
                root.lastError = String(e);
            }
        });
    }

    function refreshLists() {
        callTiqo("ListLists", [], "", (value) => {
            try {
                const parsed = JSON.parse(typeof value === "string" ? value : String(value));
                syncLists(parsed);
                if (root.lastError.indexOf("D-Bus API v2") >= 0)
                    root.lastError = "";
            } catch (e) {
                console.warn("tiqo ListLists", e);
            }
        }, (msg) => { apiTooOldError(msg); });
    }

    function refreshTasks() {
        const lid = selectedListId;
        callTiqo("ListTasks", [new DBus.int32(lid)], "(i)", (value) => {
            try {
                const parsed = JSON.parse(typeof value === "string" ? value : String(value));
                const filterBlocked = lid === listInWorkId;
                syncListModel(taskModel, Array.isArray(parsed) ? parsed : [], filterBlocked);
                if (root.lastError.indexOf("D-Bus API v2") >= 0)
                    root.lastError = "";
                else
                    root.lastError = "";
            } catch (e) {
                root.lastError = String(e);
            }
        }, (msg) => { apiTooOldError(msg); });
    }

    function refreshTodayStats() {
        const lid = selectedListId;
        callTiqo("TodayStats", [new DBus.int32(lid)], "(i)", (value) => {
            try {
                const parsed = JSON.parse(typeof value === "string" ? value : String(value));
                root.todayDone = Number(parsed.done) || 0;
                root.todayTotal = Number(parsed.total) || 0;
            } catch (e) {
                console.warn("tiqo TodayStats", e);
            }
        }, (msg) => { apiTooOldError(msg); });
    }

    function setSelectedListId(listId) {
        Plasmoid.configuration.selectedListId = Number(listId);
        refreshTasks();
        refreshTodayStats();
    }

    function resumeTask(taskId) {
        callTiqo("Resume", [new DBus.int32(taskId)], "(i)", (value) => {
            if (typeof value === "string" && value.indexOf("error:") === 0)
                root.lastError = value;
            root.refreshAll();
        });
    }

    function pauseTask(taskId) {
        callTiqo("Pause", [new DBus.int32(taskId)], "(i)", (value) => {
            if (typeof value === "string" && value.indexOf("error:") === 0)
                root.lastError = value;
            root.refreshAll();
        });
    }

    function stopTask(taskId) {
        callTiqo("Stop", [new DBus.int32(taskId)], "(i)", (value) => {
            if (typeof value === "string" && value.indexOf("error:") === 0)
                root.lastError = value;
            root.refreshAll();
        });
    }

    function completeChecklist(taskId) {
        callTiqo("CompleteChecklist", [new DBus.int32(taskId)], "(i)", (value) => {
            if (typeof value === "string" && value.indexOf("error:") === 0)
                root.lastError = value;
            root.refreshAll();
        }, (msg) => { apiTooOldError(msg); });
    }

    function showWindow() {
        callTiqo("ShowWindow", [], "", null);
    }
}
