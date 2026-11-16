import QtQuick
import QtQuick.Controls.Basic

MenuItem {
    id: item
    property string iconName: ""
    property color tint: Theme.text
    implicitHeight: 38
    implicitWidth: Math.max(200, row.implicitWidth + 28 + (subMenu ? 20 : 0))
    leftPadding: 10
    rightPadding: 10

    contentItem: Item {
        Row {
            id: row
            anchors.verticalCenter: parent.verticalCenter
            spacing: 10
            Icon {
                name: item.checkable ? (item.checked ? "check" : "") : item.iconName
                size: 16
                color: item.checkable ? Theme.amber : item.tint
                anchors.verticalCenter: parent.verticalCenter
                visible: true
                width: 16
            }
            Text {
                text: item.text
                color: item.enabled ? item.tint : Theme.textMuted
                font.pixelSize: 13
                font.weight: Font.DemiBold
                elide: Text.ElideRight
                width: Math.min(implicitWidth, 260)
                anchors.verticalCenter: parent.verticalCenter
            }
        }
        Icon {
            visible: item.subMenu !== null
            name: "chevron-right"
            size: 14
            color: Theme.textMuted
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
        }
    }
    arrow: Item {}
    indicator: Item {}
    background: Rectangle {
        radius: 10
        color: item.highlighted ? Theme.track : "transparent"
        Behavior on color { ColorAnimation { duration: 120 } }
    }
}
