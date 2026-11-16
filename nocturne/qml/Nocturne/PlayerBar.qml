import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Rectangle {
    id: root
    color: Theme.panel
    implicitHeight: 104
    readonly property var track: Player.currentTrack

    Rectangle { anchors.top: parent.top; width: parent.width; height: 1; color: Theme.elevated }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 24
        anchors.rightMargin: 24
        anchors.topMargin: 14
        anchors.bottomMargin: 14
        spacing: 28

        // ------------------------------------------------------------ left
        RowLayout {
            Layout.fillWidth: true
            Layout.preferredWidth: 1
            Layout.horizontalStretchFactor: 1
            Layout.minimumWidth: 160
            spacing: 12
            Artwork {
                Layout.preferredWidth: 56
                Layout.preferredHeight: 56
                radius: 14
                source: root.track.artwork || ""
                colors: [Theme.gradStart, Theme.gradEnd]
                placeholderIcon: "moon"
                iconSize: 22
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Text {
                    id: barTitle
                    Layout.fillWidth: true
                    text: Player.hasTrack ? (root.track.title || "") : qsTr("Nothing playing")
                    color: Theme.text
                    font.pixelSize: 15
                    font.weight: Font.Bold
                    elide: Text.ElideRight
                    HoverHandler { id: barTitleHover }
                    NToolTip { visible: barTitleHover.hovered && barTitle.truncated; text: barTitle.text }
                }
                Text {
                    Layout.fillWidth: true
                    text: Player.hasTrack ? (root.track.artist || "") : "Nocturne"
                    color: Theme.textMuted
                    font.pixelSize: 13
                    elide: Text.ElideRight
                }
            }
        }

        // ---------------------------------------------------------- center
        ColumnLayout {
            Layout.fillWidth: true
            Layout.preferredWidth: 2
            Layout.horizontalStretchFactor: 2
            Layout.minimumWidth: 340
            spacing: 8
            RowLayout {
                Layout.alignment: Qt.AlignHCenter
                spacing: 14
                NButton {
                    implicitWidth: 40; implicitHeight: 40; radius: 12
                    icon: "shuffle"
                    iconSize: 20
                    iconColor: Player.shuffle ? Theme.amber : Theme.textMuted
                    bg: Player.shuffle ? Theme.amberSoft : "transparent"
                    tooltip: Player.shuffle ? qsTr("Shuffle: on") : qsTr("Shuffle: off")
                    onClicked: Player.toggleShuffle()
                }
                NButton {
                    implicitWidth: 44; implicitHeight: 44; radius: 22
                    icon: "previous"
                    iconSize: 22
                    tooltip: qsTr("Previous (Ctrl+←)")
                    onClicked: Player.previous()
                }
                PlayButton {
                    size: 52
                    playing: Player.playing
                    onClicked: Player.togglePlay()
                }
                NButton {
                    implicitWidth: 44; implicitHeight: 44; radius: 22
                    icon: "next"
                    iconSize: 22
                    tooltip: qsTr("Next (Ctrl+→)")
                    onClicked: Player.next()
                }
                NButton {
                    id: repeatBtn
                    implicitWidth: 40; implicitHeight: 40; radius: 12
                    icon: "repeat"
                    iconSize: 20
                    iconColor: Player.repeatMode > 0 ? Theme.amber : Theme.textMuted
                    bg: Player.repeatMode > 0 ? Theme.amberSoft : "transparent"
                    tooltip: Player.repeatMode === 2 ? qsTr("Repeat: one")
                           : Player.repeatMode === 1 ? qsTr("Repeat: all") : qsTr("Repeat: off")
                    onClicked: Player.cycleRepeat()
                    Rectangle {
                        visible: Player.repeatMode === 2
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.rightMargin: 3
                        anchors.topMargin: 3
                        width: 14; height: 14; radius: 7
                        color: Theme.amber
                        Text {
                            anchors.centerIn: parent
                            text: "1"
                            color: Theme.bg
                            font.pixelSize: 9
                            font.weight: Font.ExtraBold
                        }
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                Layout.maximumWidth: 560
                Layout.alignment: Qt.AlignHCenter
                spacing: 10
                Text {
                    Layout.preferredWidth: Math.max(36, implicitWidth)
                    horizontalAlignment: Text.AlignRight
                    text: Fmt.durationMs(seek.dragging ? seek.dragValue * Player.duration : Player.position)
                    color: Theme.textMuted
                    font.pixelSize: 12
                    font.weight: Font.DemiBold
                }
                SeekBar {
                    id: seek
                    Layout.fillWidth: true
                    value: Player.duration > 0 ? Player.position / Player.duration : 0
                    interactive: Player.hasTrack
                    onCommitted: (v) => Player.seek(Math.round(v * Player.duration))
                    Accessible.name: qsTr("Seek")
                }
                Text {
                    Layout.preferredWidth: Math.max(36, implicitWidth)
                    text: Fmt.durationMs(Player.duration)
                    color: Theme.textMuted
                    font.pixelSize: 12
                    font.weight: Font.DemiBold
                }
            }
        }

        // ----------------------------------------------------------- right
        RowLayout {
            Layout.fillWidth: true
            Layout.preferredWidth: 1
            Layout.horizontalStretchFactor: 1
            Layout.minimumWidth: 220
            spacing: 10
            Item { Layout.fillWidth: true }
            NButton {
                id: queueBtn
                implicitWidth: 40; implicitHeight: 40; radius: 12
                icon: "queue"
                iconSize: 20
                iconColor: queuePopup.opened ? Theme.amber : Theme.textMuted
                bg: queuePopup.opened ? Theme.amberSoft : "transparent"
                tooltip: qsTr("Queue")
                onClicked: queuePopup.opened ? queuePopup.close() : queuePopup.open()
            }
            NButton {
                implicitWidth: 34; implicitHeight: 40; radius: 12
                icon: Player.muted || Player.volume === 0 ? "volume-x" : "volume"
                iconSize: 20
                iconColor: Theme.textMuted
                tooltip: Player.muted ? qsTr("Unmute") : qsTr("Mute")
                onClicked: Player.toggleMute()
            }
            SeekBar {
                Layout.preferredWidth: 110
                barHeight: 4
                thumbSize: 12
                thumbOnHover: true
                gradientFill: false
                fillColor: Theme.textOnGradient
                value: Player.muted ? 0 : Player.volume
                onMoved: (v) => Player.setVolume(v)
                onCommitted: (v) => Player.setVolume(v)
                Accessible.name: qsTr("Volume")
            }
            NButton {
                id: miniBtn
                implicitWidth: 40; implicitHeight: 40; radius: 12
                bg: Theme.elevated
                icon: "miniplayer"
                iconSize: 20
                tooltip: qsTr("Mini player / desktop widget")
                onClicked: miniMenu.popup(miniBtn, miniBtn.width - 230, -miniMenu.implicitHeight - 8)
            }
        }
    }

    NMenu {
        id: miniMenu
        NMenuItem {
            text: App.miniPlayerVisible ? qsTr("Close mini player") : qsTr("Open mini player")
            iconName: "miniplayer"
            onTriggered: App.toggleMiniPlayer()
        }
        NMenuItem {
            text: AppSettings.widgetVisible ? qsTr("Hide desktop widget") : qsTr("Show desktop widget")
            iconName: "widgets"
            onTriggered: App.toggleDesktopWidget()
        }
    }

    Popup {
        id: queuePopup
        parent: queueBtn
        x: queueBtn.width - width
        y: -height - 12
        width: 360
        height: Math.min(460, Math.max(220, root.Window.height - 200))
        padding: 16
        modal: false
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent
        enter: Transition {
            NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.fast }
            NumberAnimation { property: "y"; from: -queuePopup.height; to: -queuePopup.height - 12; duration: Theme.fast; easing.type: Easing.OutQuad }
        }
        background: Rectangle {
            color: Theme.panel
            radius: Theme.rPanel
            border.color: Theme.elevated
            border.width: 1
        }
        contentItem: ColumnLayout {
            spacing: 8
            RowLayout {
                Layout.fillWidth: true
                Text {
                    Layout.fillWidth: true
                    text: qsTr("Up next")
                    color: Theme.text
                    font.pixelSize: 15
                    font.weight: Font.Bold
                }
                NButton {
                    implicitHeight: 32; padH: 10; radius: 10
                    text: qsTr("Clear"); textColor: Theme.textMuted; fontSize: 12
                    enabled: popupList.count > 0
                    onClicked: Player.clearQueue()
                }
            }
            QueueList {
                id: popupList
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
            Text {
                visible: popupList.count === 0
                Layout.fillWidth: true
                Layout.fillHeight: true
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                wrapMode: Text.Wrap
                text: qsTr("The queue is empty. Right-click a song → “Add to queue”.")
                color: Theme.textMuted
                font.pixelSize: 13
            }
        }
    }
}
