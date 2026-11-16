import QtQuick
import QtQuick.Effects
import QtQuick.Layouts
import QtQuick.Window

// Mini-player 380×176, always on top, frameless, draggable.
Window {
    id: mini
    readonly property real m: 22   // room for the drop shadow
    width: 380 + m * 2
    height: 176 + m * 2
    flags: Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
    color: "transparent"
    title: qsTr("Nocturne mini player")
    visible: App.miniPlayerVisible
    readonly property var track: Player.currentTrack

    onClosing: (close) => { App.miniPlayerVisible = false }
    onVisibleChanged: if (visible) placeWindow()

    function placeWindow() {
        var sx = AppSettings.miniX, sy = AppSettings.miniY
        if (sx > -10000 && sy > -10000) { x = sx; y = sy; return }
        x = Screen.virtualX + Screen.desktopAvailableWidth - width - 24
        y = Screen.virtualY + Screen.desktopAvailableHeight - height - 24
    }
    Timer {
        id: saveTimer
        interval: 400
        onTriggered: { AppSettings.miniX = mini.x; AppSettings.miniY = mini.y }
    }
    onXChanged: if (visible) saveTimer.restart()
    onYChanged: if (visible) saveTimer.restart()

    Rectangle {
        id: shadowSource
        x: mini.m; y: mini.m
        width: 380; height: 176
        radius: Theme.rPanel
        color: "#000000"
        visible: false
    }
    MultiEffect {
        source: shadowSource
        anchors.fill: shadowSource
        shadowEnabled: true
        shadowColor: "#99000000"
        shadowBlur: 0.8
        shadowVerticalOffset: 8
    }

    GradientRect {
        id: card
        x: mini.m; y: mini.m
        width: 380; height: 176
        radius: Theme.rPanel

        MouseArea {
            anchors.fill: parent
            onPressed: mini.startSystemMove()
            onDoubleClicked: App.showMainWindow()
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.leftMargin: 16
            anchors.rightMargin: 16
            anchors.topMargin: 14
            anchors.bottomMargin: 14
            spacing: 12

            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                Artwork {
                    Layout.preferredWidth: 56
                    Layout.preferredHeight: 56
                    radius: 14
                    source: mini.track.artwork || ""
                    colors: [Theme.artStart, Theme.artEnd]
                    placeholderIcon: "moon"
                    iconSize: 22
                    insetLine: true
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    Text {
                        id: miniTitle
                        Layout.fillWidth: true
                        text: Player.hasTrack ? (mini.track.title || "") : qsTr("Nothing playing")
                        color: Theme.text
                        font.pixelSize: 15
                        font.weight: Font.ExtraBold
                        elide: Text.ElideRight
                    }
                    Text {
                        Layout.fillWidth: true
                        text: Player.hasTrack ? (mini.track.artist || "") : "Nocturne"
                        color: Theme.textOnGradient
                        font.pixelSize: 13
                        elide: Text.ElideRight
                    }
                }
                NButton {
                    Layout.alignment: Qt.AlignTop
                    implicitWidth: 32; implicitHeight: 32; radius: 10
                    bg: Theme.glass
                    hoverBg: "#33F1F1F7"
                    icon: "expand"; iconSize: 15
                    tooltip: qsTr("Open the main window")
                    onClicked: { App.showMainWindow(); App.miniPlayerVisible = false }
                }
                NButton {
                    Layout.alignment: Qt.AlignTop
                    implicitWidth: 32; implicitHeight: 32; radius: 10
                    bg: Theme.glass
                    hoverBg: "#33F1F1F7"
                    icon: "close"; iconSize: 15
                    tooltip: qsTr("Close the mini player")
                    onClicked: App.miniPlayerVisible = false
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                Text {
                    text: Fmt.durationMs(Player.position)
                    color: Theme.textOnGradient
                    font.pixelSize: 11
                    font.weight: Font.DemiBold
                }
                SeekBar {
                    Layout.fillWidth: true
                    barHeight: 4
                    thumbSize: 11
                    thumbOnHover: true
                    gradientFill: false
                    fillColor: Theme.text
                    trackColor: "#38F1F1F7"
                    value: Player.duration > 0 ? Player.position / Player.duration : 0
                    interactive: Player.hasTrack
                    onCommitted: (v) => Player.seek(Math.round(v * Player.duration))
                }
                Text {
                    text: Fmt.durationMs(Player.duration)
                    color: Theme.textOnGradient
                    font.pixelSize: 11
                    font.weight: Font.DemiBold
                }
            }

            RowLayout {
                Layout.fillWidth: true
                NButton {
                    implicitWidth: 36; implicitHeight: 36; radius: 11
                    icon: "shuffle"; iconSize: 18
                    iconColor: Player.shuffle ? Theme.amber : Theme.text
                    bg: Player.shuffle ? Theme.amberSofter : "transparent"
                    hoverBg: "#1FF1F1F7"
                    tooltip: Player.shuffle ? qsTr("Shuffle: on") : qsTr("Shuffle: off")
                    onClicked: Player.toggleShuffle()
                }
                Item { Layout.fillWidth: true }
                NButton {
                    implicitWidth: 40; implicitHeight: 40; radius: 20
                    icon: "previous"; iconSize: 20
                    hoverBg: "#1FF1F1F7"
                    tooltip: qsTr("Previous")
                    onClicked: Player.previous()
                }
                Item { Layout.fillWidth: true }
                PlayButton {
                    size: 46
                    playing: Player.playing
                    glowBlur: 0.8
                    onClicked: Player.togglePlay()
                }
                Item { Layout.fillWidth: true }
                NButton {
                    implicitWidth: 40; implicitHeight: 40; radius: 20
                    icon: "next"; iconSize: 20
                    hoverBg: "#1FF1F1F7"
                    tooltip: qsTr("Next")
                    onClicked: Player.next()
                }
                Item { Layout.fillWidth: true }
                NButton {
                    implicitWidth: 36; implicitHeight: 36; radius: 11
                    icon: "repeat"; iconSize: 18
                    iconColor: Player.repeatMode > 0 ? Theme.amber : Theme.text
                    bg: Player.repeatMode > 0 ? Theme.amberSofter : "transparent"
                    hoverBg: "#1FF1F1F7"
                    tooltip: Player.repeatMode === 2 ? qsTr("Repeat: one")
                           : Player.repeatMode === 1 ? qsTr("Repeat: all") : qsTr("Repeat: off")
                    onClicked: Player.cycleRepeat()
                    Rectangle {
                        visible: Player.repeatMode === 2
                        anchors.right: parent.right; anchors.top: parent.top
                        anchors.rightMargin: 2; anchors.topMargin: 2
                        width: 13; height: 13; radius: 6.5
                        color: Theme.amber
                        Text { anchors.centerIn: parent; text: "1"; color: Theme.bg; font.pixelSize: 8; font.weight: Font.ExtraBold }
                    }
                }
            }
        }
    }

    Shortcut { sequences: ["Space"]; onActivated: Player.togglePlay() }
    Shortcut { sequences: ["Escape"]; onActivated: App.miniPlayerVisible = false }
}
