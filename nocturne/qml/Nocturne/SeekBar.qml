import QtQuick

// Thin progress / seek bar. Emits `moved` while dragging and `committed` on release.
Item {
    id: root
    property real value: 0              // 0..1
    property real barHeight: 5
    property color trackColor: Theme.track
    property bool gradientFill: true
    property color fillColor: Theme.textOnGradient
    property bool showThumb: true
    property bool thumbOnHover: false
    property real thumbSize: 13
    property bool interactive: true
    property real wheelStep: 0.05
    readonly property bool dragging: mouse.pressed
    property real dragValue: 0
    readonly property real shown: dragging ? dragValue : Math.max(0, Math.min(1, value))

    signal moved(real v)
    signal committed(real v)

    implicitHeight: Math.max(thumbSize, barHeight) + 8
    implicitWidth: 200

    Accessible.role: Accessible.Slider

    Rectangle {
        id: bar
        anchors.verticalCenter: parent.verticalCenter
        width: parent.width
        height: root.barHeight
        radius: height / 2
        color: root.trackColor
    }
    Item {
        anchors.left: bar.left
        anchors.verticalCenter: bar.verticalCenter
        height: bar.height
        width: Math.max(root.barHeight, bar.width * root.shown)
        visible: root.shown > 0
        clip: true
        Rectangle {
            width: bar.width
            height: bar.height
            radius: bar.radius
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0; color: root.gradientFill ? Theme.brightStart : root.fillColor }
                GradientStop { position: 1; color: root.gradientFill ? Theme.brightEnd : root.fillColor }
            }
        }
        Behavior on width {
            enabled: !root.dragging
            NumberAnimation { duration: 180; easing.type: Easing.OutQuad }
        }
    }
    Rectangle {
        visible: root.showThumb && root.interactive
        opacity: !root.thumbOnHover || mouse.containsMouse || root.dragging ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.fast } }
        width: root.thumbSize
        height: root.thumbSize
        radius: width / 2
        color: Theme.text
        x: bar.width * root.shown - width / 2
        anchors.verticalCenter: bar.verticalCenter
        scale: root.dragging ? 1.15 : 1
        Behavior on scale { NumberAnimation { duration: 120 } }
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        anchors.topMargin: -6
        anchors.bottomMargin: -6
        enabled: root.interactive
        hoverEnabled: true
        cursorShape: root.interactive ? Qt.PointingHandCursor : Qt.ArrowCursor
        preventStealing: true
        function valueAt(x) { return Math.max(0, Math.min(1, x / Math.max(1, bar.width))) }
        onPressed: (m) => { root.dragValue = valueAt(m.x); root.moved(root.dragValue) }
        onPositionChanged: (m) => { if (pressed) { root.dragValue = valueAt(m.x); root.moved(root.dragValue) } }
        onReleased: (m) => { root.dragValue = valueAt(m.x); root.committed(root.dragValue) }
        onWheel: (w) => {
            var v = Math.max(0, Math.min(1, root.value + (w.angleDelta.y > 0 ? root.wheelStep : -root.wheelStep)))
            root.committed(v)
        }
    }
}
