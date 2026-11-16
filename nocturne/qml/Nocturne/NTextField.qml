import QtQuick
import QtQuick.Controls.Basic

TextField {
    id: field
    color: Theme.text
    placeholderTextColor: Theme.placeholder
    selectionColor: Theme.selection
    selectedTextColor: Theme.text
    font.pixelSize: 14
    font.weight: Font.Medium
    selectByMouse: true
    leftPadding: 0
    rightPadding: 0
    verticalAlignment: TextInput.AlignVCenter
    background: Item {}
    Keys.onEscapePressed: { field.focus = false }
}
