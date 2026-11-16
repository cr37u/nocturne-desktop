import QtQuick

Item {
    id: root
    property string icon: ""
    property string text: ""
    property bool active: false
    property int badge: 0
    property real itemHeight: 44
    signal clicked()

    height: itemHeight
    activeFocusOnTab: true
    Accessible.role: Accessible.Button
    Accessible.name: text
    Accessible.onPressAction: root.clicked()
    Keys.onReturnPressed: root.clicked()

    scale: mouse.pressed ? 0.97 : 1
    Behavior on scale { NumberAnimation { duration: 120 } }

    Rectangle {
        anchors.fill: parent
        radius: Theme.rButton
        color: root.active ? Theme.elevated : (mouse.containsMouse ? Theme.hover : "transparent")
        border.width: root.activeFocus ? 2 : 0
        border.color: Theme.selection
        Behavior on color { ColorAnimation { duration: Theme.fast } }
    }
    Row {
        anchors.left: parent.left
        anchors.leftMargin: 12
        anchors.right: badgeRect.visible ? badgeRect.left : parent.right
        anchors.rightMargin: 8
        anchors.verticalCenter: parent.verticalCenter
        spacing: 12
        Icon {
            name: root.icon
            size: 20
            color: root.active ? Theme.amber : (mouse.containsMouse ? Theme.text : Theme.textMuted)
            anchors.verticalCenter: parent.verticalCenter
        }
        Text {
            id: label
            text: root.text
            color: root.active || mouse.containsMouse ? Theme.text : Theme.textMuted
            font.pixelSize: 14
            font.weight: root.active ? Font.Bold : Font.DemiBold
            elide: Text.ElideRight
            width: Math.max(0, parent.width - 32)
            anchors.verticalCenter: parent.verticalCenter
            Behavior on color { ColorAnimation { duration: Theme.fast } }
        }
    }
    Rectangle {
        id: badgeRect
        visible: root.badge > 0
        anchors.right: parent.right
        anchors.rightMargin: 12
        anchors.verticalCenter: parent.verticalCenter
        height: 22
        width: Math.max(22, badgeText.implicitWidth + 12)
        radius: 11
        color: Theme.amber
        Text {
            id: badgeText
            anchors.centerIn: parent
            text: root.badge > 99 ? "99+" : root.badge
            color: Theme.bg
            font.pixelSize: 12
            font.weight: Font.ExtraBold
        }
    }
    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
    NToolTip { visible: mouse.containsMouse && label.truncated; text: root.text }
}
