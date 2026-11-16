import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root
    color: Theme.panel
    radius: Theme.rPanel
    implicitHeight: col.implicitHeight + 32

    ColumnLayout {
        id: col
        anchors.fill: parent
        anchors.margins: 16
        spacing: 10
        RowLayout {
            Layout.fillWidth: true
            Text {
                text: qsTr("Downloads")
                color: Theme.text
                font.pixelSize: 15
                font.weight: Font.Bold
            }
            Item { Layout.fillWidth: true }
            Text {
                Layout.maximumWidth: root.width * 0.6
                text: (Fmt.revision >= 0 ? qsTr("%1 of %2").arg(Fmt.number(Downloads.completedCount)).arg(Fmt.number(Downloads.totalCount)) : "")
                      + (Downloads.speed > 0 ? " · " + Fmt.speed(Downloads.speed) : "")
                color: Theme.textMuted
                font.pixelSize: 12
                elide: Text.ElideRight
            }
        }
        SeekBar {
            Layout.fillWidth: true
            implicitHeight: 5
            barHeight: 5
            value: Downloads.progress
            interactive: false
            showThumb: false
            trackColor: Theme.elevated
        }
        Repeater {
            model: Downloads.activeItems
            delegate: RowLayout {
                required property var modelData
                Layout.fillWidth: true
                spacing: 10
                Text {
                    Layout.fillWidth: true
                    text: modelData.title
                    color: Theme.text
                    font.pixelSize: 13
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }
                Text {
                    text: Fmt.percent(modelData.progress)
                    color: Theme.text
                    font.pixelSize: 13
                    font.weight: Font.Bold
                }
            }
        }
        Text {
            visible: Downloads.activeItems.length === 0
            Layout.fillWidth: true
            text: Downloads.paused ? qsTr("Downloads are paused.")
                  : Downloads.busy ? qsTr("Preparing…") : qsTr("All downloads finished.")
            color: Theme.textMuted
            font.pixelSize: 13
            elide: Text.ElideRight
        }
        Text {
            text: qsTr("See all downloads")
            color: linkMouse.containsMouse ? "#FFD27A" : Theme.amber
            font.pixelSize: 13
            font.weight: Font.Bold
            font.underline: true
            MouseArea {
                id: linkMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: App.navigate("downloads")
            }
        }
    }
}
