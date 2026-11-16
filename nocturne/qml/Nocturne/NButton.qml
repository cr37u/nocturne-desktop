import QtQuick

// Generic button: icon and/or text, flat / filled / gradient, press scale 0.94.
FocusScope {
    id: root
    property string text: ""
    property string icon: ""
    property real iconSize: 18
    property color iconColor: textColor
    property color textColor: Theme.text
    property int fontSize: 14
    property int fontWeight: Font.Bold
    property color bg: "transparent"
    property color hoverBg: bg.a === 0 ? Theme.hover : Qt.lighter(bg, 1.25)
    property bool gradient: false
    property real radius: Theme.rButton
    property real padH: 16
    property real spacing: 8
    property string tooltip: ""
    property bool spinning: false
    property bool enabledLook: enabled
    property alias hovered: mouse.containsMouse
    property alias pressed: mouse.pressed
    property bool iconOnly: text === ""
    property int acceptedButtons: Qt.LeftButton

    signal clicked(var mouse)
    signal rightClicked(var mouse)

    implicitHeight: 44
    readonly property real _iconSpace: icon !== "" ? iconSize + spacing : 0
    implicitWidth: iconOnly ? implicitHeight : Math.ceil(_iconSpace + label.implicitWidth + padH * 2)
    opacity: enabledLook ? 1 : 0.45
    activeFocusOnTab: true

    scale: mouse.pressed ? 0.94 : 1.0
    Behavior on scale { NumberAnimation { duration: 120; easing.type: Easing.OutQuad } }

    Accessible.role: Accessible.Button
    Accessible.name: tooltip !== "" ? tooltip : text
    Accessible.onPressAction: root.clicked(null)
    Keys.onReturnPressed: root.clicked(null)
    Keys.onEnterPressed: root.clicked(null)

    Rectangle {
        anchors.fill: parent
        radius: root.radius
        visible: !root.gradient
        color: mouse.containsMouse && root.enabled ? root.hoverBg : root.bg
        Behavior on color { ColorAnimation { duration: Theme.fast } }
    }
    GradientRect {
        anchors.fill: parent
        radius: root.radius
        visible: root.gradient
    }
    Rectangle {
        anchors.fill: parent
        radius: root.radius
        visible: root.gradient
        color: "#FFFFFF"
        opacity: mouse.containsMouse ? 0.08 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.fast } }
    }
    Rectangle {
        anchors.fill: parent
        anchors.margins: -3
        radius: root.radius + 3
        color: "transparent"
        border.width: 2
        border.color: Theme.selection
        visible: root.activeFocus
        opacity: 0.9
    }

    Row {
        id: content
        anchors.centerIn: parent
        spacing: root.spacing
        Icon {
            id: ico
            name: root.icon
            size: root.iconSize
            color: root.iconColor
            anchors.verticalCenter: parent.verticalCenter
            RotationAnimation on rotation {
                from: 0; to: 360; duration: 900
                loops: Animation.Infinite
                running: root.spinning
                onStopped: ico.rotation = 0
            }
        }
        Text {
            id: label
            visible: root.text !== ""
            text: root.text
            color: root.textColor
            font.pixelSize: root.fontSize
            font.weight: root.fontWeight
            elide: Text.ElideRight
            width: Math.min(implicitWidth, Math.max(0, root.width - root.padH * 2 - root._iconSpace))
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: root.acceptedButtons | Qt.RightButton
        cursorShape: root.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: (m) => {
            if (m.button === Qt.RightButton) root.rightClicked(m)
            else root.clicked(m)
        }
    }

    NToolTip {
        visible: mouse.containsMouse && (root.tooltip !== "" || label.truncated)
        text: root.tooltip !== "" ? root.tooltip : root.text
    }
}
