import QtQuick
import QtQuick.Layouts

// One row of the library table: # | TITLU | PLAYLIST | ADĂUGAT | DURATĂ | ⋯
Item {
    id: row
    required property int index
    required property int trackId
    required property string title
    required property string artist
    required property real duration
    required property string playlistName
    required property string addedAt
    required property string artwork
    required property int colorSeed
    required property bool isCurrent
    required property bool favorite
    required property int number

    property bool compact: false
    property var menuHost: null
    property Item dragLayer: null

    height: 56

    Rectangle {
        anchors.fill: parent
        radius: 14
        color: row.isCurrent ? Theme.surface : (rowMouse.containsMouse ? Theme.hover : "transparent")
        Behavior on color { ColorAnimation { duration: Theme.fast } }
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 12
        anchors.rightMargin: 12
        spacing: 12

        Item {
            Layout.preferredWidth: 40
            Layout.fillHeight: true
            Text {
                anchors.verticalCenter: parent.verticalCenter
                visible: !row.isCurrent && !rowMouse.containsMouse
                text: row.number
                color: Theme.textMuted
                font.pixelSize: 13
                font.weight: Font.Bold
            }
            Icon {
                anchors.verticalCenter: parent.verticalCenter
                visible: row.isCurrent || rowMouse.containsMouse
                name: row.isCurrent && Player.playing && rowMouse.containsMouse ? "pause" : "play"
                size: 15
                color: row.isCurrent ? Theme.amber : Theme.text
                MouseArea {
                    anchors.fill: parent
                    anchors.margins: -6
                    cursorShape: Qt.PointingHandCursor
                    onClicked: row.isCurrent ? Player.togglePlay() : App.playFromView(row.trackId)
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.horizontalStretchFactor: 3
            Layout.preferredWidth: 1
            spacing: 12
            Artwork {
                Layout.preferredWidth: 40
                Layout.preferredHeight: 40
                radius: 11
                source: row.artwork
                seed: row.colorSeed
                iconSize: 16
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Text {
                    id: titleText
                    Layout.fillWidth: true
                    text: row.title
                    color: row.isCurrent ? Theme.amber : Theme.text
                    font.pixelSize: 14
                    font.weight: Font.Bold
                    elide: Text.ElideRight
                }
                Text {
                    Layout.fillWidth: true
                    text: row.artist
                    color: Theme.textMuted
                    font.pixelSize: 12
                    elide: Text.ElideRight
                }
            }
        }

        Text {
            visible: !row.compact
            Layout.fillWidth: true
            Layout.horizontalStretchFactor: 2
            Layout.preferredWidth: 1
            text: row.playlistName !== "" ? row.playlistName : "—"
            color: Theme.textMuted
            font.pixelSize: 13
            elide: Text.ElideRight
        }
        Text {
            visible: !row.compact
            Layout.preferredWidth: 120
            text: Fmt.revision >= 0 ? Fmt.date(row.addedAt) : ""
            color: Theme.textMuted
            font.pixelSize: 13
            elide: Text.ElideRight
        }
        Text {
            Layout.preferredWidth: 70
            horizontalAlignment: Text.AlignRight
            text: Fmt.duration(row.duration)
            color: Theme.textMuted
            font.pixelSize: 13
        }
        NButton {
            Layout.preferredWidth: 36
            Layout.preferredHeight: 36
            Layout.leftMargin: 4
            radius: 11
            icon: "more"
            iconSize: 18
            iconColor: Theme.textMuted
            tooltip: qsTr("Song options")
            onClicked: if (row.menuHost) row.menuHost.openFor(row.trackId, row.title, row.favorite, null)
        }
    }

    MouseArea {
        id: rowMouse
        anchors.fill: parent
        anchors.rightMargin: 56
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        drag.target: dragProxy
        drag.threshold: 12
        onDoubleClicked: (m) => { if (m.button === Qt.LeftButton) App.playFromView(row.trackId) }
        onClicked: (m) => {
            if (m.button === Qt.RightButton && row.menuHost)
                row.menuHost.openFor(row.trackId, row.title, row.favorite, null)
        }
        onReleased: {
            if (dragProxy.Drag.active)
                dragProxy.Drag.drop()
            dragProxy.x = 12
            dragProxy.y = 6
        }
    }

    // Drag ghost (dropped onto a sidebar playlist).
    Item {
        id: dragProxy
        property int dragTrackId: row.trackId
        x: 12; y: 6
        width: ghost.width
        height: 44
        visible: Drag.active
        Drag.active: rowMouse.drag.active
        Drag.keys: ["nocturne/track"]
        Drag.hotSpot.x: 20
        Drag.hotSpot.y: 22
        Drag.source: dragProxy
        states: State {
            when: dragProxy.Drag.active && row.dragLayer !== null
            ParentChange { target: dragProxy; parent: row.dragLayer }
        }
        Rectangle {
            id: ghost
            width: Math.min(280, ghostRow.implicitWidth + 20)
            height: 44
            radius: 14
            color: Theme.elevated
            border.color: Theme.brightEnd
            border.width: 1
            opacity: 0.95
            Row {
                id: ghostRow
                anchors.verticalCenter: parent.verticalCenter
                x: 6
                spacing: 10
                Artwork { width: 32; height: 32; radius: 9; source: row.artwork; seed: row.colorSeed; iconSize: 14 }
                Text {
                    text: row.title
                    color: Theme.text
                    font.pixelSize: 13
                    font.weight: Font.Bold
                    elide: Text.ElideRight
                    width: Math.min(implicitWidth, 220)
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
        }
    }
}
