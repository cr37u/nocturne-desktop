import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Effects
import QtQuick.Layouts
import QtQuick.Window

// Desktop widget: large card 360×140 or compact pill 300×60. Frameless, translucent, draggable.
Window {
    id: widget
    readonly property real m: 24
    readonly property bool compact: AppSettings.widgetCompact
    readonly property bool pinned: AppSettings.widgetPinned
    readonly property bool onTop: AppSettings.widgetOnTop && !pinned
    readonly property real cardW: compact ? 300 : 360
    readonly property real cardH: compact ? 60 : 140
    readonly property var track: Player.currentTrack

    width: cardW + m * 2
    height: cardH + m * 2
    color: "transparent"
    title: qsTr("Nocturne widget")
    flags: Qt.Tool | Qt.FramelessWindowHint
           | (onTop ? Qt.WindowStaysOnTopHint : 0)
           | (pinned ? Qt.WindowStaysOnBottomHint : 0)
    visible: AppSettings.widgetVisible

    onClosing: (close) => { AppSettings.widgetVisible = false }
    onVisibleChanged: if (visible) placeWindow()
    onFlagsChanged: if (AppSettings.widgetVisible && !visible) Qt.callLater(() => widget.visible = true)

    function placeWindow() {
        var sx = AppSettings.widgetX, sy = AppSettings.widgetY
        if (sx > -10000 && sy > -10000) { x = sx; y = sy; return }
        x = Screen.virtualX + Screen.desktopAvailableWidth - width - 24
        y = Screen.virtualY + 24
    }
    Timer {
        id: saveTimer
        interval: 400
        onTriggered: { AppSettings.widgetX = widget.x; AppSettings.widgetY = widget.y }
    }
    onXChanged: if (visible) saveTimer.restart()
    onYChanged: if (visible) saveTimer.restart()

    // Shadow
    Rectangle {
        id: shadowSource
        x: widget.m; y: widget.m
        width: widget.cardW; height: widget.cardH
        radius: widget.compact ? 30 : Theme.rPanel
        color: "#000000"
        visible: false
    }
    MultiEffect {
        source: shadowSource
        anchors.fill: shadowSource
        shadowEnabled: true
        shadowColor: "#8C000000"
        shadowBlur: 0.9
        shadowVerticalOffset: 10
    }

    Item {
        id: card
        x: widget.m; y: widget.m
        width: widget.cardW; height: widget.cardH

        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton | Qt.RightButton
            onPressed: (m) => { if (m.button === Qt.LeftButton) widget.startSystemMove() }
            onClicked: (m) => { if (m.button === Qt.RightButton) menu.popup() }
            onDoubleClicked: App.showMainWindow()
        }

        // ---------------------------------------------------------- large
        GradientRect {
            anchors.fill: parent
            visible: !widget.compact
            radius: Theme.rPanel
            startColor: "#E01E40AF"     // rgba(30,64,175,0.88)
            endColor: "#EB3B0764"       // rgba(59,7,100,0.92)
            borderColor: "#1AF1F1F7"
            borderWidth: 1
        }
        RowLayout {
            anchors.fill: parent
            anchors.margins: 14
            spacing: 14
            visible: !widget.compact

            Artwork {
                Layout.preferredWidth: 112
                Layout.preferredHeight: 112
                radius: 16
                source: widget.track.artwork || ""
                colors: [Theme.artStart, Theme.artEnd]
                placeholderIcon: "moon"
                iconSize: 48
                iconColor: "#D9F1F1F7"
                insetLine: true
            }
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 0
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 6
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Text {
                            Layout.fillWidth: true
                            text: Player.hasTrack ? (widget.track.title || "") : qsTr("Nothing playing")
                            color: Theme.text
                            font.pixelSize: 15
                            font.weight: Font.ExtraBold
                            elide: Text.ElideRight
                        }
                        Text {
                            Layout.fillWidth: true
                            text: Player.hasTrack ? (widget.track.artist || "") : "Nocturne"
                            color: Theme.textOnGradient
                            font.pixelSize: 12
                            elide: Text.ElideRight
                        }
                    }
                    NButton {
                        id: moreBtn
                        Layout.alignment: Qt.AlignTop
                        implicitWidth: 28; implicitHeight: 28; radius: 8
                        icon: "more"; iconSize: 18; iconColor: Theme.textOnGradient
                        hoverBg: "#1FF1F1F7"
                        tooltip: qsTr("Widget options")
                        onClicked: menu.popup(moreBtn, 0, moreBtn.height)
                    }
                }
                Item { Layout.fillHeight: true }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Text {
                        text: Fmt.durationMs(Player.position)
                        color: Theme.textOnGradient
                        font.pixelSize: 11
                        font.weight: Font.DemiBold
                    }
                    SeekBar {
                        Layout.fillWidth: true
                        barHeight: 4
                        thumbSize: 10
                        thumbOnHover: true
                        gradientFill: false
                        fillColor: Theme.text
                        trackColor: "#38F1F1F7"
                        value: Player.duration > 0 ? Player.position / Player.duration : 0
                        interactive: Player.hasTrack
                        onCommitted: (v) => Player.seek(Math.round(v * Player.duration))
                    }
                    Text {
                        text: Fmt.durationMs(Player.duration)
                        color: Theme.textOnGradient
                        font.pixelSize: 11
                        font.weight: Font.DemiBold
                    }
                }
                Item { Layout.fillHeight: true }
                RowLayout {
                    Layout.fillWidth: true
                    NButton {
                        implicitWidth: 36; implicitHeight: 36; radius: 18
                        icon: "previous"; iconSize: 18
                        hoverBg: "#1FF1F1F7"
                        tooltip: qsTr("Previous")
                        onClicked: Player.previous()
                    }
                    Item { Layout.fillWidth: true }
                    PlayButton {
                        size: 44
                        playing: Player.playing
                        glowBlur: 0.7
                        onClicked: Player.togglePlay()
                    }
                    Item { Layout.fillWidth: true }
                    NButton {
                        implicitWidth: 36; implicitHeight: 36; radius: 18
                        icon: "next"; iconSize: 18
                        hoverBg: "#1FF1F1F7"
                        tooltip: qsTr("Next")
                        onClicked: Player.next()
                    }
                }
            }
        }

        // ---------------------------------------------------------- pill
        Rectangle {
            anchors.fill: parent
            visible: widget.compact
            radius: 30
            color: "#E0161630"
            border.width: 1
            border.color: "#737C3AED"
        }
        RowLayout {
            anchors.fill: parent
            anchors.margins: 8
            spacing: 10
            visible: widget.compact
            Artwork {
                Layout.preferredWidth: 44
                Layout.preferredHeight: 44
                radius: 22
                source: widget.track.artwork || ""
                colors: [Theme.gradStart, Theme.gradEnd]
                placeholderIcon: "moon"
                iconSize: 18
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 0
                Text {
                    Layout.fillWidth: true
                    text: Player.hasTrack ? (widget.track.title || "") : qsTr("Nothing playing")
                    color: Theme.text
                    font.pixelSize: 13
                    font.weight: Font.ExtraBold
                    elide: Text.ElideRight
                }
                Text {
                    Layout.fillWidth: true
                    text: Player.hasTrack ? (widget.track.artist || "") : "Nocturne"
                    color: Theme.textMuted
                    font.pixelSize: 11
                    elide: Text.ElideRight
                }
            }
            PlayButton {
                size: 40
                playing: Player.playing
                glow: false
                onClicked: Player.togglePlay()
            }
            NButton {
                implicitWidth: 40; implicitHeight: 40; radius: 20
                icon: "next"; iconSize: 18
                hoverBg: "#1FF1F1F7"
                tooltip: qsTr("Next")
                onClicked: Player.next()
            }
        }
    }

    NMenu {
        id: menu
        popupType: Popup.Window
        NMenuItem {
            text: widget.compact ? qsTr("Large size") : qsTr("Compact size")
            iconName: "resize"
            onTriggered: AppSettings.widgetCompact = !AppSettings.widgetCompact
        }
        NMenuItem {
            text: qsTr("Always on top")
            checkable: true
            checked: AppSettings.widgetOnTop && !AppSettings.widgetPinned
            onTriggered: {
                AppSettings.widgetPinned = false
                AppSettings.widgetOnTop = !AppSettings.widgetOnTop
            }
        }
        NMenuItem {
            text: qsTr("Pin to desktop")
            checkable: true
            checked: AppSettings.widgetPinned
            onTriggered: AppSettings.widgetPinned = !AppSettings.widgetPinned
        }
        NMenuItem {
            text: qsTr("Open Nocturne")
            iconName: "window"
            onTriggered: App.showMainWindow()
        }
        NMenuItem {
            text: qsTr("Hide widget")
            iconName: "eye-off"
            onTriggered: AppSettings.widgetVisible = false
        }
    }
}
