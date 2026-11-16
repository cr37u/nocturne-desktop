import QtQuick
import QtQuick.Controls.Basic

ScrollBar {
    id: bar
    policy: ScrollBar.AsNeeded
    minimumSize: 0.08
    contentItem: Rectangle {
        implicitWidth: 6
        radius: 3
        color: bar.pressed ? Theme.textMuted : Theme.track
        opacity: bar.active || bar.hovered ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.normal } }
    }
    background: Item {}
}
