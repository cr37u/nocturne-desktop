import QtQuick
import QtQuick.Controls.Basic

// Context menu for a track (right-click, "⋯" button).
NMenu {
    id: menu
    property int trackId: -1
    property string trackTitle: ""
    property bool favorite: false
    signal newPlaylistWithTrack(int trackId)
    signal deleteRequested(int trackId, string title)

    function openFor(id, title, fav, anchorItem) {
        trackId = id
        trackTitle = title
        favorite = fav
        if (anchorItem) popup(anchorItem, 0, anchorItem.height)
        else popup()
    }

    NMenuItem { text: qsTr("Play"); iconName: "play"; onTriggered: App.playFromView(menu.trackId) }
    NMenuItem { text: qsTr("Play next"); iconName: "queue"; onTriggered: Player.playNext(menu.trackId) }
    NMenuItem { text: qsTr("Add to queue"); iconName: "playlists"; onTriggered: Player.enqueue(menu.trackId) }
    NMenu {
        id: playlistMenu
        title: qsTr("Add to playlist")
        Instantiator {
            model: App.playlists
            delegate: NMenuItem {
                required property int playlistId
                required property string name
                text: name
                iconName: "music"
                onTriggered: App.addToPlaylist(menu.trackId, playlistId)
            }
            onObjectAdded: (index, object) => playlistMenu.insertItem(index, object)
            onObjectRemoved: (index, object) => playlistMenu.removeItem(object)
        }
        MenuSeparator {
            contentItem: Rectangle { implicitHeight: 1; color: Theme.track }
        }
        NMenuItem {
            text: qsTr("New playlist…")
            iconName: "plus"
            onTriggered: menu.newPlaylistWithTrack(menu.trackId)
        }
    }
    NMenuItem {
        text: qsTr("Remove from this playlist")
        iconName: "close"
        visible: App.page === "playlist"
        height: visible ? implicitHeight : 0
        onTriggered: App.removeFromCurrentPlaylist(menu.trackId)
    }
    NMenuItem {
        text: menu.favorite ? qsTr("Remove from favorites") : qsTr("Add to favorites")
        iconName: menu.favorite ? "heart-filled" : "heart"
        onTriggered: App.toggleFavorite(menu.trackId)
    }
    NMenuItem { text: qsTr("Show in folder"); iconName: "folder"; onTriggered: App.showInFolder(menu.trackId) }
    MenuSeparator {
        contentItem: Rectangle { implicitHeight: 1; color: Theme.track }
    }
    NMenuItem {
        text: qsTr("Delete from library")
        iconName: "trash"
        tint: Theme.error
        onTriggered: menu.deleteRequested(menu.trackId, menu.trackTitle)
    }
}
