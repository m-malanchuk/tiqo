import QtQuick

// Color tokens only. Spacing/sizes come from context property ``ui`` (UiMetrics)
// so Settings can change them at runtime without restart.
QtObject {
    id: theme

    readonly property SystemPalette sys: SystemPalette {
        colorGroup: SystemPalette.Active
    }

    readonly property color panelBg: sys.window
    readonly property color paneBg: sys.base
    // Readable on Breeze Dark (raw mid is often near-black)
    readonly property color border: Qt.rgba(sys.windowText.r, sys.windowText.g, sys.windowText.b, 0.35)
    readonly property color text: sys.windowText
    readonly property color muted: Qt.rgba(sys.windowText.r, sys.windowText.g, sys.windowText.b, 0.78)
    readonly property color accent: sys.highlight
    readonly property color accentText: sys.highlightedText
    readonly property color chipBg: Qt.rgba(sys.windowText.r, sys.windowText.g, sys.windowText.b, 0.08)
}
