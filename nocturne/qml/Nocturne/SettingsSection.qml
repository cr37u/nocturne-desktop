import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root
    property string title: ""
    property string subtitle: ""
    default property alias content: body.data
    color: Theme.panel
    radius: Theme.rPanel
    implicitHeight: col.implicitHeight + 40

    ColumnLayout {
        id: col
        anchors.fill: parent
        anchors.margins: 20
        spacing: 14
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 4
            Text {
                Layout.fillWidth: true
                text: root.title
                color: Theme.text
                font.pixelSize: 17
                font.weight: Font.ExtraBold
                elide: Text.ElideRight
            }
            Text {
                Layout.fillWidth: true
                visible: root.subtitle !== ""
                text: root.subtitle
                color: Theme.textMuted
                font.pixelSize: 13
                wrapMode: Text.Wrap
            }
        }
        ColumnLayout {
            id: body
            Layout.fillWidth: true
            spacing: 12
        }
    }
}
