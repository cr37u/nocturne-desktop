import QtQuick
import QtQuick.Layouts

// "Lipește un link YouTube…" field with the gradient "Descarcă" button.
Rectangle {
    id: root
    property alias text: field.text
    property string buttonText: qsTr("Download")
    property string buttonIcon: "download"
    property bool busy: Downloads.analyzing
    signal submitted(string text)

    function focusField() { field.forceActiveFocus(); field.selectAll() }
    function submit() {
        if (field.text.trim() === "") { App.pasteLink(); return }
        root.submitted(field.text.trim())
    }

    color: Theme.surface
    radius: Theme.rInput
    implicitHeight: 52
    border.width: field.activeFocus ? 1 : 0
    border.color: "#553B6CF6"

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 16
        anchors.rightMargin: 6
        anchors.topMargin: 6
        anchors.bottomMargin: 6
        spacing: 8
        Icon { name: "link"; size: 18; color: Theme.textMuted }
        NTextField {
            id: field
            Layout.fillWidth: true
            Layout.fillHeight: true
            placeholderText: qsTr("Paste a YouTube link (video or playlist)…  Ctrl+V")
            onAccepted: root.submit()
            Accessible.name: qsTr("YouTube link")
        }
        NButton {
            Layout.preferredHeight: 40
            gradient: true
            text: root.buttonText
            icon: root.busy ? "refresh" : root.buttonIcon
            spinning: root.busy
            padH: 18
            onClicked: root.submit()
        }
    }
}
