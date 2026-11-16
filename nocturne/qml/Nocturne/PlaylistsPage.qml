import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

ColumnLayout {
    id: root
    spacing: 22
    signal newPlaylistRequested()
    signal playlistOptionsRequested(int playlistId, string name, var anchorItem)

    RowLayout {
        Layout.fillWidth: true
        spacing: 16
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 4
            Text {
                Layout.fillWidth: true
                text: qsTr("Playlists")
                color: Theme.text
                font.pixelSize: 34
                font.weight: Font.ExtraBold
                font.letterSpacing: -0.7
                elide: Text.ElideRight
            }
            Text {
                Layout.fillWidth: true
                text: Fmt.revision >= 0 ? qsTr("%n playlist(s)", "", App.playlists.count) : ""
                color: Theme.textMuted
                font.pixelSize: 14
                elide: Text.ElideRight
            }
        }
        NButton {
            Layout.alignment: Qt.AlignBottom
            gradient: true
            icon: "plus"
            iconSize: 16
            text: qsTr("New playlist")
            onClicked: root.newPlaylistRequested()
        }
    }

    GridView {
        id: grid
        Layout.fillWidth: true
        Layout.fillHeight: true
        clip: true
        visible: count > 0
        readonly property int columns: Math.max(2, Math.floor(width / 210))
        cellWidth: Math.floor(width / columns)
        cellHeight: cellWidth + 64
        model: App.playlists
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: NScrollBar {}
        delegate: Item {
            id: card
            required property int playlistId
            required property string name
            required property int colorIndex
            required property int trackCount
            required property real duration
            width: grid.cellWidth
            height: grid.cellHeight

            Rectangle {
                anchors.fill: parent
                anchors.margins: 6
                radius: Theme.rCard
                color: cardMouse.containsMouse || drop.containsDrag ? Theme.surface : Theme.panel
                border.width: drop.containsDrag ? 1.5 : 0
                border.color: Theme.brightStart
                Behavior on color { ColorAnimation { duration: Theme.fast } }
                scale: cardMouse.pressed ? 0.98 : 1
                Behavior on scale { NumberAnimation { duration: 120 } }

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 8
                    GradientRect {
                        Layout.fillWidth: true
                        Layout.preferredHeight: width
                        radius: 18
                        startColor: Theme.playlistArt(card.colorIndex)[0]
                        endColor: Theme.playlistArt(card.colorIndex)[1]
                        Icon { anchors.centerIn: parent; name: "playlists"; size: parent.width * 0.3; color: "#D9F1F1F7" }
                        PlayButton {
                            anchors.right: parent.right
                            anchors.bottom: parent.bottom
                            anchors.margins: 10
                            size: 44
                            glow: true
                            playing: false
                            opacity: cardMouse.containsMouse ? 1 : 0
                            Behavior on opacity { NumberAnimation { duration: Theme.fast } }
                            onClicked: App.playPlaylist(card.playlistId)
                        }
                    }
                    Text {
                        Layout.fillWidth: true
                        text: card.name
                        color: Theme.text
                        font.pixelSize: 15
                        font.weight: Font.Bold
                        elide: Text.ElideRight
                    }
                    Text {
                        Layout.fillWidth: true
                        text: Fmt.revision >= 0 ? Fmt.songs(card.trackCount) + " · " + Fmt.totalDuration(card.duration) : ""
                        color: Theme.textMuted
                        font.pixelSize: 12
                        elide: Text.ElideRight
                    }
                }
            }
            MouseArea {
                id: cardMouse
                anchors.fill: parent
                anchors.margins: 6
                hoverEnabled: true
                z: -1
                acceptedButtons: Qt.LeftButton | Qt.RightButton
                cursorShape: Qt.PointingHandCursor
                onClicked: (m) => {
                    if (m.button === Qt.RightButton) root.playlistOptionsRequested(card.playlistId, card.name, card)
                    else App.openPlaylist(card.playlistId)
                }
            }
            DropArea {
                id: drop
                anchors.fill: parent
                keys: ["nocturne/track"]
                onDropped: (d) => { if (d.source) App.addToPlaylist(d.source.dragTrackId, card.playlistId) }
            }
        }
    }

    Item {
        visible: grid.count === 0
        Layout.fillWidth: true
        Layout.fillHeight: true
        Column {
            anchors.centerIn: parent
            width: Math.min(480, parent.width - 40)
            spacing: 14
            GradientRect {
                anchors.horizontalCenter: parent.horizontalCenter
                width: 88; height: 88; radius: 28
                Icon { anchors.centerIn: parent; name: "playlists"; size: 40 }
            }
            Text {
                width: parent.width
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
                text: qsTr("No playlists yet")
                color: Theme.text
                font.pixelSize: 20
                font.weight: Font.ExtraBold
            }
            Text {
                width: parent.width
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
                text: qsTr("Create one with the + button, or download a YouTube playlist — it becomes a playlist here automatically.")
                color: Theme.textMuted
                font.pixelSize: 14
            }
        }
    }
}
