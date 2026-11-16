import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

ApplicationWindow {
    id: win
    visible: false
    width: 1360
    height: 860
    minimumWidth: 1000
    minimumHeight: 640
    color: Theme.bg
    title: Player.hasTrack ? Player.currentTrack.title + " — Nocturne" : "Nocturne"
    font.family: Theme.fontFamily

    onClosing: (close) => { close.accepted = App.handleCloseRequest() }

    readonly property bool showRightPanel: width >= 1180

    // ------------------------------------------------------------- keyboard
    Shortcut { sequences: ["Space"]; onActivated: Player.togglePlay() }
    Shortcut { sequences: ["Ctrl+Right"]; onActivated: Player.next() }
    Shortcut { sequences: ["Ctrl+Left"]; onActivated: Player.previous() }
    Shortcut { sequences: ["Ctrl+Up"]; onActivated: Player.changeVolume(0.05) }
    Shortcut { sequences: ["Ctrl+Down"]; onActivated: Player.changeVolume(-0.05) }
    Shortcut {
        sequences: ["Ctrl+F"]
        onActivated: {
            if (App.page !== "library" && App.page !== "favorites" && App.page !== "playlist")
                App.navigate("library")
            Qt.callLater(() => topBar.focusSearch())
        }
    }
    Shortcut { sequences: [StandardKey.Paste]; onActivated: App.pasteLink() }
    Shortcut { sequences: ["Ctrl+L"]; onActivated: App.openAddLink() }

    Connections {
        target: App
        function onToast(message, isError) { toast.show(message, isError) }
        function onFocusAddLink() {
            if (App.page === "downloads") pageLoader.item.focusLink()
            else topBar.focusLink()
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: 16
            spacing: 16

            Sidebar {
                Layout.preferredWidth: 220
                Layout.fillHeight: true
                onNewPlaylistRequested: newPlaylist(-1)
                onPlaylistMenuRequested: (id, name, anchor) => playlistMenu.openFor(id, name, anchor)
                onTracksDropped: (trackId, playlistId) => App.addToPlaylist(trackId, playlistId)
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.leftMargin: 8
                Layout.rightMargin: 8
                Layout.topMargin: 4
                spacing: 22

                TopBar {
                    id: topBar
                    Layout.fillWidth: true
                    visible: App.page !== "downloads" && App.page !== "settings"
                }

                Loader {
                    id: pageLoader
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    sourceComponent: App.page === "playlists" ? playlistsPage
                                   : App.page === "downloads" ? downloadsPage
                                   : App.page === "settings" ? settingsPage
                                   : libraryPage
                    opacity: 0
                    onLoaded: { opacity = 0; fadeIn.restart() }
                    NumberAnimation { id: fadeIn; target: pageLoader; property: "opacity"; from: 0; to: 1; duration: Theme.normal; easing.type: Easing.OutQuad }
                }
            }

            RightPanel {
                visible: win.showRightPanel
                Layout.preferredWidth: 300
                Layout.fillHeight: true
            }
        }

        PlayerBar {
            Layout.fillWidth: true
        }
    }

    Component {
        id: libraryPage
        LibraryPage {
            menuHost: trackMenu
            dragLayer: floatLayer
            onPlaylistOptionsRequested: (id, name, anchor) => playlistMenu.openFor(id, name, anchor)
        }
    }
    Component {
        id: playlistsPage
        PlaylistsPage {
            onNewPlaylistRequested: newPlaylist(-1)
            onPlaylistOptionsRequested: (id, name, anchor) => playlistMenu.openFor(id, name, anchor)
        }
    }
    Component { id: downloadsPage; DownloadsPage {} }
    Component { id: settingsPage; SettingsPage {} }

    // Items being dragged are re-parented here so they float above everything.
    Item { id: floatLayer; anchors.fill: parent; z: 1000 }

    // Links dropped from a browser.
    DropArea {
        anchors.fill: parent
        keys: ["text/uri-list", "text/plain"]
        onDropped: (drop) => {
            var t = drop.hasUrls && drop.urls.length > 0 ? drop.urls[0].toString() : drop.text
            if (t && App.submitLink(t)) drop.accept()
        }
    }

    // ------------------------------------------------------------- menus
    TrackMenu {
        id: trackMenu
        onNewPlaylistWithTrack: (trackId) => newPlaylist(trackId)
        onDeleteRequested: (trackId, title) => dialog.ask({
            title: qsTr("Delete “%1”?").arg(title),
            message: qsTr("The audio file is removed from this computer. You can download it again any time."),
            acceptText: qsTr("Delete"),
            destructive: true,
            onAccepted: function() { App.deleteTracks([trackId]) }
        })
    }

    NMenu {
        id: playlistMenu
        property int playlistId: -1
        property string playlistName: ""
        function openFor(id, name, anchor) {
            playlistId = id
            playlistName = name
            if (anchor) popup(anchor, 0, anchor.height)
            else popup()
        }
        NMenuItem { text: qsTr("Play"); iconName: "play"; onTriggered: App.playPlaylist(playlistMenu.playlistId) }
        NMenuItem { text: qsTr("Open"); iconName: "playlists"; onTriggered: App.openPlaylist(playlistMenu.playlistId) }
        NMenuItem {
            text: qsTr("Rename…")
            iconName: "edit"
            onTriggered: dialog.ask({
                title: qsTr("Rename playlist"),
                input: true,
                text: playlistMenu.playlistName,
                acceptText: qsTr("Save"),
                onAccepted: function(v) { App.renamePlaylist(playlistMenu.playlistId, v) }
            })
        }
        NMenuItem {
            text: qsTr("Delete playlist")
            iconName: "trash"
            tint: Theme.error
            onTriggered: dialog.ask({
                title: qsTr("Delete the playlist “%1”?").arg(playlistMenu.playlistName),
                message: qsTr("The songs stay in your library."),
                acceptText: qsTr("Delete"),
                destructive: true,
                onAccepted: function() { App.deletePlaylist(playlistMenu.playlistId) }
            })
        }
    }

    function newPlaylist(trackId) {
        dialog.ask({
            title: qsTr("New playlist"),
            input: true,
            placeholder: qsTr("Playlist name"),
            acceptText: qsTr("Create"),
            onAccepted: function(v) {
                if (trackId >= 0) App.createPlaylistWithTrack(v, trackId)
                else App.createPlaylist(v)
            }
        })
    }

    NDialog { id: dialog }

    Item {
        z: 2000
        width: toast.width
        height: toast.height
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 120
        Toast { id: toast }
    }
}
