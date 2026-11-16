import QtQuick
import QtQuick.Shapes

// Rounded rectangle with a CSS-style angled linear gradient (e.g. 135deg, 170deg).
Item {
    id: root
    property real radius: 0
    property real angle: 135
    property color startColor: Theme.gradStart
    property color endColor: Theme.gradEnd
    property color midColor: Qt.rgba((startColor.r + endColor.r) / 2, (startColor.g + endColor.g) / 2,
                                     (startColor.b + endColor.b) / 2, (startColor.a + endColor.a) / 2)
    property real midPosition: 0.5
    property color borderColor: "transparent"
    property real borderWidth: 0

    readonly property real _rad: angle * Math.PI / 180
    readonly property real _dx: Math.sin(_rad)
    readonly property real _dy: -Math.cos(_rad)
    readonly property real _len: Math.abs(width * _dx) + Math.abs(height * _dy)

    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeWidth: root.borderWidth > 0 ? root.borderWidth : -1
            strokeColor: root.borderColor
            fillGradient: LinearGradient {
                x1: root.width / 2 - root._dx * root._len / 2
                y1: root.height / 2 - root._dy * root._len / 2
                x2: root.width / 2 + root._dx * root._len / 2
                y2: root.height / 2 + root._dy * root._len / 2
                GradientStop { position: 0; color: root.startColor }
                GradientStop { position: root.midPosition; color: root.midColor }
                GradientStop { position: 1; color: root.endColor }
            }
            PathRectangle {
                x: root.borderWidth / 2
                y: root.borderWidth / 2
                width: root.width - root.borderWidth
                height: root.height - root.borderWidth
                radius: Math.max(0, root.radius - root.borderWidth / 2)
            }
        }
    }
}
