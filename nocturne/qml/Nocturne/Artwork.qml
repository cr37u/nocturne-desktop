import QtQuick
import QtQuick.Effects

// Track artwork with rounded corners; gradient + icon placeholder when there is no image.
Item {
    id: root
    property string source: ""
    property real radius: 11
    property int seed: 0
    property string placeholderIcon: "music"
    property real iconSize: Math.max(14, Math.min(width, height) * 0.4)
    property color iconColor: Theme.text
    property bool insetLine: false
    property var colors: Theme.art(seed)

    readonly property bool hasImage: img.status === Image.Ready && source !== ""

    GradientRect {
        anchors.fill: parent
        radius: root.radius
        startColor: root.colors[0]
        endColor: root.colors[1]
        visible: !root.hasImage
    }
    Icon {
        anchors.centerIn: parent
        name: root.placeholderIcon
        size: root.iconSize
        color: root.iconColor
        visible: !root.hasImage
    }

    Image {
        id: img
        anchors.fill: parent
        source: root.source
        visible: false
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        cache: true
        sourceSize: Qt.size(Math.ceil(root.width * Screen.devicePixelRatio), Math.ceil(root.height * Screen.devicePixelRatio))
    }
    Item {
        id: mask
        anchors.fill: parent
        visible: false
        layer.enabled: true
        Rectangle { anchors.fill: parent; radius: root.radius; color: "black" }
    }
    MultiEffect {
        anchors.fill: parent
        source: img
        visible: root.hasImage
        maskEnabled: true
        maskSource: mask
        maskThresholdMin: 0.5
        maskSpreadAtMin: 1.0
    }
    Rectangle {
        anchors.fill: parent
        radius: root.radius
        color: "transparent"
        border.width: root.insetLine ? 1 : 0
        border.color: Theme.glassLine
    }
}
