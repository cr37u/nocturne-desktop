import QtQuick
import QtQuick.Controls.Basic

ToolTip {
    id: tip
    delay: 550
    timeout: 6000
    padding: 8
    leftPadding: 10
    rightPadding: 10
    contentItem: Text {
        text: tip.text
        color: Theme.text
        font.pixelSize: 12
        font.weight: Font.DemiBold
        wrapMode: Text.Wrap
    }
    background: Rectangle {
        color: Theme.elevated
        radius: 10
        border.color: Theme.track
        border.width: 1
    }
}
