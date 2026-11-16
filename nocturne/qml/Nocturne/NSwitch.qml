import QtQuick

// Toggle switch: amber when ON (accent only for active states).
Item {
    id: root
    property bool checked: false
    signal toggled(bool checked)
    implicitWidth: 44
    implicitHeight: 26
    activeFocusOnTab: true

    Accessible.role: Accessible.CheckBox
    Accessible.checkable: true
    Accessible.checked: checked
    Accessible.onToggleAction: root.toggled(!root.checked)
    Keys.onSpacePressed: (e) => { root.toggled(!root.checked); e.accepted = true }

    Rectangle {
        anchors.fill: parent
        radius: height / 2
        color: root.checked ? Theme.amber : Theme.track
        Behavior on color { ColorAnimation { duration: Theme.fast } }
        border.width: root.activeFocus ? 2 : 0
        border.color: Theme.selection
    }
    Rectangle {
        width: parent.height - 6
        height: width
        radius: width / 2
        y: 3
        x: root.checked ? parent.width - width - 3 : 3
        color: root.checked ? Theme.bg : Theme.text
        Behavior on x { NumberAnimation { duration: Theme.fast; easing.type: Easing.OutQuad } }
    }
    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: root.toggled(!root.checked)
    }
}
