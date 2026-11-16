import QtQuick
import QtQuick.Layouts

RowLayout {
    id: root
    spacing: 12

    function focusSearch() { search.forceActiveFocus(); search.selectAll() }
    function focusLink() { link.focusField() }

    LinkField {
        id: link
        Layout.fillWidth: true
        Layout.horizontalStretchFactor: 3
        Layout.minimumWidth: 300
        onSubmitted: (t) => { if (App.submitLink(t)) link.text = "" }
    }

    Rectangle {
        Layout.fillWidth: true
        Layout.horizontalStretchFactor: 1
        Layout.minimumWidth: 200
        Layout.maximumWidth: 420
        implicitHeight: 52
        color: Theme.surface
        radius: Theme.rInput
        border.width: search.activeFocus ? 1 : 0
        border.color: "#553B6CF6"
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 16
            anchors.rightMargin: 10
            spacing: 8
            Icon { name: "search"; size: 18; color: Theme.textMuted }
            NTextField {
                id: search
                Layout.fillWidth: true
                Layout.fillHeight: true
                placeholderText: qsTr("Search the library")
                text: App.searchText
                onTextEdited: App.setSearch(text)
                Accessible.name: qsTr("Search the library")
                Keys.onEscapePressed: { App.setSearch(""); search.focus = false }
            }
            NButton {
                visible: search.text !== ""
                implicitHeight: 28; implicitWidth: 28; radius: 9
                icon: "close"; iconSize: 14; iconColor: Theme.textMuted
                tooltip: qsTr("Clear search")
                onClicked: App.setSearch("")
            }
        }
    }
}
