import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Library / Favorites / single playlist view.
ColumnLayout {
    id: root
    property var menuHost: null
    property Item dragLayer: null
    signal playlistOptionsRequested(int playlistId, string name, var anchorItem)

    spacing: 22
    readonly property bool compact: width < 600
    readonly property string sortMode: AppSettings.sortMode

    function sortLabel(mode) {
        switch (mode) {
        case "title": return qsTr("Title")
        case "artist": return qsTr("Artist")
        case "duration": return qsTr("Duration")
        default: return qsTr("Recently added")
        }
    }

    // Header
    RowLayout {
        Layout.fillWidth: true
        spacing: 16
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 4
            Text {
                Layout.fillWidth: true
                text: App.page === "favorites" ? qsTr("Favorites")
                    : App.page === "playlist" ? App.playlistName
                    : qsTr("Library")
                color: Theme.text
                font.pixelSize: 34
                font.weight: Font.ExtraBold
                font.letterSpacing: -0.7
                elide: Text.ElideRight
            }
            Text {
                Layout.fillWidth: true
                text: (Fmt.revision >= 0 ? Fmt.songs(App.library.count) : "") + " · "
                      + Fmt.totalDuration(App.library.totalDuration) + " · " + qsTr("all offline")
                color: Theme.textMuted
                font.pixelSize: 14
                elide: Text.ElideRight
            }
        }
        RowLayout {
            Layout.alignment: Qt.AlignBottom
            spacing: 10
            NButton {
                id: sortButton
                text: root.sortLabel(root.sortMode) + " ▾"
                bg: Theme.surface
                textColor: Theme.textMuted
                fontSize: 13
                padH: 14
                onClicked: sortMenu.popup(sortButton, 0, sortButton.height + 6)
            }
            NButton {
                text: qsTr("Shuffle")
                icon: "shuffle"
                iconColor: Theme.amber
                bg: Theme.surface
                enabled: App.library.count > 0
                onClicked: App.shuffleView()
            }
            NButton {
                text: qsTr("Play all")
                icon: "play"
                iconSize: 16
                gradient: true
                padH: 20
                enabled: App.library.count > 0
                onClicked: App.playView()
            }
            NButton {
                id: plMore
                visible: App.page === "playlist"
                bg: Theme.surface
                icon: "more"
                tooltip: qsTr("Playlist options")
                onClicked: root.playlistOptionsRequested(App.playlistId, App.playlistName, plMore)
            }
        }
    }

    NMenu {
        id: sortMenu
        Repeater {
            model: ["recent", "title", "artist", "duration"]
            delegate: NMenuItem {
                required property string modelData
                text: root.sortLabel(modelData)
                checkable: true
                checked: root.sortMode === modelData
                onTriggered: App.setSort(modelData)
            }
        }
    }

    // Table
    ColumnLayout {
        Layout.fillWidth: true
        Layout.fillHeight: true
        spacing: 2
        visible: App.library.count > 0

        Item {
            Layout.fillWidth: true
            implicitHeight: 30
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                anchors.bottomMargin: 10
                spacing: 12
                component HeaderText: Text {
                    color: Theme.textMuted
                    font.pixelSize: 11
                    font.weight: Font.ExtraBold
                    font.letterSpacing: 1.1
                    elide: Text.ElideRight
                }
                HeaderText { Layout.preferredWidth: 40; text: "#" }
                HeaderText {
                    Layout.fillWidth: true; Layout.horizontalStretchFactor: 3; Layout.preferredWidth: 1
                    text: qsTr("TITLE")
                }
                HeaderText {
                    visible: !root.compact
                    Layout.fillWidth: true; Layout.horizontalStretchFactor: 2; Layout.preferredWidth: 1
                    text: qsTr("PLAYLIST")
                }
                HeaderText { visible: !root.compact; Layout.preferredWidth: 120; text: qsTr("ADDED") }
                HeaderText { Layout.preferredWidth: 70; horizontalAlignment: Text.AlignRight; text: qsTr("DURATION") }
                Item { Layout.preferredWidth: 40 }
            }
            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: 1
                color: Theme.elevated
            }
        }

        ListView {
            id: list
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.topMargin: 4
            clip: true
            spacing: 2
            reuseItems: true
            model: App.library
            boundsBehavior: Flickable.StopAtBounds
            cacheBuffer: 600
            ScrollBar.vertical: NScrollBar {}
            delegate: TrackRow {
                width: list.width - 10
                compact: root.compact
                menuHost: root.menuHost
                dragLayer: root.dragLayer
            }
        }
    }

    // Empty state
    Item {
        visible: App.library.count === 0
        Layout.fillWidth: true
        Layout.fillHeight: true

    Column {
        anchors.centerIn: parent
        width: Math.min(480, parent.width - 40)
        spacing: 14
        GradientRect {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 88; height: 88; radius: 28
            Icon { anchors.centerIn: parent; name: App.page === "favorites" ? "heart" : "moon-wave"; size: 44 }
        }
        Text {
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.Wrap
            text: App.searchText !== "" ? qsTr("Nothing matches “%1”").arg(App.searchText)
                : App.page === "favorites" ? qsTr("No favorites yet")
                : App.page === "playlist" ? qsTr("This playlist is empty")
                : qsTr("Your library is empty")
            color: Theme.text
            font.pixelSize: 20
            font.weight: Font.ExtraBold
        }
        Text {
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.Wrap
            text: App.searchText !== "" ? qsTr("Try another title or artist.")
                : App.page === "favorites" ? qsTr("Tap the heart on any song to keep it here.")
                : App.page === "playlist" ? qsTr("Drag songs from the library onto this playlist in the sidebar.")
                : qsTr("Paste a YouTube link above (or press Ctrl+V) to download songs. Everything plays offline afterwards.")
            color: Theme.textMuted
            font.pixelSize: 14
        }
        Item { width: 1; height: 4 }
        NButton {
            anchors.horizontalCenter: parent.horizontalCenter
            visible: App.page === "library" && App.searchText === ""
            text: qsTr("Paste link from clipboard")
            icon: "link"
            gradient: true
            onClicked: App.pasteLink()
        }
    }
    }
}
