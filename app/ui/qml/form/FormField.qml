import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Compose: <FormField label="…"> <FormTextField/> </FormField>
ColumnLayout {
    id: root
    property string label: ""
    property string hint: ""

    spacing: Math.max(2, ui.padSm / 2)
    Layout.fillWidth: true

    FormLabel {
        text: root.label
        visible: root.label.length > 0
        Layout.fillWidth: true
    }

    FormHint {
        text: root.hint
        visible: root.hint.length > 0
    }

    // Nested controls are additional ColumnLayout children (React children).
}
