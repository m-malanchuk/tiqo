import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import form 1.0
import controls 1.0

AppToolWindow {
    id: dialog
    titleText: t("settings.window_title")
    bodyWidth: 480
    onRejected: settings.closeSettings()

    function syncCombo(combo, value) {
        for (var i = 0; i < combo.count; i++) {
            if (combo.model.data(combo.model.index(i, 0), 257) === value) {
                combo.currentIndex = i
                return
            }
        }
    }

    FormField {
        label: t("settings.language")
        FormComboBox {
            id: langCombo
            model: settings.languageModel
            textRole: "title"
            valueRole: "value"
            onActivated: settings.setLanguage(currentValue)
            Component.onCompleted: dialog.syncCombo(langCombo, settings.language)
            Connections {
                target: settings
                function onChanged() { dialog.syncCombo(langCombo, settings.language) }
                function onLanguageChanged() {
                    dialog.syncCombo(langCombo, settings.language)
                }
            }
        }
    }

    FormField {
        label: t("settings.font_size")
        FormComboBox {
            id: fontCombo
            model: settings.fontModel
            textRole: "title"
            valueRole: "value"
            onActivated: settings.setFontSize(currentValue)
            Component.onCompleted: dialog.syncCombo(fontCombo, settings.fontSize)
            Connections {
                target: settings
                function onChanged() { dialog.syncCombo(fontCombo, settings.fontSize) }
            }
        }
    }

    FormField {
        label: t("settings.close_behavior")
        FormComboBox {
            id: closeCombo
            model: settings.closeModel
            textRole: "title"
            valueRole: "value"
            onActivated: settings.setCloseBehavior(currentValue)
            Component.onCompleted: dialog.syncCombo(closeCombo, settings.closeBehavior)
            Connections {
                target: settings
                function onChanged() { dialog.syncCombo(closeCombo, settings.closeBehavior) }
            }
        }
    }

    FormField {
        label: t("settings.autostart")
        FormCheckBox {
            text: t("settings.autostart_enabled")
            checked: settings.autostart
            onToggled: settings.setAutostart(checked)
        }
    }

    FormField {
        label: t("settings.timer_sound")
        FormComboBox {
            id: soundCombo
            model: settings.soundModel
            textRole: "title"
            valueRole: "value"
            onActivated: settings.setTimerSound(currentValue)
            Component.onCompleted: dialog.syncCombo(soundCombo, settings.timerSound)
            Connections {
                target: settings
                function onChanged() { dialog.syncCombo(soundCombo, settings.timerSound) }
            }
        }
    }

    FormHint {
        text: settings.soundsPathHint
    }

    FormField {
        label: t("settings.tray_icon")
        FormComboBox {
            id: trayCombo
            model: settings.trayIconModel
            textRole: "title"
            valueRole: "value"
            onActivated: settings.setTrayIcon(currentValue)
            Component.onCompleted: dialog.syncCombo(trayCombo, settings.trayIcon)
            Connections {
                target: settings
                function onChanged() { dialog.syncCombo(trayCombo, settings.trayIcon) }
            }
        }
    }

    RowLayout {
        Layout.alignment: Qt.AlignRight
        FormButton {
            text: t("action.ok")
            highlighted: true
            onClicked: settings.closeSettings()
        }
    }
}
