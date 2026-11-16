import QtQuick
import QtQml.Models
import QtQuick.Controls.Basic

// "UrmeazÄƒ": upcoming tracks with drag handles (reorder), double-click to play, remove on hover.
ListView {
    id: list
    clip: true
    spacing: 0
    boundsBehavior: Flickable.StopAtBounds
    ScrollBar.vertical: NScrollBar {}

    displaced: Transition { NumberAnimation { properties: "y"; duration: 180; easing.type: Easing.OutQuad } }

    model: DelegateModel {
        id: visualModel
        model: Player.queue
        delegate: DropArea {
            id: slot
            required property int index
            required property int trackId
            required property string title
            required property string artist
            required property real duration
            required property string artwork
            required property int colorSeed
            required property int queueIndex
            readonly property int visualIndex: DelegateModel.itemsIndex

            width: list.width - 6
            height: 54
            keys: ["nocturne/queue"]
            onEntered: (drag) => {
                if (drag.source && drag.source.visualIndex !== undefined && drag.source.visualIndex !== slot.visualIndex)
                    visualModel.items.move(drag.source.visualIndex, slot.visualIndex)
            }

            Item {
                id: content
                readonly property int visualIndex: slot.visualIndex
                width: slot.width
                height: slot.height
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.verticalCenter: parent.verticalCenter

                HoverHandler { id: rowHover }
                Drag.active: handle.drag.active
                Drag.source: content
                Drag.keys: ["nocturne/queue"]
                Drag.hotSpot.x: 20
                Drag.hotSpot.y: height / 2

                states: State {
                    when: handle.drag.active
                    ParentChange { target: content; parent: list }
                    AnchorChanges {
                        target: content
                        anchors.horizontalCenter: undefined
                        anchors.verticalCenter: undefined
                    }
                }

                Rectangle {
                    anchors.fill: parent
                    radius: 12
                    color: handle.drag.active ? Theme.elevated : (rowHover.hovered ? Theme.hover : "transparent")
                    border.width: handle.drag.active ? 1 : 0
                    border.color: Theme.brightEnd
                }

                Row {
                    anchors.fill: parent
                    anchors.leftMargin: 2
                    anchors.rightMargin: 4
                    spacing: 10

                    Item {
                        width: 18
                        height: parent.height
                        Icon {
                            anchors.centerIn: parent
                            name: "grip"; size: 16
                            color: handle.containsMouse || handle.drag.active ? Theme.text : Theme.textMuted
                        }
                        MouseArea {
                            id: handle
                            anchors.fill: parent
                            anchors.margins: -4
                            hoverEnabled: true
                            cursorShape: drag.active ? Qt.ClosedHandCursor : Qt.OpenHandCursor
                            drag.target: content
                            drag.axis: Drag.YAxis
                            onReleased: {
                                var from = slot.queueIndex
                                var to = (slot.queueIndex - slot.index) + content.visualIndex
                                content.Drag.drop()
                                if (from !== to) Player.moveInQueue(from, to)
                            }
                        }
                    }
                    Artwork {
                        width: 34; height: 34; radius: 10
                        anchors.verticalCenter: parent.verticalCenter
                        source: slot.artwork
                        seed: slot.colorSeed
                        iconSize: 14
                    }
                    Column {
                        width: parent.width - 18 - 34 - durText.width - 40
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 1
                        Text {
                            width: parent.width
                            text: slot.title
                            color: Theme.text
                            font.pixelSize: 13
                            font.weight: Font.Bold
                            elide: Text.ElideRight
                        }
                        Text {
                            width: parent.width
                            text: slot.artist
                            color: Theme.textMuted
                            font.pixelSize: 12
                            elide: Text.ElideRight
                        }
                    }
                    Item {
                        width: durText.width
                        height: parent.height
                        Text {
                            id: durText
                            anchors.verticalCenter: parent.verticalCenter
                            visible: !removeBtn.visible
                            text: Fmt.duration(slot.duration)
                            color: Theme.textMuted
                            font.pixelSize: 12
                        }
                        NButton {
                            id: removeBtn
                            visible: rowHover.hovered
                            anchors.centerIn: parent
                            implicitWidth: 28; implicitHeight: 28; radius: 9
                            icon: "close"; iconSize: 13; iconColor: Theme.textMuted
                            tooltip: qsTr("Remove from queue")
                            onClicked: Player.removeFromQueue(slot.queueIndex)
                        }
                    }
                }
                MouseArea {
                    id: rowMouse
                    anchors.fill: parent
                    anchors.leftMargin: 24
                    anchors.rightMargin: 36
                    hoverEnabled: true
                    acceptedButtons: Qt.LeftButton
                    propagateComposedEvents: true
                    onDoubleClicked: Player.playQueueIndex(slot.queueIndex)
                }
            }
        }
    }
}
