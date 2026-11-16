import QtQuick
import QtQuick.Effects
import QtQuick.Layouts

ColumnLayout {
    id: root
    spacing: 16
    readonly property var track: Player.currentTrack
    readonly property bool showDownloads: Downloads.totalCount > 0
    // Artwork shrinks on short windows so the queue keeps a usable height.
    readonly property real artSize: Math.max(120, Math.min(width - 40,
        height - 160 - 220 - (showDownloads ? downloadsCard.implicitHeight + 16 : 0)))

    // ---------------------------------------------------------- SE REDĂ ACUM
    GradientRect {
        id: nowCard
        Layout.fillWidth: true
        Layout.preferredHeight: nowCol.implicitHeight + 40
        radius: Theme.rCard
        angle: 170
        startColor: Theme.gradStart
        midColor: Theme.gradEnd
        midPosition: 0.7
        endColor: Theme.gradDeep

        ColumnLayout {
            id: nowCol
            anchors.fill: parent
            anchors.margins: 20
            spacing: 16
            Text {
                Layout.fillWidth: true
                text: qsTr("NOW PLAYING")
                color: Theme.textOnGradient
                font.pixelSize: 11
                font.weight: Font.ExtraBold
                font.letterSpacing: 1.3
                elide: Text.ElideRight
            }
            Item {
                Layout.alignment: Qt.AlignHCenter
                Layout.preferredWidth: root.artSize
                Layout.preferredHeight: root.artSize
                Rectangle {
                    id: artShadowSource
                    anchors.fill: parent
                    radius: 20
                    color: "#000000"
                    visible: false
                }
                MultiEffect {
                    source: artShadowSource
                    anchors.fill: artShadowSource
                    shadowEnabled: true
                    shadowColor: "#800A0A14"
                    shadowBlur: 1.0
                    shadowVerticalOffset: 20
                    shadowScale: 0.96
                    opacity: 0.9
                }
                Artwork {
                    anchors.fill: parent
                    radius: 20
                    source: root.track.artwork || ""
                    colors: [Theme.artStart, Theme.artEnd]
                    placeholderIcon: "moon-wave"
                    iconSize: parent.width * 0.42
                    iconColor: "#D9F1F1F7"
                }
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3
                    Text {
                        id: nowTitle
                        Layout.fillWidth: true
                        text: Player.hasTrack ? (root.track.title || "") : qsTr("Nothing playing")
                        color: Theme.text
                        font.pixelSize: 20
                        font.weight: Font.ExtraBold
                        elide: Text.ElideRight
                        HoverHandler { id: titleHover }
                        NToolTip { visible: titleHover.hovered && nowTitle.truncated; text: nowTitle.text }
                    }
                    Text {
                        Layout.fillWidth: true
                        text: Player.hasTrack
                              ? root.track.artist + (root.track.playlistName ? " · " + root.track.playlistName : "")
                              : qsTr("Pick a song from your library")
                        color: Theme.textOnGradient
                        font.pixelSize: 14
                        elide: Text.ElideRight
                    }
                }
                NButton {
                    visible: Player.hasTrack
                    implicitWidth: 44
                    implicitHeight: 44
                    bg: Theme.glass
                    hoverBg: "#2EF1F1F7"
                    icon: root.track.favorite ? "heart-filled" : "heart"
                    iconColor: Theme.amber
                    iconSize: 20
                    tooltip: root.track.favorite ? qsTr("Remove from favorites") : qsTr("Add to favorites")
                    onClicked: App.toggleFavoriteCurrent()
                }
            }
        }
    }

    // ---------------------------------------------------------------- Urmează
    Rectangle {
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.minimumHeight: 150
        color: Theme.panel
        radius: Theme.rPanel
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 6
            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 4
                Layout.rightMargin: 4
                Layout.bottomMargin: 6
                Text {
                    Layout.fillWidth: true
                    text: qsTr("Up next")
                    color: Theme.text
                    font.pixelSize: 15
                    font.weight: Font.Bold
                    elide: Text.ElideRight
                }
                NButton {
                    implicitHeight: 32
                    padH: 10
                    radius: 10
                    text: qsTr("Clear")
                    textColor: Theme.textMuted
                    fontSize: 12
                    enabled: queueList.count > 0
                    onClicked: Player.clearQueue()
                }
            }
            QueueList {
                id: queueList
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
            Text {
                visible: queueList.count === 0
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

    // ------------------------------------------------------------ Descărcări
    DownloadsCard {
        id: downloadsCard
        visible: root.showDownloads
        Layout.fillWidth: true
    }
}
