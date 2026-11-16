import QtQuick
import QtQuick.Layouts

// Radio card: selected = 1.5px #3B6CF6 border + amber check.
Rectangle {
    id: root
    property string title: ""
    property string subtitle: ""
    property string chip: ""
    property bool selected: false
    signal clicked()

    implicitHeight: 64
    implicitWidth: 200
    radius: 16
    color: mouse.containsMouse ? Theme.elevated : Theme.surface
    border.width: selected ? 1.5 : 1
    border.color: selected ? Theme.selection : Theme.elevated
    activeFocusOnTab: true
    Behavior on color { ColorAnimation { duration: Theme.fast } }
    scale: mouse.pressed ? 0.98 : 1
    Behavior on scale { NumberAnimation { duration: 120 } }

    Accessible.role: Accessible.RadioButton
    Accessible.name: title
    Accessible.checked: selected
    Accessible.onPressAction: root.clicked()
    Keys.onSpacePressed: (e) => { root.clicked(); e.accepted = true }
    Keys.onReturnPressed: root.clicked()

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        spacing: 12
        Rectangle {
            visible: root.chip !== ""
            Layout.preferredHeight: 26
            Layout.preferredWidth: Math.max(36, chipText.implicitWidth + 14)
            radius: 8
            color: root.selected ? "#333B6CF6" : Theme.elevated
            Text {
                id: chipText
                anchors.centerIn: parent
                text: root.chip
                color: root.selected ? Theme.text : Theme.textMuted
                font.pixelSize: 11
                font.weight: Font.ExtraBold
                font.letterSpacing: 0.8
            }
        }
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 1
            Text {
                Layout.fillWidth: true
                text: root.title
                color: Theme.text
                font.pixelSize: 15
                font.weight: Font.Bold
                elide: Text.ElideRight
            }
            Text {
                Layout.fillWidth: true
                visible: root.subtitle !== ""
                text: root.subtitle
                color: Theme.textMuted
                font.pixelSize: 12
                elide: Text.ElideRight
            }
        }
        Rectangle {
            Layout.preferredWidth: 22
            Layout.preferredHeight: 22
            radius: 11
            color: root.selected ? Theme.amber : "transparent"
            border.width: root.selected ? 0 : 1.5
            border.color: Theme.track
            Icon { anchors.centerIn: parent; visible: root.selected; name: "check"; size: 14; color: Theme.bg }
        }
    }
    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
