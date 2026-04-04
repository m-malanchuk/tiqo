import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "../" as Root

Label {
    id: root
    property int listId: -1
    readonly property string _lang: typeof i18n !== "undefined" ? i18n.language : "ru"
    function t(key) { var _ = _lang; return i18n.t(key) }

    Layout.alignment: Qt.AlignHCenter
    horizontalAlignment: Text.AlignHCenter
    wrapMode: Text.WordWrap
    color: emptyTheme.muted

    text: {
        var _ = _lang
        if (listId === 2)
            return t("empty.today")
        if (listId === 3)
            return t("empty.in_work")
        return t("empty.generic")
    }

    Root.Theme { id: emptyTheme }
}
