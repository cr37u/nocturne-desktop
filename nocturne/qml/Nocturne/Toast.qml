import QtQuick
import QtQuick.Layouts

// Small in-app notification shown above the player bar.
Item {
    id: root
    property var queue: []
    width: Math.min(560, bubble.implicitWidth)
    height: bubble.height

    function show(message, isError) {
        queue.push({ text: message, error: isError })
        if (!timer.running && !visibleState) next()
    }
    property bool visibleState: false
    function next() {
        if (queue.length === 0) { visibleState = false; return }
        var item = queue.shift()
        label.text = item.text
        bubble.isError = item.error
        visibleState = true
        timer.restart()
    }

    Timer {
        id: timer
        interval: 3800
        onTriggered: { root.visibleState = false; gap.restart() }
    }
    Timer { id: gap; interval: 260; onTriggered: root.next() }

    opacity: visibleState ? 1 : 0
    y: visibleState ? 0 : 10
    visible: opacity > 0
    Behavior on opacity { NumberAnimation { duration: Theme.normal } }
    Behavior on y { NumberAnimation { duration: Theme.normal; easing.type: Easing.OutQuad } }

    Rectangle {
        id: bubble
        property bool isError: false
        width: root.width
        implicitWidth: row.implicitWidth + 36
        height: Math.max(48, row.implicitHeight + 24)
        radius: 16
        color: Theme.elevated
        border.width: 1
        border.color: isError ? "#66F87171" : Theme.track
        RowLayout {
            id: row
            anchors.fill: parent
            anchors.leftMargin: 18
            anchors.rightMargin: 18
            spacing: 10
            Icon {
                name: bubble.isError ? "x-circle" : "check"
                size: 18
                color: bubble.isError ? Theme.error : Theme.amber
            }
            Text {
                id: label
                Layout.fillWidth: true
                Layout.maximumWidth: 480
                color: Theme.text
                font.pixelSize: 13
                font.weight: Font.DemiBold
                wrapMode: Text.Wrap
            }
        }
        MouseArea {
            anchors.fill: parent
            onClicked: { timer.stop(); root.visibleState = false; gap.restart() }
        }
    }
}
