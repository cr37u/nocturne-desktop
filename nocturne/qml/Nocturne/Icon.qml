import QtQuick

// Vector icon rendered by the Python image provider at the exact device size.
Image {
    id: root
    property string name: ""
    property color color: Theme.text
    property real size: 20

    width: size
    height: size
    visible: name !== ""
    source: name !== "" ? Theme.icon(name, color) : ""
    sourceSize: Qt.size(Math.ceil(size * Screen.devicePixelRatio), Math.ceil(size * Screen.devicePixelRatio))
    fillMode: Image.PreserveAspectFit
    smooth: true
    mipmap: false
    cache: true
}
