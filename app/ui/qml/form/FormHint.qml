import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "../" as Root

Label {
    Layout.fillWidth: true
    wrapMode: Text.WordWrap
    color: hintTheme.muted
    font.pixelSize: 12

    Root.Theme { id: hintTheme }
}
