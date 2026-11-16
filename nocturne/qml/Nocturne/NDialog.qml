import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Modal dialog used for text input (new / rename playlist) and confirmations.
Popup {
    id: dlg
    property string title: ""
    property string message: ""
    property string acceptText: qsTr("OK")
    property string cancelText: qsTr("Cancel")
    property bool showInput: false
    property alias inputText: input.text
    property string placeholder: ""
    property bool destructive: false
    property var onAcceptedCallback: null

    function ask(opts) {
        title = opts.title || ""
        message = opts.message || ""
        acceptText = opts.acceptText || qsTr("OK")
        showInput = !!opts.input
        input.text = opts.text || ""
        placeholder = opts.placeholder || ""
        destructive = !!opts.destructive
        onAcceptedCallback = opts.onAccepted || null
        open()
        if (showInput) {
            input.forceActiveFocus()
            input.selectAll()
        }
    }
    function accept() {
        if (showInput && input.text.trim() === "") return
        var cb = onAcceptedCallback
        var value = input.text.trim()
        close()
        if (cb) cb(value)
    }

    parent: Overlay.overlay
    anchors.centerIn: parent
    width: Math.min(440, parent ? parent.width - 48 : 440)
    modal: true
    focus: true
    padding: 24
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    Overlay.modal: Rectangle { color: "#990A0A14" }
    enter: Transition {
        NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.fast }
        NumberAnimation { property: "scale"; from: 0.95; to: 1; duration: Theme.fast; easing.type: Easing.OutQuad }
    }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 140 } }

    background: Rectangle {
        color: Theme.panel
        radius: Theme.rCard
        border.color: Theme.elevated
        border.width: 1
    }

    contentItem: ColumnLayout {
        spacing: 16
        Text {
            Layout.fillWidth: true
            text: dlg.title
            color: Theme.text
            font.pixelSize: 18
            font.weight: Font.ExtraBold
            wrapMode: Text.Wrap
        }
        Text {
            Layout.fillWidth: true
            visible: dlg.message !== ""
            text: dlg.message
            color: Theme.textMuted
            font.pixelSize: 14
            wrapMode: Text.Wrap
        }
        Rectangle {
            Layout.fillWidth: true
            visible: dlg.showInput
            implicitHeight: 48
            radius: Theme.rInput
            color: Theme.surface
            border.width: input.activeFocus ? 1 : 0
            border.color: "#553B6CF6"
            NTextField {
                id: input
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                placeholderText: dlg.placeholder
                onAccepted: dlg.accept()
            }
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Item { Layout.fillWidth: true }
            NButton {
                text: dlg.cancelText
                bg: Theme.surface
                textColor: Theme.textMuted
                onClicked: dlg.close()
            }
            NButton {
                text: dlg.acceptText
                gradient: !dlg.destructive
                bg: dlg.destructive ? "#33F87171" : "transparent"
                textColor: dlg.destructive ? Theme.error : Theme.text
                enabled: !dlg.showInput || input.text.trim() !== ""
                onClicked: dlg.accept()
            }
        }
    }
}
