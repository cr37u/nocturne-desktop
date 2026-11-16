import QtQuick
import QtQuick.Controls.Basic

Menu {
    id: menu
    padding: 6
    implicitWidth: Math.min(320, Math.max(220, contentItem.implicitWidth + leftPadding + rightPadding))
    delegate: NMenuItem {}
    background: Rectangle {
        implicitWidth: 220
        color: Theme.elevated
        radius: 14
        border.color: Theme.track
        border.width: 1
    }
    enter: Transition {
        NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 140 }
        NumberAnimation { property: "scale"; from: 0.96; to: 1; duration: 140; easing.type: Easing.OutQuad }
    }
    exit: Transition {
        NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 100 }
    }
}
