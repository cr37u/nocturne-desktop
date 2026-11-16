import QtQuick
import QtQuick.Layouts

// Label + description on the left, control on the right.
RowLayout {
    id: root
    property string label: ""
    property string description: ""
    default property alias control: holder.data
    spacing: 16

    ColumnLayout {
        Layout.fillWidth: true
        spacing: 2
        Text {
            Layout.fillWidth: true
            text: root.label
            color: Theme.text
            font.pixelSize: 14
            font.weight: Font.Bold
            wrapMode: Text.Wrap
        }
        Text {
            Layout.fillWidth: true
            visible: root.description !== ""
            text: root.description
            color: Theme.textMuted
            font.pixelSize: 12
            wrapMode: Text.Wrap
        }
    }
    RowLayout {
        id: holder
        spacing: 8
    }
}
