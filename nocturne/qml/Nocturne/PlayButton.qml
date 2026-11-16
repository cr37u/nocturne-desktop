import QtQuick
import QtQuick.Effects

// White circular play/pause button with purple glow and icon cross-fade.
Item {
    id: root
    property bool playing: false
    property real size: 52
    property real iconSize: size * 0.38
    property color iconColor: Theme.onWhite
    property bool glow: true
    property real glowBlur: 0.9
    property color circleColor: Theme.text
    signal clicked()

    width: size
    height: size
    scale: mouse.pressed ? 0.94 : (mouse.containsMouse ? 1.04 : 1.0)
    Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutQuad } }

    Accessible.role: Accessible.Button
    Accessible.name: playing ? qsTr("Pause") : qsTr("Play")
    Accessible.onPressAction: root.clicked()

    Rectangle {
        id: circle
        anchors.fill: parent
        radius: width / 2
        color: root.circleColor
        visible: !root.glow
    }
    MultiEffect {
        source: circle
        anchors.fill: circle
        visible: root.glow
        shadowEnabled: true
        shadowColor: "#8C7C3AED"
        shadowBlur: root.glowBlur
        shadowHorizontalOffset: 0
        shadowVerticalOffset: 0
        shadowScale: 1.12
    }

    Icon {
        anchors.centerIn: parent
        name: "pause"
        size: root.iconSize
        color: root.iconColor
        opacity: root.playing ? 1 : 0
        scale: root.playing ? 1 : 0.7
        Behavior on opacity { NumberAnimation { duration: Theme.fast } }
        Behavior on scale { NumberAnimation { duration: Theme.fast; easing.type: Easing.OutBack } }
    }
    Icon {
        anchors.centerIn: parent
        anchors.horizontalCenterOffset: root.size * 0.03
        name: "play"
        size: root.iconSize
        color: root.iconColor
        opacity: root.playing ? 0 : 1
        scale: root.playing ? 0.7 : 1
        Behavior on opacity { NumberAnimation { duration: Theme.fast } }
        Behavior on scale { NumberAnimation { duration: Theme.fast; easing.type: Easing.OutBack } }
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
    NToolTip {
        visible: mouse.containsMouse
        text: root.playing ? qsTr("Pause (Space)") : qsTr("Play (Space)")
    }
}
