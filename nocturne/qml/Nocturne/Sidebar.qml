import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root
    color: Theme.panel
    radius: Theme.rPanel

    signal newPlaylistRequested()
    signal playlistMenuRequested(int playlistId, string name, var anchorItem)
    signal tracksDropped(int trackId, int playlistId)

    ColumnLayout {
        anchors.fill: parent
        anchors.topMargin: 20
        anchors.bottomMargin: 20
        anchors.leftMargin: 14
        anchors.rightMargin: 14
        spacing: 6

        // Logo
        Row {
            Layout.leftMargin: 8
            Layout.bottomMargin: 18
            spacing: 10
            GradientRect {
                width: 36; height: 36; radius: 12
                Icon { anchors.centerIn: parent; name: "moon"; size: 18; color: Theme.text }
            }
            Text {
                text: "Nocturne"
                color: Theme.text
                font.pixelSize: 20
                font.weight: Font.ExtraBold
                font.letterSpacing: -0.4
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        NavItem {
            Layout.fillWidth: true
            icon: "music"
            text: qsTr("Library")
            active: App.page === "library"
            onClicked: App.navigate("library")
        }
        NavItem {
            Layout.fillWidth: true
            icon: "playlists"
            text: qsTr("Playlists")
            active: App.page === "playlists"
            onClicked: App.navigate("playlists")
        }
        NavItem {
            Layout.fillWidth: true
            icon: "download"
            text: qsTr("Downloads")
            badge: Downloads.pendingCount
            active: App.page === "downloads"
            onClicked: App.navigate("downloads")
        }
        NavItem {
            Layout.fillWidth: true
            icon: "heart"
            text: qsTr("Favorites")
            active: App.page === "favorites"
            onClicked: App.navigate("favorites")
        }

        // PLAYLISTURI header
        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: 18
            Layout.leftMargin: 12
            Layout.rightMargin: 12
            Layout.bottomMargin: 4
            Text {
                Layout.fillWidth: true
                text: qsTr("PLAYLISTS")
                color: Theme.textMuted
                font.pixelSize: 11
                font.weight: Font.ExtraBold
                font.letterSpacing: 1.3
                elide: Text.ElideRight
            }
            NButton {
                implicitHeight: 28
                implicitWidth: 28
                radius: 9
                bg: Theme.elevated
                icon: "plus"
                iconSize: 14
                tooltip: qsTr("New playlist")
                onClicked: root.newPlaylistRequested()
            }
        }

        ListView {
            id: playlistList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 2
            model: App.playlists
            boundsBehavior: Flickable.StopAtBounds
            delegate: Item {
                id: plItem
                required property int playlistId
                required property string name
                required property int colorIndex
                required property int trackCount
                width: ListView.view.width
                height: 40
                readonly property bool isActive: App.page === "playlist" && App.playlistId === playlistId

                Rectangle {
                    anchors.fill: parent
                    radius: 12
                    color: drop.containsDrag ? Theme.track
                         : plItem.isActive ? Theme.elevated
                         : (plMouse.containsMouse ? Theme.hover : "transparent")
                    border.width: drop.containsDrag ? 1.5 : 0
                    border.color: Theme.brightStart
                    Behavior on color { ColorAnimation { duration: Theme.fast } }
                }
                Row {
                    anchors.left: parent.left
                    anchors.leftMargin: 12
                    anchors.right: parent.right
                    anchors.rightMargin: 8
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 10
                    GradientRect {
                        width: 22; height: 22; radius: 7
                        startColor: Theme.playlistArt(plItem.colorIndex)[0]
                        endColor: Theme.playlistArt(plItem.colorIndex)[1]
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        id: plName
                        text: plItem.name
                        color: plItem.isActive ? Theme.text : Theme.textSoft
                        font.pixelSize: 14
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                        width: parent.width - 32
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
                MouseArea {
                    id: plMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    acceptedButtons: Qt.LeftButton | Qt.RightButton
                    cursorShape: Qt.PointingHandCursor
                    onClicked: (m) => {
                        if (m.button === Qt.RightButton)
                            root.playlistMenuRequested(plItem.playlistId, plItem.name, plItem)
                        else
                            App.openPlaylist(plItem.playlistId)
                    }
                    onDoubleClicked: App.playPlaylist(plItem.playlistId)
                }
                DropArea {
                    id: drop
                    anchors.fill: parent
                    keys: ["nocturne/track"]
                    onDropped: (d) => {
                        if (d.source && d.source.dragTrackId !== undefined) {
                            root.tracksDropped(d.source.dragTrackId, plItem.playlistId)
                            d.accept()
                        }
                    }
                }
                NToolTip {
                    visible: plMouse.containsMouse && !drop.containsDrag
                    text: plItem.name + " · " + Fmt.songs(plItem.trackCount) + (Fmt.revision < 0 ? "" : "")
                }
            }
        }

        // Storage
        ColumnLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 12
            Layout.rightMargin: 12
            Layout.topMargin: 16
            spacing: 8
            RowLayout {
                Layout.fillWidth: true
                Text {
                    Layout.fillWidth: true
                    text: qsTr("Storage used")
                    color: Theme.textMuted
                    font.pixelSize: 12
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }
                Text {
                    text: Fmt.revision >= 0 ? Fmt.size(App.storageUsed) : ""
                    color: Theme.textMuted
                    font.pixelSize: 12
                    font.weight: Font.DemiBold
                }
            }
            Rectangle {
                Layout.fillWidth: true
                height: 4
                radius: 2
                color: Theme.elevated
                Rectangle {
                    width: Math.max(App.storageFraction > 0 ? 4 : 0, parent.width * App.storageFraction)
                    height: 4
                    radius: 2
                    gradient: Gradient {
                        orientation: Gradient.Horizontal
                        GradientStop { position: 0; color: Theme.brightStart }
                        GradientStop { position: 1; color: Theme.brightEnd }
                    }
                    Behavior on width { NumberAnimation { duration: Theme.normal } }
                }
            }
        }
        NavItem {
            Layout.fillWidth: true
            Layout.topMargin: 8
            itemHeight: 40
            icon: "settings"
            text: qsTr("Settings")
            active: App.page === "settings"
            onClicked: App.navigate("settings")
        }
    }
}
