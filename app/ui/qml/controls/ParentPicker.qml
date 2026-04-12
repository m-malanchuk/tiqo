import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import form 1.0

// Single parent only (tree).
ColumnLayout {
    id: root
    spacing: ui.padSm
    Layout.fillWidth: true

    readonly property string _lang: typeof i18n !== "undefined" ? i18n.language : "ru"
    function t(key) { var _ = _lang; return i18n.t(key) }

    FormField {
        label: t("field.parent")
        FormComboBox {
            id: parentCombo
            model: app.parentPicker
            textRole: "title"
            valueRole: "taskId"
            onActivated: app.setDraftParentId(currentValue)
            Component.onCompleted: syncParent()
            function syncParent() {
                for (var i = 0; i < count; i++) {
                    if (model.data(model.index(i, 0), 257) === app.draftParentId) {
                        currentIndex = i
                        return
                    }
                }
                currentIndex = 0
            }
            Connections {
                target: app
                function onParentPickerChanged() { parentCombo.syncParent() }
            }
        }
    }
}
