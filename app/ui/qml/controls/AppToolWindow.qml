import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import ".." as Root

// Real top-level window shell for create/edit/start/… (not an overlay Dialog).
Window {
    id: root

    property string titleText: ""
    property int bodyWidth: 520
    default property alias body: column.data

    signal rejected()
    signal opened()

    title: titleText
    width: bodyWidth
    minimumWidth: 360
    minimumHeight: 160
    // Default: content-sized. Callers may override ``height`` (e.g. emoji grid).
    height: Math.min(760, Math.max(minimumHeight, column.implicitHeight + 2 * ui.padMd))
    visible: false
    color: theme.paneBg
    flags: Qt.Window
    // Plain Window has no ``icon`` property (unlike ApplicationWindow).
    // Title-bar mark comes from QApplication.setWindowIcon + hicolor ``tiqo``.

    Root.Theme { id: theme }

    property bool _suppressReject: false

    // Re-evaluate T()/t1()/t2() when the UI language changes.
    readonly property string _lang: typeof i18n !== "undefined" ? i18n.language : "ru"
    function t(key) { var _ = _lang; return i18n.t(key) }
    function t1(key, a) { var _ = _lang; return i18n.t1(key, String(a)) }
    function t2(key, a, b) { var _ = _lang; return i18n.t2(key, String(a), String(b)) }

    function open() {
        // Property-notify signals for dialog fields are shared with the open
        // state.  They can call this method again while the window is already
        // visible; do not re-run `opened()`, or a field would steal focus on
        // every keystroke.
        if (visible)
            return
        visible = true
        raise()
        requestActivate()
        opened()
    }

    function close() {
        _suppressReject = true
        visible = false
        _suppressReject = false
    }

    function reject() {
        _suppressReject = true
        visible = false
        _suppressReject = false
        rejected()
    }

    onClosing: function (close) {
        close.accepted = true
        if (!_suppressReject)
            Qt.callLater(function () { root.rejected() })
    }

    ColumnLayout {
        id: column
        x: ui.padMd
        y: ui.padMd
        width: root.width - 2 * ui.padMd
        // Match the window body so Layout.fillHeight children (emoji grid) get a real viewport.
        height: root.height - 2 * ui.padMd
        spacing: ui.padMd
    }
}
