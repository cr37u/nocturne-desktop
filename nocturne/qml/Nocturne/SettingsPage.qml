import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import QtQuick.Layouts

Flickable {
    id: root
    contentHeight: col.implicitHeight + 24
    clip: true
    boundsBehavior: Flickable.StopAtBounds
    ScrollBar.vertical: NScrollBar {}

    readonly property bool wide: width > 620

    ColumnLayout {
        id: col
        width: root.width - 12
        spacing: 16

        ColumnLayout {
            Layout.fillWidth: true
            Layout.bottomMargin: 6
            spacing: 4
            Text {
                Layout.fillWidth: true
                text: qsTr("Settings")
                color: Theme.text
                font.pixelSize: 34
                font.weight: Font.ExtraBold
                font.letterSpacing: -0.7
                elide: Text.ElideRight
            }
            Text {
                Layout.fillWidth: true
                text: qsTr("Nocturne %1 · everything stays on this computer").arg(App.version)
                color: Theme.textMuted
                font.pixelSize: 14
                elide: Text.ElideRight
            }
        }

        // ------------------------------------------------------------ Limbă
        SettingsSection {
            Layout.fillWidth: true
            title: qsTr("Language")
            subtitle: qsTr("The interface switches instantly, no restart needed.")
            GridLayout {
                Layout.fillWidth: true
                columns: root.wide ? 2 : 1
                rowSpacing: 10
                columnSpacing: 10
                ChoiceCard {
                    Layout.fillWidth: true
                    title: qsTr("System language")
                    subtitle: qsTr("Follow Windows/Linux (fallback: Română)")
                    chip: "AUTO"
                    selected: Lang.language === "system"
                    onClicked: Lang.setLanguage("system")
                }
                Repeater {
                    model: Lang.languages
                    delegate: ChoiceCard {
                        required property var modelData
                        Layout.fillWidth: true
                        title: modelData.name
                        chip: modelData.chip
                        selected: Lang.language === modelData.code
                        onClicked: Lang.setLanguage(modelData.code)
                    }
                }
            }
        }

        // ------------------------------------------------------- Descărcări
        SettingsSection {
            Layout.fillWidth: true
            title: qsTr("Downloads")
            SettingRow {
                Layout.fillWidth: true
                label: qsTr("Download folder")
                description: App.downloadDir
                NButton { text: qsTr("Change…"); bg: Theme.elevated; fontSize: 13; onClicked: folderDialog.open() }
                NButton { text: qsTr("Open"); bg: Theme.surface; fontSize: 13; textColor: Theme.textMuted; onClicked: App.openDownloadDir() }
                NButton {
                    visible: AppSettings.downloadDir !== ""
                    icon: "retry"; iconColor: Theme.textMuted; bg: Theme.surface
                    tooltip: qsTr("Reset to the default Music folder")
                    onClicked: App.resetDownloadDir()
                }
            }
            SettingRow {
                Layout.fillWidth: true
                label: qsTr("Parallel downloads")
                description: qsTr("How many songs download at the same time (1–8).")
                NButton {
                    implicitWidth: 36; implicitHeight: 36; radius: 11; bg: Theme.elevated
                    text: "−"; fontSize: 16
                    enabled: AppSettings.parallelDownloads > 1
                    onClicked: AppSettings.parallelDownloads = AppSettings.parallelDownloads - 1
                }
                Text {
                    Layout.preferredWidth: 28
                    horizontalAlignment: Text.AlignHCenter
                    text: AppSettings.parallelDownloads
                    color: Theme.text
                    font.pixelSize: 16
                    font.weight: Font.ExtraBold
                }
                NButton {
                    implicitWidth: 36; implicitHeight: 36; radius: 11; bg: Theme.elevated
                    text: "+"; fontSize: 16
                    enabled: AppSettings.parallelDownloads < 8
                    onClicked: AppSettings.parallelDownloads = AppSettings.parallelDownloads + 1
                }
            }
            Text {
                Layout.fillWidth: true
                text: qsTr("Audio quality")
                color: Theme.text
                font.pixelSize: 14
                font.weight: Font.Bold
            }
            GridLayout {
                Layout.fillWidth: true
                columns: root.wide ? 3 : 1
                rowSpacing: 10
                columnSpacing: 10
                ChoiceCard {
                    Layout.fillWidth: true
                    title: qsTr("Best")
                    subtitle: qsTr("Highest bitrate (m4a/AAC preferred)")
                    selected: AppSettings.audioQuality === "best"
                    onClicked: AppSettings.audioQuality = "best"
                }
                ChoiceCard {
                    Layout.fillWidth: true
                    title: qsTr("Balanced")
                    subtitle: qsTr("Up to ~128 kbps, smaller files")
                    selected: AppSettings.audioQuality === "medium"
                    onClicked: AppSettings.audioQuality = "medium"
                }
                ChoiceCard {
                    Layout.fillWidth: true
                    title: qsTr("Data saver")
                    subtitle: qsTr("Lowest bitrate, smallest files")
                    selected: AppSettings.audioQuality === "low"
                    onClicked: AppSettings.audioQuality = "low"
                }
            }
        }

        // ------------------------------------------------------------ Sistem
        SettingsSection {
            Layout.fillWidth: true
            title: qsTr("System")
            SettingRow {
                Layout.fillWidth: true
                visible: App.autostartSupported
                label: qsTr("Start with the system")
                description: qsTr("Nocturne starts minimized when you sign in.")
                NSwitch { checked: App.startWithSystem; onToggled: (c) => App.setStartWithSystem(c) }
            }
            SettingRow {
                Layout.fillWidth: true
                visible: App.trayAvailable
                label: qsTr("Keep playing in the tray when the window is closed")
                description: qsTr("Use the tray icon to show the window or quit.")
                NSwitch { checked: AppSettings.keepRunningInTray; onToggled: (c) => AppSettings.keepRunningInTray = c }
            }
            SettingRow {
                Layout.fillWidth: true
                visible: !App.trayAvailable
                label: qsTr("Keep running when the window is closed")
                description: qsTr("No system tray was found (on GNOME install the “AppIndicator” extension). Launch Nocturne again to show the window.")
                NSwitch { checked: AppSettings.keepRunningWithoutTray; onToggled: (c) => AppSettings.keepRunningWithoutTray = c }
            }
            SettingRow {
                Layout.fillWidth: true
                label: qsTr("Desktop widget")
                description: qsTr("A small player that stays on your desktop, even when the window is closed.")
                NSwitch { checked: AppSettings.widgetVisible; onToggled: (c) => AppSettings.widgetVisible = c }
            }
            SettingRow {
                Layout.fillWidth: true
                label: qsTr("Mini player")
                description: qsTr("Compact always-on-top player.")
                NSwitch { checked: App.miniPlayerVisible; onToggled: (c) => App.miniPlayerVisible = c }
            }
            SettingRow {
                Layout.fillWidth: true
                visible: App.os === "linux" && App.capabilities.kde === true
                label: qsTr("KDE Plasma widget")
                description: qsTr("Installs a Nocturne widget you can add to the desktop or panel.")
                NButton { text: qsTr("Install KDE widget"); gradient: true; fontSize: 13; onClicked: App.installKdeWidget() }
            }
            Text {
                Layout.fillWidth: true
                visible: App.os === "linux" && App.capabilities.wayland === true
                wrapMode: Text.Wrap
                text: qsTr("Wayland: the compositor decides where windows go, so “Always on top” and the widget position may be ignored. Everything works fully under X11/XWayland.")
                color: Theme.textMuted
                font.pixelSize: 12
            }
        }

        // ------------------------------------------------------------ yt-dlp
        SettingsSection {
            Layout.fillWidth: true
            title: "yt-dlp"
            subtitle: qsTr("The engine that reads YouTube. When YouTube changes, an update usually fixes failing downloads.")
            SettingRow {
                Layout.fillWidth: true
                label: qsTr("Version %1").arg(App.ytdlpVersion)
                description: App.ytdlpStatus
                NButton {
                    text: qsTr("Check for updates")
                    icon: "refresh"
                    spinning: App.ytdlpBusy
                    enabled: !App.ytdlpBusy
                    bg: Theme.elevated
                    fontSize: 13
                    onClicked: App.checkYtDlpUpdate()
                }
                NButton {
                    visible: App.ytdlpRestartNeeded
                    text: qsTr("Restart")
                    gradient: true
                    fontSize: 13
                    onClicked: App.restartApp()
                }
            }
        }

        // ------------------------------------------------------------ Despre
        SettingsSection {
            Layout.fillWidth: true
            title: qsTr("About")
            SettingRow {
                Layout.fillWidth: true
                label: "Nocturne " + App.version
                description: qsTr("Local music player. Downloads audio from YouTube links and plays it offline.")
                NButton { text: qsTr("Open log folder"); bg: Theme.elevated; fontSize: 13; onClicked: App.openLogs() }
            }
            SettingRow {
                Layout.fillWidth: true
                label: qsTr("Nocturne for Android")
                description: qsTr("The same player on your phone: same design, same YouTube links, everything offline.")
                NButton {
                    text: qsTr("Get the app")
                    icon: "download"
                    iconSize: 16
                    gradient: true
                    fontSize: 13
                    onClicked: Qt.openUrlExternally("https://github.com/cr37u/nocturne/releases/latest")
                }
            }
            SettingRow {
                Layout.fillWidth: true
                label: qsTr("Source code and updates")
                description: "github.com/cr37u/nocturne-desktop"
                NButton {
                    text: "GitHub"
                    bg: Theme.elevated
                    fontSize: 13
                    onClicked: Qt.openUrlExternally("https://github.com/cr37u/nocturne-desktop")
                }
            }
        }
    }

    FolderDialog {
        id: folderDialog
        title: qsTr("Choose the download folder")
        currentFolder: App.downloadDirUrl
        onAccepted: App.setDownloadDir(selectedFolder.toString())
    }
}
